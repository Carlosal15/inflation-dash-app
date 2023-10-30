# inflation-dash-app
This is a python package to create a simple dash app that displays a plot with the annualised inflation of Consumer Price Indices (plus owner-occupier's Housing cost) or CPI(H) from AU and UK, obtained from online sources. 

Beyond that, this package provides an efficient and scalable approach to obtain and process more data, error handling/logging and an editable file for users to set up different data sources. 

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
This package is intended to provide more functionality and be more scallable/flexible than just producing the required plot. It uses a json configuration file (configs.json) with a list of dictionaries, each with info about different data sources. For the two requested data sources in the assessment, it looks like (as delivered):
```
[
    {
        "url": "https://api.data.abs.gov.au/data/CPI/1.10001.10.50.Q?format=csv",
        "skiprows": 1,
        "name": "AU CPI",
        "date_column":6,
        "cpi_column":7
    },
    {
        "url": "https://www.ons.gov.uk/generator?format=csv&uri=/economy/inflationandpriceindices/timeseries/l522/mm23",
        "skiprows": 8,
        "name": "UK CPIH",
        "date_column":0,
        "cpi_column":1
    }
]
``` 
The fields are self-explanatory, and they include the URL to obtain the csv, the index of the date and CPI(H) columns, how many rows to skip, and the name of the data to display in the dash app. If there is another source with quarterly data (more on that in the next section), it can be added to the config.json. Try adding the following info for Spain and run the app again:
```
  {
    "url": "https://fred.stlouisfed.org/graph/fredgraph.csv?bgcolor=%23e1e9f0&chart_type=line&drp=0&fo=open%20sans&graph_bgcolor=%23ffffff&height=450&mode=fred&recession_bars=off&txtcolor=%23444444&ts=12&tts=12&width=1318&nt=0&thu=0&trc=0&show_legend=yes&show_axis_titles=yes&show_tooltip=yes&id=ESPCPIALLQINMEI&scale=left&cosd=1960-01-01&coed=2023-04-01&line_color=%234572a7&link_values=false&line_style=solid&mark_type=none&mw=3&lw=2&ost=-99999&oet=99999&mma=0&fml=a&fq=Quarterly&fam=avg&fgst=lin&fgsnd=2020-02-01&line_index=1&transformation=lin&vintage_date=2023-10-30&revision_date=2023-10-30&nd=1960-01-01",
    "skiprows": 1,
    "name": "ESP CPI",
    "date_column": 0,
    "cpi_column": 1
  }
```

Pydantic is used to validate the format (see the Config class in config_base_model.py). If some dictionary is incorrectly formatted, an error will be shown in the log (inflation_app.log), but the correct ones will be used (can be checked by adding a dummy {"wrong_field" : "wrong_value"} to the list in configs.json, and running inflation/app.py again). In general, the app tries to plot what is possible while logging any issues in the process, instead of stopping. 

If none are correctly formatted or result in bad data with nothing to plot, the app will display a message indicating to the user to check the logs.

## Getting and processing data
Getting and processing the data is done in the DataProcessor class in data_processor.py. The csv data is obtained asynchronously using aiohttp for improved performance (most probably the first bottleneck for scalability) and stored in a pandas dataframe for each source/url, which is then processed into dataframes containing quarterly annualised inflation values that can be easily merged. 

If some data cannot be processed into annualised inflation for reasons such as bad URL response, incorrect config setup (e.g. wrong date or CPI columns), not enough data (e.g. data for less than a year, so no annualised inflation calculated), it is added to the log, and the correctly processed ones are still used. The processed dataframes are merged on the common indices (i.e., overlaps in time), so if the data does not overlap in time, no figure is generated. 

A note to be made here is that currently, the app works only with quarterly inflation information. If any dates in the csv contain the letter "Q" (such as in the UK and AU examples) it tries to use only those and discard the rest (AU data was only provided quarterly, while UK data mixed yearly, quarterly and monthly). "%Y-Q%q" or "%Y Q%q" are accepted in this sense. If no dates contain "Q", pandas will try to convert to quarterly periods inferring the format. This can result in failing to plot the data if, e.g., the CSV data is monthly instead of quarterly, so several inflation values would correspond to the same quarter. 

The DataProcessor class also produces the figure layout info for the dash app. 

## Running the app
app.py uses the figure generated by DataProcessor for plotting. If no figure layout could be made (e.g. try changing config.json to use fake URLs and running app.py), it will just display a message indicating to check the logs.  

# Tests
Unit tests can be found in tests/test_app.py