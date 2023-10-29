import pytest
from unittest.mock import patch, MagicMock
from app import DataProcessor
import pandas as pd
from constants import DATE_FIELD, CPI_SUFFIX
from pandas.testing import assert_frame_equal
from enums import ConfigFields
import aioresponses


@patch("aiohttp.ClientSession.get")
async def test_get_data_response_not_200(mock_get, caplog):
    """
    Checks get_data method returns None and logs the correct error
    when url response is != 200
    """
    configs = [
        {
            "url": "http://test.com",
            "date_column": 1,
            "cpi_column": 2,
            "name": "test CPI",
            "skiprows": 0,
        }
    ]
    data_processor = DataProcessor(configs)
    mock_response = MagicMock()
    mock_response.status = 404
    mock_get.return_value.__aenter__.return_value = mock_response

    expected_error_msg = "Error getting data from http://test.com: 404"

    resp = await data_processor.get_data(configs[0])

    assert expected_error_msg in caplog.text
    assert resp is None


@patch("aiohttp.ClientSession.get")
async def test_get_data_error_reading_csv(mock_get, caplog):
    """
    Checks it raises the correct error if the connection is successful
    but the payload cannot be converted to a dataframe.
    """
    # Set up the mock response
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_get.return_value.__aenter__.return_value = mock_resp

    # Set up the DataProcessor and configs
    configs = [
        {
            "url": "http://test.com",
            "date_column": 1,
            "cpi_column": 2,
            "name": "test CPI",
            "skiprows": 0,
        }
    ]
    dp = DataProcessor(configs)

    # Run the method and check the logs
    await dp.get_data(configs[0])
    assert "Error reading CSV data from http://test.com:" in caplog.text


@patch("aiohttp.ClientSession.get")
async def test_get_data(mock_get):
    """
    Checks correctly building the df from the config.
    """
    mock_resp = MagicMock()
    mock_resp.status = 200

    async def mock_text():
        return "2021-Q1,10\n2021-Q2,11\n "

    mock_resp.text.side_effect = mock_text
    mock_get.return_value.__aenter__.return_value = mock_resp
    configs = [
        {
            "url": "http://test.com",
            "date_column": 0,
            "cpi_column": 1,
            "name": "test CPI",
            "skiprows": 0,
        }
    ]

    dp = DataProcessor(configs)
    # Run the method and check the logs
    loaded_df = await dp.get_data(configs[0])

    cpi_col_name = configs[0][ConfigFields.NAME] + CPI_SUFFIX
    expected_df = pd.DataFrame(
        {DATE_FIELD: ["2021-Q1", "2021-Q2"], cpi_col_name: [10, 11]}
    )
    assert_frame_equal(loaded_df, expected_df, check_dtype=False)


dates_hyphen = [
    "2021-Q1",
    "2021-Q2",
    "2021-Q3",
    "2021-Q4",
    "2022-Q1",
    "2022-Q2",
    "2022-Q3",
    "2022-Q4",
]
dates_space = [
    "2021 Q1",
    "2021 Q2",
    "2021 Q3",
    "2021 Q4",
    "2022 Q1",
    "2022 Q2",
    "2022 Q3",
    "2022 Q4",
]
dates_extra = dates_space + ["2010", "2014 NOV"]
cpis_default = [10, 10, 10, 10, 11, 12, 13, 14]
cpis_extra = [10, 10, 10, 10, 11, 12, 13, 14, 15, 16]


@pytest.mark.parametrize(
    "dates,cpis",
    [
        (dates_hyphen, cpis_default),
        (dates_space, cpis_default),
        (dates_extra, cpis_extra),
    ],
)
def test_process_data(dates, cpis):
    """
    Checks correctly processing the dataframe from the config
    (dates, inflation, etc), for the different date formats in the used CSV's
    (e.g. "2010-Q1" and "2010 Q1" should be processed equally), as well as
    other dates not corresponding to quarters not being used.
    """
    configs = {
        "url": "http://test.com",
        "date_column": 0,
        "cpi_column": 1,
        "name": "test CPI",
        "skiprows": 0,
        "freq": "Q",
    }

    dp = DataProcessor([configs])

    df = pd.DataFrame(
        {
            DATE_FIELD: dates,
            configs[ConfigFields.NAME] + CPI_SUFFIX: cpis,
        }
    )

    processed_df = dp.process_data(df, configs)

    expected_df = pd.DataFrame(
        {
            configs[ConfigFields.NAME]: [10, 20, 30, 40],
        },
        index=pd.PeriodIndex(
            [
                "2022Q1",
                "2022Q2",
                "2022Q3",
                "2022Q4",
            ],
            freq=configs["freq"],
        ),
    )
    expected_df.index.names = [DATE_FIELD]

    pd.testing.assert_frame_equal(processed_df, expected_df, check_dtype=False)


def test_error_process_data():
    """
    Checks DataProcessor.process_data correctly handles error in
    processing.
    """
    configs = {
        "url": "http://test.com",
        "date_column": 0,
        "cpi_column": 1,
        "name": "test CPI",
        "skiprows": 0,
        "freq": "Q",
    }

    dp = DataProcessor([configs])

    dates_no_quarters = ["2021", "2022"]
    cpis = [10, 11]
    df = pd.DataFrame(
        {
            DATE_FIELD: dates_no_quarters,
            configs[ConfigFields.NAME] + CPI_SUFFIX: cpis,
        }
    )

    processed_df = dp.process_data(df, configs)

    assert processed_df is None


@pytest.fixture
def processor():
    configs = [
        {
            "url": "http://test.com",
            "date_column": 0,
            "cpi_column": 1,
            "name": "test CPI",
            "skiprows": 0,
            "freq": "Q",
        },
        {
            "url": "http://test-1.com",
            "date_column": 0,
            "cpi_column": 1,
            "name": "test-1 CPI",
            "skiprows": 0,
            "freq": "Q",
        },
        {
            "url": "http://test-2.com",
            "date_column": 0,
            "cpi_column": 1,
            "name": "test-2 CPI",
            "skiprows": 0,
            "freq": "Q",
        },
        {
            "url": "http://test-2.com",
            "date_column": 0,
            "cpi_column": 1,
            "name": "test-3 CPI",
            "skiprows": 0,
            "freq": "Q",
        },
    ]
    return DataProcessor(configs)


@pytest.mark.asyncio
async def test_run_and_merge(processor):
    """
    Full run and merge test with 4 different csv payloads, including
    bad responses, unused data and insufficient data.

    - The first response is a normal one with more than one year of data.

    - The second also includes sufficient data but has extra data that should
      be discarded (a yearly value instead of a quarterly one).

    - The third one contains almost a year of data, therefore not enough to
      calculate year-on-year variations.

    - The fourth one is a bad response.

    The final merged dataframe should contain only the usable values of the
    first two csv responses, and therefore still generate a figure.
    """
    responses = [
        "2021-Q1,10\n2021-Q2,10\n2021-Q3,10\n2021-Q4,10\n2022-Q1,11\n",
        "2021-Q1,10\n2021-Q2,10\n2021-Q3,10\n2021-Q4,10\n2022-Q1,12\n2023,25\n",
        "2021-Q1,10\n2021-Q2,10\n2021-Q3,10\n2021-Q4,10\n",
        "bad_response",
    ]
    with aioresponses.aioresponses() as mocked:
        for ind, config in enumerate(processor.configs):
            url = config[ConfigFields.URL]
            response_text = responses[ind]
            mocked.get(url, status=200, body=response_text)

        await processor.run()
        merged_df = processor.merge_data()

        # Check if dataframes were created for all configs
        assert len(processor.dataframes) == 2

        # Check if merged dataframe has correct columns
    expected_df = pd.DataFrame(
        {
            processor.configs[0][ConfigFields.NAME]: [10],
            processor.configs[1][ConfigFields.NAME]: [20],
        },
        index=pd.PeriodIndex(
            [
                "2022Q1",
            ],
            freq=processor.configs[0]["freq"],
        ),
    )
    expected_df.index.names = [DATE_FIELD]

    # Check if the processed DataFrame matches the expected DataFrame
    pd.testing.assert_frame_equal(merged_df, expected_df, check_dtype=False)
