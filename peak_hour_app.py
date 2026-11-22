import argparse
import csv
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from peak_hour_analyzer import DEFAULT_DATA_FILE, build_summary


class AnalyzerHandler(BaseHTTPRequestHandler):
    csv_file = DEFAULT_DATA_FILE
    page_file = Path(__file__).with_name("peak_hour_app.html")

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            self.send_file(self.page_file, "text/html; charset=utf-8")
        elif path == "/api/summary":
            self.send_summary()
        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        path = urlsplit(self.path).path
        if path != "/api/observations":
            self.send_error(404, "Not found")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length))
            record = self.validate_record(payload)
            self.append_record(record)
            summary = build_summary(self.csv_file)
            self.send_json(201, summary)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError, OSError, csv.Error) as error:
            message = str(error) if str(error) else "Invalid request"
            self.send_json(400, {"error": message})

    def validate_record(self, payload):
        required = ("date", "time_slot_start", "time_slot_end", "customer_count", "estimated_wait_minutes")
        missing = [field for field in required if payload.get(field) in (None, "")]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        try:
            date = datetime.strptime(str(payload["date"]), "%Y-%m-%d").date().isoformat()
            start = datetime.strptime(str(payload["time_slot_start"]), "%H:%M").strftime("%H:%M")
            end = datetime.strptime(str(payload["time_slot_end"]), "%H:%M").strftime("%H:%M")
            customers = int(payload["customer_count"])
            wait = int(payload["estimated_wait_minutes"])
        except (TypeError, ValueError) as error:
            raise ValueError("Date, time, customer count, or wait time is invalid") from error

        if customers < 0 or wait < 0:
            raise ValueError("Customer count and wait time must be zero or greater")
        if end <= start:
            raise ValueError("Time slot end must be after time slot start")

        return {
            "date": date,
            "day_of_week": datetime.strptime(date, "%Y-%m-%d").strftime("%A"),
            "time_slot_start": start,
            "time_slot_end": end,
            "customer_count": customers,
            "estimated_wait_minutes": wait,
        }

    def append_record(self, record):
        with self.csv_file.open(newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.DictReader(csv_file)
            fieldnames = reader.fieldnames
            if not fieldnames:
                raise ValueError("the CSV file is empty")

        with self.csv_file.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            next_observation_id = 1
            with self.csv_file.open(newline="", encoding="utf-8-sig") as source:
                for row in csv.DictReader(source):
                    try:
                        next_observation_id = max(next_observation_id, int(row.get("observation_id") or 0) + 1)
                    except ValueError:
                        pass

            complete_record = {field: "" for field in fieldnames}
            complete_record.update(record)
            complete_record["observation_id"] = next_observation_id
            complete_record["data_status"] = "measured"
            complete_record["observer_notes"] = "Entered through dashboard"
            writer.writerow(complete_record)

    def send_file(self, path, content_type):
        try:
            content = path.read_bytes()
        except OSError as error:
            self.send_error(500, f"Could not read the app page: {error}")
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def send_summary(self):
        try:
            summary = build_summary(self.csv_file)
        except (OSError, UnicodeError, csv.Error, ValueError) as error:
            self.send_json(500, {"error": f"Could not analyze {self.csv_file}: {error}"})
            return
        self.send_json(200, summary)

    def send_json(self, status, data):
        content = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format_string, *args):
        print(f"{self.address_string()} - {format_string % args}")

def main():
    parser = argparse.ArgumentParser(
        description="Open the Chenab Printers peak-hour dashboard."
    )
    parser.add_argument(
        "csv_file",
        nargs="?",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help=f"CSV file to analyze (default: {DEFAULT_DATA_FILE.name})",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    AnalyzerHandler.csv_file = args.csv_file
    try:
        server = HTTPServer((args.host, args.port), AnalyzerHandler)
    except OSError as error:
        parser.error(f"could not start server: {error}")

    print(f"Dashboard ready at http://{args.host}:{args.port}/")
    print(f"Reading data from {args.csv_file}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
