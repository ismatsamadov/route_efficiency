"""Check the two GTFS feeds with MobilityData's canonical GTFS validator.

    python3 validate_gtfs.py --jar gtfs-validator-8.0.1-cli.jar

The validator is a Java program (Java 17 or later) that is not part of the repository;
its command-line jar is on https://github.com/MobilityData/gtfs-validator/releases. Each
feed in output/redesign/ is checked with the country code AZ and a fixed validation date,
and two files are written to output/gtfs_validation/:

  notices.csv                every kind of notice the validator raised, and how many
  stops_far_from_shape.csv   the stops it found more than 100 m from their trip's shape
"""

import argparse
import csv
import io
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from busnet.metrics import _route_key                                          # noqa: E402

FEEDS_DIR = ROOT / "output" / "redesign"
OUT = ROOT / "output" / "gtfs_validation"
FEEDS = ("today", "redesign")
SEVERITY = {"ERROR": 0, "WARNING": 1, "INFO": 2}


def trips_of(feed):
    """{trip id: (route number, direction 1 or 2)} from a feed's routes.txt and trips.txt."""
    with zipfile.ZipFile(feed) as z:
        def rows(name):
            return csv.DictReader(io.StringIO(z.read(name).decode("utf-8")))
        number = {r["route_id"]: r["route_short_name"] for r in rows("routes.txt")}
        return {t["trip_id"]: (number[t["route_id"]], int(t["direction_id"]) + 1) for t in rows("trips.txt")}


def validate(java, jar, feed, date):
    with tempfile.TemporaryDirectory() as tmp:
        run = subprocess.run([java, "-jar", str(jar), "-i", str(feed), "-o", tmp, "-c", "az", "-d", date, "-svu"],
                             capture_output=True, text=True)
        if run.returncode:                       # the validator logs to stderr; show it only when it fails
            sys.exit(f"the validator failed on {feed.name}:\n{run.stderr}")
        return json.loads((Path(tmp) / "report.json").read_text(encoding="utf-8"))


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:            # like every output CSV, for Excel
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description="Check the GTFS feeds with MobilityData's GTFS validator.")
    ap.add_argument("--jar", required=True, help="the validator's command-line jar")
    ap.add_argument("--java", default="java", help="a Java 17 or later executable (default: java on the PATH)")
    ap.add_argument("--date", default="2026-10-26", help="date for the validator's date rules (default: %(default)s)")
    args = ap.parse_args()
    notices, stops = [], []
    for name in FEEDS:
        feed = FEEDS_DIR / f"gtfs_{name}.zip"
        report = validate(args.java, args.jar, feed, args.date)
        version = report["summary"]["validatorVersion"]
        trips = trips_of(feed)
        far = []
        for n in sorted(report["notices"], key=lambda n: (SEVERITY[n["severity"]], n["code"])):
            notices.append([name, version, n["severity"], n["code"], n["totalNotices"]])
            if n["code"] == "stop_too_far_from_shape":
                if n["totalNotices"] > len(n["sampleNotices"]):
                    print(f"  {name}: the report lists {len(n['sampleNotices'])} of {n['totalNotices']} far stops")
                for s in n["sampleNotices"]:
                    route, direction = trips[s["tripId"]]
                    far.append([name, route, direction, s["stopId"], s["stopName"], round(s["geoDistanceToShape"])])
        stops += sorted(far, key=lambda r: (_route_key(r[1]), r[2], -r[5], r[3]))
        errors = sum(n["totalNotices"] for n in report["notices"] if n["severity"] == "ERROR")
        warnings = sum(n["totalNotices"] for n in report["notices"] if n["severity"] == "WARNING")
        print(f"gtfs_{name}.zip: {errors} errors, {warnings} warnings (validator {version})")
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "notices.csv", ["feed", "validator", "severity", "notice", "count"], notices)
    write_csv(OUT / "stops_far_from_shape.csv",
              ["feed", "route", "direction", "stop_id", "stop_name", "metres_from_shape"], stops)
    print(f"wrote {OUT / 'notices.csv'} and {OUT / 'stops_far_from_shape.csv'}")


if __name__ == "__main__":
    main()
