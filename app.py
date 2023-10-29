import pandas as pd
import io
import plotly.graph_objects as go
from dash import dcc, html
import dash
from enums import ConfigFields
import json
from typing import Dict, Any, Optional
import aiohttp
import asyncio
import logging
from constants import DATE_FIELD, CPI_SUFFIX


class DataProcessor:
    def __init__(self, configs):
        self.configs = configs
        self.dataframes: Dict[str, pd.DataFrame] = {}
        self.logger = logging.getLogger(__name__)
        handler = logging.FileHandler("dataprocessor.log")
        handler.setLevel(logging.ERROR)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    async def get_data(self, config) -> Optional[pd.DataFrame]:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(config[ConfigFields.URL]) as response:
                if response.status != 200:
                    error_msg = (
                        f"Error getting data from "
                        f"{config[ConfigFields.URL]}: {response.status}"
                    )
                    self.logger.error(error_msg)
                    return None
                try:
                    # TODO: check date and cpi cols are integers and not the same val
                    content = await response.text()
                    date_col = config[ConfigFields.DATE_COLUMN]
                    cpi_col = config[ConfigFields.CPI_COLUMN]
                    cpi_col_name = config[ConfigFields.NAME] + CPI_SUFFIX
                    usecols = [
                        date_col,
                        cpi_col,
                    ]
                    names = (
                        [DATE_FIELD, cpi_col_name]
                        if date_col < cpi_col
                        else [cpi_col_name, DATE_FIELD]
                    )
                    df = pd.read_csv(
                        io.StringIO(content),
                        skiprows=config[ConfigFields.SKIPROWS],
                        usecols=usecols,
                        names=names,
                    )

                    return df
                except Exception as e:
                    error_msg = (
                        f"Error reading CSV data from {config[ConfigFields.URL]}: {e}"
                    )
                    self.logger.error(error_msg)
                    return None

    def process_data(self, df: pd.DataFrame, config) -> Optional[pd.DataFrame]:
        try:
            df[DATE_FIELD] = df[DATE_FIELD].str.replace(" ", "-")
            df = df[df[DATE_FIELD].str.contains(r"\d{4}-Q\d")]

            df.set_index(
                pd.PeriodIndex(df[DATE_FIELD], freq=config["freq"]), inplace=True
            )

            df[config[ConfigFields.NAME]] = (
                df[config[ConfigFields.NAME] + CPI_SUFFIX].pct_change(periods=4) * 100
            )

            df.drop(
                columns=[c for c in df.columns if c != config[ConfigFields.NAME]],
                axis=1,
                inplace=True,
            )
            df.sort_index(inplace=True)
            df.dropna(inplace=True)
            if df.empty:
                self.logger.error(
                    f"Processing of {config[ConfigFields.NAME]} "
                    "returned an empty dataframe. Possible reason: "
                    "CSV only contains CPI(H) data for a year "
                    "(cannot calculate year-on-year inflation)."
                )
            return df

        except Exception as e:
            error_msg = (
                f"Error processing CSV data from {config[ConfigFields.NAME]}: {e}"
            )
            self.logger.error(error_msg)
            return None

    async def get_and_process_data(self, config) -> None:
        df = await self.get_data(config)
        if df is not None:
            processed_df = self.process_data(df, config)
            if processed_df is not None and not processed_df.empty:
                self.dataframes[config[ConfigFields.NAME]] = processed_df

    async def run(self) -> None:
        tasks = [self.get_and_process_data(config) for config in self.configs]

        await asyncio.gather(*tasks)

    def merge_data(self) -> pd.DataFrame:
        merged_df = pd.concat(self.dataframes.values(), join="inner", axis=1)
        merged_df.dropna(inplace=True)
        return merged_df

    async def generate_figure(self) -> Optional[Dict[str, Any]]:
        await self.run()
        if self.dataframes:
            merged_df = self.merge_data()
            merged_df.index = merged_df.index.to_timestamp()
            plot_lines = [
                go.Scatter(x=merged_df.index, y=merged_df[c], mode="lines", name=c)
                for c in merged_df.columns
            ]
            fig = {
                "layout": go.Layout(
                    title="Inflation (CPI)",
                    xaxis={"title": "Date"},
                    yaxis={"title": "%"},
                ),
                "data": plot_lines,
            }
            return fig
        else:
            return None


async def generate_fig() -> Optional[Dict[str, Any]]:
    with open("configs.json") as f:
        configs: Dict[str, Any] = json.load(f)
    processor = DataProcessor(configs)
    fig = await processor.generate_figure()
    return fig


def app_plot_df(fig) -> None:
    """
    takes in a df that may be obtained through any of the previous function/methods,
    and produces the plotly and app objects for it
    """
    # Initialize the Dash app
    app = dash.Dash(__name__)

    # Define the layout of the app
    app.layout = html.Div(
        children=[
            # html.H1(children="Inflation (CPI )"),
            dcc.Graph(
                id="example-graph",
                figure=fig,
            ),
        ]
    )
    app.run_server(debug=True, host="0.0.0.0", port=8080, use_reloader=False)


async def main() -> None:
    fig = await generate_fig()
    if fig is not None:
        app_plot_df(fig)
    else:
        # app that just displays error message
        pass


if __name__ == "__main__":
    asyncio.run(main())
