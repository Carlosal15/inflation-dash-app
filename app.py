import pandas as pd
import requests
import io
import plotly.graph_objects as go
from dash import dcc, html
import dash
from enums import ConfigFields
import json
from typing import Dict, Any

# pd.options.plotting.backend = "plotly"
# random ideas
# - use enums for date fields
# - if I want to overkill, I can use a common class with init and merge methods that reads and formats a csv,
#   with similar data, maybe even handling similar %Y-Q%q formats and extra data through user inpu & flags
#       - What about storing other time data to be able to process into quarters?
# - their plot has quarter data shifted (my dates start at the beginning of the quarter)
# -inflation indicators
#   - compound inflation rate
# - put the configs in a json reader
# - use asyncio for reading the csv's
# - have a schema for the json
# - typing for the config dict
# - log stuff properly

DATE_FIELD = "date"
CPI_SUFFIX = "__cpi_"


class DataProcessor:
    def __init__(self, configs):
        self.configs = configs
        self.dataframes = {}

    def get_data(self, config):
        try:
            request = requests.get(config[ConfigFields.URL]).content

            df = pd.read_csv(
                io.StringIO(request.decode("utf-8")),
                skiprows=config[ConfigFields.SKIPROWS],
                usecols=config[ConfigFields.USECOLS],
                names=[DATE_FIELD, config[ConfigFields.NAME] + CPI_SUFFIX],
            )

            return df

        except Exception as e:
            print(f"Error getting data from {config[ConfigFields.URL]}: {e}")
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

    def run(self):
        for config in self.configs:
            df = self.get_data(config)

            if df is not None:
                processed_df = self.process_data(df, config)

                if processed_df is not None:
                    self.dataframes[config[ConfigFields.NAME]] = processed_df

    def merge_data(self):
        merged_df = pd.concat(self.dataframes.values(), join="inner", axis=1)
        merged_df.dropna(inplace=True)
        return merged_df

    def generate_figure(self):
        self.run()
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


def generate_fig():
    with open("configs.json") as f:
        configs: Dict[str, Any] = json.load(f)
    processor = DataProcessor(configs)
    fig = processor.generate_figure()
    return fig


# def get_data_with_class():
#     with open("configs.json") as f:
#         configs: Dict[str, Any] = json.load(f)
#     processor = DataProcessor(configs)
#     processor.run()
#     df = processor.merge_data()
#     df.index = df.index.to_timestamp()

#     new_df = df.copy()
#     return new_df


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


if __name__ == "__main__":
    # df = get_data_with_class()
    fig = generate_fig()
    app_plot_df(fig)
