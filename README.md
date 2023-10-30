# inflation-dash-app
This is a python package to create a simple dash app that displays a plot with the annualised inflation of Consumer Price Indices (plus owner-occupier's Housing cost) or CPI(H) from AU and UK, obtained from online sources. 

Beyond that, this package provides an efficient and scalable approach to obtain and process data, error handling/logging and an editable file for users to set up different data sources. 

# Simple usage for an example dash app (assessment test)
NOTE: This package has been developed and only tested with Python 3.12.

This package is pip installable. Navigate to the package folder and execute (ideally within a virtual environment):
```
pip install . 
```

To generate the dash app with the requested plot of UK and AU annualised inflation rates, simply run
```
python inflation/app.py
```
(replace python with the correct executable if required). It should generate the plot on http://0.0.0.0:8080/ .

# How it works and features

## Setting up the data sources
This package uses a json configuration file (configs.json) with a list of dictionaries, each with info about different data sources. For the two requested data sources in the assessment, it looks like (as delivered):
```
[
    {
        "url": "https://api.data.abs.gov.au/data/CPI/1.10001.10.50.Q?format=csv",
        "skiprows": 1,
        "freq": "Q",
        "name": "AU CPI",
        "date_column":6,
        "cpi_column":7
    },
    {
        "url": "https://www.ons.gov.uk/generator?format=csv&uri=/economy/inflationandpriceindices/timeseries/l522/mm23",
        "skiprows": 8,
        "freq": "Q",
        "name": "UK CPIH",
        "date_column":0,
        "cpi_column":1
    }
]
``` 
The fields are self-explanatory, and they include the URL to obtain the csv, the index of the date and CPI(H) columns, how many rows to skip, and the name of the data to display in the dash app. 

Pydantic is used to validate the format (see the Config class in config_base_model.py). If some dictionary is incorrectly formatted, an error will be shown in the log (inflation_app.log), but the correct ones will be used (can be checked by adding a dummy {"wrong_field" : "wrong_value"} to the list in configs.json, and running inflation/app.py again). In general, the app tries to plot what is possible while logging any issues in the process, instead of stopping. 

If none are correctly formatted or result in bad data with nothing to plot, the app will display a message indicating to the user to check the logs.

## Getting and processing data
Getting and processing the data is done in the DataProcessor class in data_processor.py. The csv data is obtained asynchronously using aiohttp for improved performance (most probably the first bottleneck for scalability) and stored in a pandas dataframe for each source/url, which is then processed into dataframes containing quarterly annualised inflation values that can be easily merged. 

If some data cannot be processed into annualised inflation for reasons such as bad URL response, incorrect config setup (e.g. wrong date or CPI columns), not enough data (e.g. data for less than a year, so no annualised inflation calculated), it is added to the log, and the correctly processed ones are still used. The processed dataframes are merged on the common indices (i.e., overlaps in time), so if the data does not overlap in time, no figure is generated. 

A note to be made here is that currently, only dates with format "%Y-Q%q" or "%Y Q%q" are accepted, and any dates with different format automatically discarded. Quarterly data in that format was used by default given the provided data sources (AU data was only provided quarterly, while UK data mixed yearly, quarterly and monthly). This could be a good place to make the package more powerful by handling different data formats and periods. For example, by coercing %Y-%m-%d formats that are nonetheless used for representing quarters into quarter periods; or by aggregating data from smaller periods into quarters;
or by using flexible time periods altogether and leveraging pandas' capabilities for unstacking them into different time frequencies.

The DataProcessor class also produces the figure layout info for the dash app. 

## Running the app
app.py uses the figure generated in by DataProcessor for plotting. If no figure layout could be made (e.g. try changing config.json to use fake URLs and running app.py), it will just display a message indicating to check the logs.  
