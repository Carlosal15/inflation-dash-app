import pandas as pd
import io
import plotly.graph_objects as go
from typing import Dict, Any, Optional, List
import aiohttp
import asyncio
from inflation_app.constants import DATE_FIELD, CPI_SUFFIX
from inflation_app.config_base_model import Config
from inflation_app.logger_config import logger


class DataProcessor:
    """
    This class is used to get the data by asynchronously performing the http
    requests, load it and process it using pandas into dataframes with
    quarterly annualised inflation data, merging the dataframes and generating
    a figure layout to be used in a dash app.

    It also handles logging of errors at the different stages.

    If some config results in data that cannot be successfully requested and
    processed (bad url, wrong date or cpi columns, wrong formats, insufficient
    data...), it will log the corresponding error but will still return a layout
    with those successful ones.
    """

    def __init__(self, configs: List[Config]):
        self.configs = configs
        self.dataframes: Dict[str, pd.DataFrame] = {}
        self.logger = logger

    async def get_data(self, config: Config) -> Optional[pd.DataFrame]:
        """
        Performs an asynchronous http request and (if successful) returns
        a dataframe with the dates and inflation info to be processed.
        """
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
        """
        Processes a dataframe built from the csv into a correctly formatted one with
        annualised inflation and the correct date information.

        self.get_data will return a simple dataframe with a date column and a cpi column.
        This method:

        - first tries to format the dates into quarterly ones (given that, in
        the provided example, one of the csv's only had quarterly info) and discard dates
        that do not refer to quarterly periods (e.g. yearly, monthly...).

        - Then converts the quarters to indices of the dataframe, to be able to merge with
        other processed dataframes on matching quarters.

        - Calculates the annualised inflation rate (the data provided only shows the cpi,
        not the inflation).
        """
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
        """
        Calls get_data and process_data to add dataframes to the class.
        """
        df = await self.get_data(config)
        if df is not None:
            processed_df = self.process_data(df, config)
            if processed_df is not None and not processed_df.empty:
                self.dataframes[config.name] = processed_df

    async def run(self) -> None:
        """
        Gathers all get and process tasks.
        """
        tasks = [self.get_and_process_data(config) for config in self.configs]

        await asyncio.gather(*tasks)

    def merge_data(self) -> Optional[pd.DataFrame]:
        """
        Merges all self.dataframes which are produced after processing and
        organising data by quarters (therefore being able to merge on index).
        """
        merged_df = pd.concat(self.dataframes.values(), join="inner", axis=1)
        merged_df.dropna(inplace=True)
        if merged_df.empty:
            self.logger.error(
                "Could not produce a plot for the provided config data. "
                "Possible reason: data from different sources do not "
                "overlap in time. "
            )
            return None
        return merged_df

    async def generate_figure(self) -> Optional[Dict[str, Any]]:
        """
        Generates the info and layout for the app figure from the processed data.
        """
        await self.run()
        if self.dataframes:
            merged_df = self.merge_data()
            if merged_df is None:
                return None
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
