import pandas as pd
import io
import plotly.graph_objects as go
from dash import dcc, html
import dash
import json
from typing import Dict, Any, Optional, List
import aiohttp
import asyncio
import logging
from inflation_app.constants import DATE_FIELD, CPI_SUFFIX
from inflation_app.config_dataclass import Config


class DataProcessor:
    def __init__(self, configs: List[Config]):
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

    async def get_data(self, config: Config) -> Optional[pd.DataFrame]:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(config.url) as response:
                if response.status != 200:
                    error_msg = (
                        f"Error getting data from " f"{config.url}: {response.status}"
                    )
                    self.logger.error(error_msg)
                    return None
                try:
                    # TODO: check date and cpi cols are integers and not the same val
                    content = await response.text()
                    date_col = config.date_column
                    cpi_col = config.cpi_column
                    cpi_col_name = config.name + CPI_SUFFIX
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
                        skiprows=config.skiprows,
                        usecols=usecols,
                        names=names,
                    )

                    return df
                except Exception as e:
                    error_msg = f"Error reading CSV data from {config.url}: {e}"
                    self.logger.error(error_msg)
                    return None

    def process_data(self, df: pd.DataFrame, config: Config) -> Optional[pd.DataFrame]:
        try:
            df[DATE_FIELD] = df[DATE_FIELD].str.replace(" ", "-")
            df = df[df[DATE_FIELD].str.contains(r"\d{4}-Q\d")]

            df.set_index(pd.PeriodIndex(df[DATE_FIELD], freq=config.freq), inplace=True)

            df[config.name] = df[config.name + CPI_SUFFIX].pct_change(periods=4) * 100

            df.drop(
                columns=[c for c in df.columns if c != config.name],
                axis=1,
                inplace=True,
            )
            df.sort_index(inplace=True)
            df.dropna(inplace=True)
            if df.empty:
                self.logger.error(
                    f"Processing of {config.name} "
                    "returned an empty dataframe. Possible reason: "
                    "CSV only contains CPI(H) data for a year "
                    "(cannot calculate year-on-year inflation)."
                )
            return df

        except Exception as e:
            error_msg = f"Error processing CSV data from {config.name}: {e}"
            self.logger.error(error_msg)
            return None

    async def get_and_process_data(self, config: Config) -> None:
        df = await self.get_data(config)
        if df is not None:
            processed_df = self.process_data(df, config)
            if processed_df is not None and not processed_df.empty:
                self.dataframes[config.name] = processed_df

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
    configs: List[Config] = load_configs("configs.json")
    if configs:
        processor = DataProcessor(configs)
        fig = await processor.generate_figure()
        return fig
    else:
        return None


def load_configs(json_file: str) -> List[Config]:
    with open(json_file, "r") as f:
        data = json.load(f)

    configs: List[Config] = []
    for item in data:
        try:
            config = Config(**item)
            configs.append(config)
        except Exception as e:
            logging.error(f"Error loading config: {e}")

    return configs


def app_plot_df(fig) -> None:
    """
    Takes in a df that may be obtained through any of the previous function/methods,
    and produces the plotly and app objects for it
    """
    app = dash.Dash(__name__)

    app.layout = html.Div(
        children=[
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
