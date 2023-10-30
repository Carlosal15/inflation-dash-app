from dash import dcc, html
import dash
import json
from typing import Dict, Any, Optional, List
import asyncio
from inflation_app.config_base_model import Config
from inflation_app.data_processor import DataProcessor
from inflation_app.logger_config import logger
import os

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


async def generate_fig() -> Optional[Dict[str, Any]]:
    """
    Generates the fig to be used in the dash app layout.

    It may fail to generate a figure, which is handled in the generate_app function
    to display a message for the user.
    """
    configs: List[Config] = load_configs("configs.json")
    if configs:
        processor = DataProcessor(configs)
        fig = await processor.generate_figure()
        return fig
    else:
        return None


def load_configs(json_file: str) -> List[Config]:
    """
    Loads the configs in a json file in the same folder and handles error logging
    if the configs or file are incorrectly formatted. Used for reading the
    example in configs.json.
    """
    file_path = os.path.join(__location__, json_file)
    configs: List[Config] = []
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise Exception(
                "config.json should contain a list of dictionaries, "
                "not a single dictionary."
            )
    except Exception as e:
        logger.error(f"Error reading json file: {e}")
        return configs

    for item in data:
        try:
            config = Config(**item)
            configs.append(config)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    if not configs:
        logger.error("No applicable configs were found in configs.json")
    return configs


def generate_app(fig: Optional[Dict[str, Any]]) -> None:
    """
    Used to generate the dash app layout for plotting annualised inflation.

    If no figure is passed, the app will display a message instructing the
    user to check the logs.
    """

    app = dash.Dash(__name__)

    if fig is None:
        layout = html.Div(
            children=[
                html.H2(
                    "Could not plot annualised inflation with current config. "
                    "Please, check the logs."
                )
            ]
        )

    else:
        layout = html.Div(
            children=[
                dcc.Graph(
                    id="inflation-graph",
                    figure=fig,
                ),
            ]
        )
    app.layout = layout
    app.run_server(debug=True, host="0.0.0.0", port=8080, use_reloader=False)


async def main() -> None:
    """Tries to generate the figure from the config and run the dash app."""
    fig = await generate_fig()
    generate_app(fig)


if __name__ == "__main__":
    asyncio.run(main())
