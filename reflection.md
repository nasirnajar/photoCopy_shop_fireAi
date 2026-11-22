# Reflection: Chenab Printers Peak-Hour Analyzer

## Why I Built This
I wanted a simple tool to figure out when Chenab Printers gets busiest and how long customers usually wait. Instead of using heavy software, I built it with basic Python so it runs immediately on any computer without installing extra packages.

## What Worked Well
* **Easy to run:** Having both a quick terminal summary (`peak_hour_analyzer.py`) and a simple browser dashboard (`peak_hour_app.py`) makes the numbers easy to check and read.
* **Flexible data entry:** Allowing blank waiting times in the CSV means someone can still log customer counts during a rush even if they don't have time to track wait minutes.
* **Clear breakdown:** Looking at both 30-minute slots and full hours helps show whether a rush is just a quick spike or a steady crowd.

## Current Limitations
Right now, `customer_observations.csv` only has 20 estimated rows from a single day. While the numbers (like 16:00–17:00 being the busiest hour with 23 customers) prove that the code calculates everything properly, they don't reflect real shop traffic yet. One day of estimated data isn't enough to show how busy the shop actually gets across a normal week.

## Next Steps
* Collect real, timed observations at the shop over several days instead of relying on estimates.
* Compare different days of the week (for example, weekdays vs. weekends) to spot real patterns.
* Add a file upload button directly on the web page so users don't have to type file paths into the terminal.