import argparse
import csv
import json
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
