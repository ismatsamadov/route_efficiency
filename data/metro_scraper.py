#!/usr/bin/env python3
"""
Download the Baku Metro's own network data from the public API behind metro.gov.az
(app-api.metro.gov.az), the metro's counterpart of the AYNA map API that gives the
bus network.

Saved to data/external/metro_api/, one file per response:
  stations_map.json         26 stations with coordinates and lines (the two Memar Əcəmi
                            stations are one transfer station here), and line geometries
  lines.json                line geometries
  lines_summary.json        lines, the train services on each and the closures in force
  line_<id>.json            each line's services with their stations in order
  station_connections.json  links between stations, walking transfers and bus bridges
  warnings.json             service notices
  schedule.json             published departure times (only some terminals)
  faq.json                  the operator's answers on intervals, opening hours and fares
  journeys/<a>-<b>.json     the journey planner from the first to the last station of
                            each service and back: arrival time at every station and the
                            next three departures

Only read-only requests and the journey planner that the public site calls are used,
with a pause between requests. The planner answers for the next trains (the first
morning trains at night) whatever departure time it is given, so the arrival times move
with the time of the run; the differences between them, the running times, do not.

Standard library only. Usage (from the repository root):
  python3 data/metro_scraper.py
"""

import datetime
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://app-api.metro.gov.az"
# Names come in the language asked for (English by default); Azerbaijani matches the
# operator's files on opendata.az.
HEADERS = {"User-Agent": "route_efficiency/0.1 (bus network research)", "Accept": "application/json",
           "Accept-Language": "az"}
OUT = Path(__file__).resolve().parent / "external" / "metro_api"
PAUSE_S = 1.0


def request(path, payload=None, retries=3):
    """GET (or POST `payload` as JSON) and parse the answer, retrying with backoff."""
    data = None if payload is None else json.dumps(payload).encode()
    headers = HEADERS if payload is None else {**HEADERS, "Content-Type": "application/json"}
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(BASE + path, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            time.sleep(PAUSE_S)
            return body
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{path}: {last}")


def save(name, body):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"  {path.relative_to(OUT.parent.parent.parent)}")


def main():
    print(f"Baku Metro API, {datetime.datetime.now():%Y-%m-%d %H:%M}:")
    save("stations_map.json", request("/route/api/routes/stations/map"))
    save("lines.json", request("/route/api/routes/lines"))
    summary = request("/route/api/routes/lines/summary")
    save("lines_summary.json", summary)
    save("station_connections.json", request("/route/api/stationConnection"))
    save("warnings.json", request("/route/api/routes/warning"))
    save("schedule.json", request("/route/api/Schedule"))
    save("faq.json", request("/web/api/FaqItem?languageId=1"))
    now = datetime.datetime.now().replace(microsecond=0).isoformat()
    for line in summary:
        detail = request(f"/route/api/routes/lines/{line['id']}/stations/detailed")
        save(f"line_{line['id']}.json", detail)
        for seg in detail["segments"]:
            first, last = seg["stations"][0]["id"], seg["stations"][-1]["id"]
            for a, b in ((first, last), (last, first)):
                body = {"sourceStationId": a, "destinationStationId": b, "departureTime": now,
                        "preferLessTransfers": True, "calculateWithBus": False}
                save(f"journeys/{a}-{b}.json", request("/route/api/routes/calculate", body))


if __name__ == "__main__":
    main()
