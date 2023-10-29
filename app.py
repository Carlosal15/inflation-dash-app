import pandas as pd
import io
import plotly.graph_objects as go
from dash import dcc, html
import dash
from enums import ConfigFields
import json
from typing import Dict, Any
import aiohttp
import asyncio


DATE_FIELD = "date"
CPI_SUFFIX = "__cpi_"


class DataProcessor:
    def __init__(self, configs):
        self.configs = configs
        self.dataframes = {}

    async def get_data(self, config):
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(config[ConfigFields.URL]) as response:
                if response.status != 200:
                    self.error_message = (
                        f"Error getting data from "
                        f"{config[ConfigFields.URL]}: {response.status}"
                    )
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
                    self.error_message = (
                        f"Error reading CSV data from {config[ConfigFields.URL]}: {e}"
                    )
                    return None

    def process_data(self, df, config):
        try:
            df[DATE_FIELD] = df[DATE_FIELD].str.replace(" ", "-")
            df = df[df[DATE_FIELD].str.contains(r"\d{4}-Q\d")]

            df.set_index(
                pd.PeriodIndex(df[DATE_FIELD], freq=config["freq"]), inplace=True
            )

            df[config[ConfigFields.NAME]] = df[
                config[ConfigFields.NAME] + CPI_SUFFIX
            ].pct_change(periods=4)

            df.drop(
                columns=[c for c in df.columns if c != config[ConfigFields.NAME]],
                axis=1,
                inplace=True,
            )

            return df

        except Exception as e:
            print(f"Error processing data: {e}")
            return None

    async def get_and_process_data(self, config):
        df = await self.get_data(config)
        if df is not None:
            processed_df = self.process_data(df, config)
            if processed_df is not None:
                self.dataframes[config[ConfigFields.NAME]] = processed_df

    async def run(self):
        tasks = [self.get_and_process_data(config) for config in self.configs]

        await asyncio.gather(*tasks)

    def merge_data(self):
        merged_df = pd.concat(self.dataframes.values(), join="inner", axis=1)
        merged_df.dropna(inplace=True)
        return merged_df

    async def generate_figure(self):
        await self.run()
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


async def generate_fig():
    with open("configs.json") as f:
        configs: Dict[str, Any] = json.load(f)
    processor = DataProcessor(configs)
    fig = await processor.generate_figure()
    return fig


def app_plot_df(fig):
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


async def main():
    fig = await generate_fig()
    app_plot_df(fig)


if __name__ == "__main__":
    asyncio.run(main())
