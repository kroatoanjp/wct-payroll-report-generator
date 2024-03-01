# wct-payroll-report-generator

## Setup
``` bash
pip3 install -r requirements.txt
```
### Trello Credentials
Setting up the payroll script will require four different Trello keys: the [OAuth Secret](https://trello.com/app-key#:~:text=need%20your%20Secret.-,Secret,-:), as well as an API Key, API Secret, and API Token, all of which can be created in the [Trello Power-Up Admin Portal](https://trello.com/power-ups/admin/).

The payroll script will look for these keys under the environmental variables  `TRELLO_TOKEN_SECRET`, `TRELLO_API_KEY`, `TRELLO_API_SECRET`,  and `TRELLO_TOKEN` respectively.

These variables can alternatively be loaded from a `.env` file:
```bash
# .env
TRELLO_TOKEN_SECRET="<OAUTH SECRET>"
TRELLO_API_KEY="<API KEY>"
TRELLO_API_SECRET="<API SECRET>"
TRELLO_TOKEN="<API TOKEN>"
```

### Patreon Recipient Data
The `patreon_recipients.json` file contains the data for who is and isn't receiving Patreon money. This file needs to be manually kept in sync with the Patreon Payroll Google Sheet. Each time the payroll script is run, it will print the set of people with Trello activity that have not been added to the `patreon_recipients.json` file.
```bash
# All Trello users have been added to the recipients file
INFO:__main__:Unregistered Recipients: set()
```
```bash
# Trello users were found that were not added to the recipients file
INFO:__main__:Unregistered Recipients: {'kroatoanjp'}
```

## Usage
```bash
usage: main.py [-h] [-s START_DATE] [-e END_DATE] [-r REPORTS_DIR] [-c CACHE_DIR] [-v]

Generates Trello activity reports

optional arguments:
  -h, --help            show this help message and exit
  -s START_DATE, --start-date START_DATE
                        YYYY-MM-DD report start date (inclusive) (default: None)
  -e END_DATE, --end-date END_DATE
                        YYYY-MM-DD report end date (inclusive) (default: None)
  -r REPORTS_DIR, --reports-dir REPORTS_DIR
                        directory in which to output generated reports (default: reports/)
  -c CACHE_DIR, --cache-dir CACHE_DIR
                        directory in which to cache Trello table data (default: cache/)
  -v, --verbose
```

### Monthly Reports
```bash
$ python3 main.py
```

Running the payroll script without specifying any arguments will generate Trello activity reports for each month of available data. The first run will be slow, but in subsequent runs board data will be pulled from the local cache.

### Time Range Report
```bash
# python3 main.py -s start_date -e end_date
$ python3 main.py -s 2024-01-01 -e 2024-02-29
```
Running the payroll script when specifying a start and end date will generate a single Trello activity report for that range. The first run will be slow, but in subsequent runs board data will be pulled from the local cache.
