# Chenab Printers Peak-Hour Analyzer

A small Python tool that reads customer-flow observations from a CSV file and
summarizes busy periods and estimated waiting times for Chenab Printers.

## Run the dashboard

Requires Python 3; no third-party packages are needed.

```bash
python3 peak_hour_app.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in a browser. Stop the
server with `Ctrl+C`.

By default, the app reads `customer_observations.csv` from the project folder.
To use another CSV file:

```bash
python3 peak_hour_app.py path/to/data.csv
```

The dashboard shows the busiest hour and time slot, average estimated wait,
average customer count for each time slot, and a simple bar chart.

## Run the command-line summary

```bash
python3 peak_hour_analyzer.py
```

Pass a CSV path to analyze a different file:

```bash
python3 peak_hour_analyzer.py path/to/data.csv
```

## CSV format

The analyzer requires these column headers:

```text
time_slot_start,time_slot_end,customer_count,estimated_wait_minutes
```

Times must use 24-hour `HH:MM` format. Customer counts and waiting times must
be non-negative whole numbers. The `date` column is used to calculate daily
hourly averages; `data_status` and `observer_notes` can identify estimated data.
Blank estimated waiting times are allowed, but the `estimated_wait_minutes`
column must be present.

## How the summary is calculated

- Each time slot's customer count is averaged across rows with the same start
  and end time.
- Each time slot's estimated wait is averaged across rows with a recorded wait.
- Hourly customer totals are calculated by adding the recorded slot counts
  within each clock hour and date, then averaging those hourly totals across
  dates.
- The busiest hour and slot are those with the highest corresponding average.

## Current data and limitations

The current `customer_observations.csv` contains 20 rows from one date. The
analyzer reports **16:00–17:00** as the busiest hour (23 customers across its
two recorded half-hour slots) and **16:00–16:30** as the busiest slot (13
customers; 16-minute estimated wait). The average estimated wait across the
rows is 8.45 minutes.

The CSV notes say these values are estimates, not field measurements. The
summary is therefore only a calculation from the file and cannot confirm the
shop's actual traffic. One day's observations also cannot establish a typical
pattern across different days. Collect and enter genuine observations over
multiple days to make the averages more representative.
