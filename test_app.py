import pytest
from unittest.mock import patch, MagicMock
import aiohttp
from app import DataProcessor


@patch("aiohttp.ClientSession.get")
async def test_get_data(mock_get, caplog):
    # Set up the mock response
    mock_resp = MagicMock()
    type(mock_resp).status = 200
    mock_resp.text.return_value = "mocked content"
    mock_get.return_value.__aenter__.return_value = mock_resp

    # Set up the DataProcessor and configs
    configs = [
        {
            "url": "http://test.com",
            "date_column": 1,
            "cpi_column": 2,
            "name": "test CPI",
        }
    ]
    dp = DataProcessor(configs)

    # Run the method and check the logs
    await dp.get_data(configs[0])
    assert "Error reading CSV data from http://test.com: mocked error" in caplog.text
