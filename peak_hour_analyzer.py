import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


REQUIRED_COLUMNS = {
    "time_slot_start",
    "time_slot_end",
    "customer_count",
    "estimated_wait_minutes",
}
DEFAULT_DATA_FILE = Path(__file__).with_name("customer_observations.csv")


def read_observations(path):
    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError("the CSV file is empty")

        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing_columns:
            columns = ", ".join(sorted(missing_columns))
            raise ValueError(f"missing required CSV columns: {columns}")

        observations = []
        for line_number, row in enumerate(reader, start=2):
            try:
                customer_count = int(row.get("customer_count") or "")
                wait_text = (row.get("estimated_wait_minutes") or "").strip()
                wait_minutes = int(wait_text) if wait_text else None
                start = (row.get("time_slot_start") or "").strip()
                end = (row.get("time_slot_end") or "").strip()
                datetime.strptime(start, "%H:%M")
                datetime.strptime(end, "%H:%M")
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"line {line_number} has an invalid time, customer count, or wait time"
                ) from error

            if customer_count < 0 or (wait_minutes is not None and wait_minutes < 0):
                raise ValueError(f"line {line_number} has a negative count or wait time")

            observations.append(
                {
                    "date": (row.get("date") or "").strip(),
                    "start": start,
                    "end": end,
                    "customers": customer_count,
                    "wait": wait_minutes,
                    "data_status": (row.get("data_status") or "").strip().lower(),
                    "notes": (row.get("observer_notes") or "").strip().lower(),
                }
            )

        if not observations:
            raise ValueError("the CSV file has no observations")
        return observations


def average(total, count):
    return total / count if count else None


def analyze_observations(observations):
    slots = defaultdict(lambda: {"customers": 0, "wait": 0, "wait_count": 0, "count": 0})
    daily_hour_customers = defaultdict(int)

    for row in observations:
        slot = slots[(row["start"], row["end"])]
        slot["customers"] += row["customers"]
        slot["count"] += 1
        if row["wait"] is not None:
            slot["wait"] += row["wait"]
            slot["wait_count"] += 1

        date = row["date"] or "Unknown date"
        hour = row["start"][:2]
        daily_hour_customers[(date, hour)] += row["customers"]

    slot_averages = []
    for (start, end), totals in slots.items():
        slot_averages.append(
            {
                "start": start,
                "end": end,
                "customers": average(totals["customers"], totals["count"]),
                "wait": average(totals["wait"], totals["wait_count"]),
                "count": totals["count"],
            }
        )
    slot_averages.sort(key=lambda slot: slot["start"])

    hourly_totals = defaultdict(lambda: {"customers": 0, "days": 0})
    for (_, hour), customers in daily_hour_customers.items():
        hourly_totals[hour]["customers"] += customers
        hourly_totals[hour]["days"] += 1

    hourly_averages = [
        {
            "hour": hour,
            "customers": average(totals["customers"], totals["days"]),
        }
        for hour, totals in hourly_totals.items()
    ]
    hourly_averages.sort(key=lambda item: (-item["customers"], item["hour"]))
    return slot_averages, hourly_averages


def format_average(value):
    return f"{value:.1f}" if value is not None else "no data"


def build_summary(csv_file):
    observations = read_observations(csv_file)
    slot_averages, hourly_averages = analyze_observations(observations)
    peak_hour_customers = hourly_averages[0]["customers"]
    busiest_hours = [
        item for item in hourly_averages if item["customers"] == peak_hour_customers
    ]
    peak_slot_customers = max(slot["customers"] for slot in slot_averages)
    busiest_slots = [
        slot for slot in slot_averages if slot["customers"] == peak_slot_customers
    ]
    dates = {row["date"] for row in observations if row["date"]}
    waits = [row["wait"] for row in observations if row["wait"] is not None]
    estimated = any(
        row["data_status"] in {"assumed/simulated", "simulated", "estimated"}
        or "estimated values" in row["notes"]
        or "absence of field measurements" in row["notes"]
        for row in observations
    )
    return {
        "dataset": csv_file.name,
        "observation_count": len(observations),
        "day_count": len(dates) or 1,
        "average_wait": average(sum(waits), len(waits)),
        "estimated": estimated,
        "busiest_hours": [
            {
                "label": f"{int(item['hour']):02d}:00-{int(item['hour']) + 1:02d}:00",
                "customers_per_day": item["customers"],
            }
            for item in busiest_hours
        ],
        "busiest_slots": busiest_slots,
        "slots": slot_averages,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Summarize customer flow and busiest hours at Chenab Printers."
    )
    parser.add_argument(
        "csv_file",
        nargs="?",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help=f"CSV file to analyze (default: {DEFAULT_DATA_FILE.name})",
    )
    args = parser.parse_args()

    try:
        summary = build_summary(args.csv_file)
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        print(f"Could not analyze {args.csv_file}: {error}", file=sys.stderr)
        return 1

    print("Chenab Printers - Peak-hour analysis")
    print(
        f"Based on {summary['observation_count']} observations across "
        f"{summary['day_count']} day(s) in {summary['dataset']}."
    )
    print("\nBusiest hour(s), by average customers per day:")
    for item in summary["busiest_hours"]:
        print(
            f"  {item['label']}: "
            f"{format_average(item['customers_per_day'])} customers per day"
        )

    print("\nBusiest time slot(s), on average:")
    for slot in summary["busiest_slots"]:
        print(
            f"  {slot['start']}-{slot['end']}: "
            f"{format_average(slot['customers'])} customers, "
            f"{format_average(slot['wait'])} min wait"
        )

    print("\nAverage customer flow by time slot:")
    print(f"{'Time slot':<17} {'Avg customers':>13} {'Avg wait (min)':>15} {'Observations':>13}")
    for slot in summary["slots"]:
        time_slot = f"{slot['start']}-{slot['end']}"
        print(
            f"{time_slot:<17} "
            f"{format_average(slot['customers']):>13} "
            f"{format_average(slot['wait']):>15} "
            f"{slot['count']:>13}"
        )

    if summary["estimated"]:
        print(
            "\nNote: The CSV marks these values as estimates. "
            "This summary reflects the file and is not confirmation of measured traffic."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
