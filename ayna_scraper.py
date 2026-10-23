#!/usr/bin/env python3
"""
Download every bus route from the AYNA (Baku transport agency) map API.

Endpoints used:
  GET /api/bus/getBusList          -> [{id, number}, ...]
  GET /api/bus/getBusById?id=N     -> full route detail (stops, shapes, fare...)
  GET /api/stop/getAll             -> [{id, latitude, longitude, isTransportHub}, ...]

Output (in ./ayna_data/):
  raw/bus_<id>.json   untouched API response per bus (lets you re-run offline)
  all_buses.json      every bus detail in one list
  buses.csv           one row per bus: number, carrier, endpoints, fare, length...
  stops.csv           every stop with its NAME (getAll has no names) + routes serving it
  bus_stops.csv       ordered stop sequence per bus and direction
  routes.geojson      route polylines (one LineString per bus per direction)
  ayna.db             SQLite database with all of the above (see SCHEMA below)
  failed.txt          ids that could not be fetched (only if any failed)

Standard library only. Usage:
  python ayna_scraper.py                 # fetch everything
  python ayna_scraper.py --workers 2     # gentler on the server
  python ayna_scraper.py --refresh       # ignore cached raw files and re-download
"""

import argparse
import csv
import json
import os
import sqlite3
import time
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = "https://map-api.ayna.gov.az/api"
HEADERS = {"User-Agent": "Mozilla/5.0 (ayna-scraper)", "Accept": "application/json"}
OUT = Path("ayna_data")
RAW = OUT / "raw"


SCHEMA = """
CREATE TABLE buses (
    bus_id             INTEGER PRIMARY KEY,   -- internal API id (17 = route 21)
    number             TEXT NOT NULL,         -- route number shown on the bus
    carrier            TEXT,
    first_point        TEXT,
    last_point         TEXT,
    route_length_km    REAL,
    duration_min       INTEGER,
    tariff_qepik       INTEGER,
    tariff_azn         REAL,
    payment_type       TEXT,
    region             TEXT,
    working_zone       TEXT,
    card_payment_since TEXT,
    stops_dir1         INTEGER,
    stops_dir2         INTEGER
);
CREATE TABLE stops (
    stop_id     INTEGER PRIMARY KEY,
    code        TEXT,
    name        TEXT,
    lat         REAL,
    lon         REAL,
    is_hub      INTEGER,                      -- 0/1
    route_count INTEGER
);
CREATE TABLE bus_stops (                      -- ordered stops per route and direction
    bus_id     INTEGER NOT NULL REFERENCES buses(bus_id),
    direction  INTEGER NOT NULL,              -- 1 = outbound, 2 = return
    seq        INTEGER NOT NULL,              -- 1-based order along the route
    stop_id    INTEGER REFERENCES stops(stop_id),
    stop_code  TEXT,
    stop_name  TEXT,
    PRIMARY KEY (bus_id, direction, seq)
);
CREATE TABLE routes (                         -- one row per route direction
    bus_id      INTEGER NOT NULL REFERENCES buses(bus_id),
    direction   INTEGER NOT NULL,
    destination TEXT,
    point_count INTEGER,
    geojson     TEXT,                         -- LineString geometry as GeoJSON
    PRIMARY KEY (bus_id, direction)
);
CREATE TABLE route_points (                   -- same shapes, one row per vertex
    bus_id    INTEGER NOT NULL,
    direction INTEGER NOT NULL,
    seq       INTEGER NOT NULL,
    lat       REAL NOT NULL,
    lon       REAL NOT NULL,
    PRIMARY KEY (bus_id, direction, seq)
);
CREATE INDEX idx_bus_stops_stop ON bus_stops(stop_id);
CREATE INDEX idx_buses_number   ON buses(number);

-- Convenience view: which route numbers serve each stop
CREATE VIEW stop_routes AS
SELECT DISTINCT s.stop_id, s.name AS stop_name, b.number AS bus_number, bs.direction
FROM bus_stops bs
JOIN stops s ON s.stop_id = bs.stop_id
JOIN buses b ON b.bus_id = bs.bus_id;
"""


def write_sqlite(path, bus_rows, stop_rows, seq_rows, route_rows):
    """Build a fresh database in a temp file, then swap it in atomically."""
    tmp = path.with_suffix(".db.tmp")
    if tmp.exists():
        tmp.unlink()
    con = sqlite3.connect(tmp)
    try:
        con.executescript(SCHEMA)
        con.executemany(
            "INSERT INTO buses VALUES (:bus_id,:number,:carrier,:first_point,:last_point,"
            ":route_length_km,:duration_min,:tariff_qepik,:tariff_azn,:payment_type,:region,"
            ":working_zone,:card_payment_since,:stops_dir1,:stops_dir2)",
            bus_rows,
        )
        con.executemany(
            "INSERT OR REPLACE INTO stops VALUES (?,?,?,?,?,?,?)",
            [(r["stop_id"], r["code"] or None, r["name"] or None, r["lat"], r["lon"],
              int(bool(r["is_hub"])), r["route_count"])
             for r in stop_rows if r["stop_id"] is not None],
        )
        con.executemany(
            "INSERT OR REPLACE INTO bus_stops VALUES (?,?,?,?,?,?)",
            [(r["bus_id"], r["direction"], r["seq"], r["stop_id"], r["stop_code"], r["stop_name"])
             for r in seq_rows],
        )
        for bus_id, direction, destination, coords in route_rows:
            geom = json.dumps({"type": "LineString", "coordinates": coords})
            con.execute("INSERT OR REPLACE INTO routes VALUES (?,?,?,?,?)",
                        (bus_id, direction, destination, len(coords), geom))
            con.executemany("INSERT OR REPLACE INTO route_points VALUES (?,?,?,?,?)",
                            [(bus_id, direction, i, lat, lon)
                             for i, (lon, lat) in enumerate(coords, 1)])
        con.commit()
    finally:
        con.close()
    os.replace(tmp, path)


def fetch_json(url, retries=4, timeout=30):
    """GET a URL and parse JSON, retrying with exponential backoff."""
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"{url}: {last_err}")


def get_bus(bus_id, refresh, delay):
    """Return one bus's detail, using the cached raw file when present."""
    path = RAW / f"bus_{bus_id}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    data = fetch_json(f"{BASE}/bus/getBusById?id={bus_id}")
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    time.sleep(delay)
    return data


def name_of(obj):
    return (obj or {}).get("name")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--delay", type=float, default=0.3, help="seconds between requests per worker")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)

    # 1. Bus list
    bus_list = fetch_json(f"{BASE}/bus/getBusList")
    (OUT / "bus_list.json").write_text(json.dumps(bus_list, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Bus list: {len(bus_list)} routes")

    # 2. Every bus detail
    buses, failed = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(get_bus, b["id"], args.refresh, args.delay): b for b in bus_list}
        for i, fut in enumerate(as_completed(futures), 1):
            b = futures[fut]
            try:
                data = fut.result()
                if data and data.get("id") is not None:
                    buses.append(data)
                else:
                    failed.append((b["id"], b["number"], "empty response"))
            except Exception as e:
                failed.append((b["id"], b["number"], str(e)))
            print(f"\r  fetched {i}/{len(bus_list)}  (failed: {len(failed)})", end="", flush=True)
    print()

    # Keep the same order as the official list
    order = {b["id"]: i for i, b in enumerate(bus_list)}
    buses.sort(key=lambda b: order.get(b["id"], 1e9))
    (OUT / "all_buses.json").write_text(json.dumps(buses, ensure_ascii=False), encoding="utf-8")

    # 3. All stops (coordinates only)
    try:
        all_stops = fetch_json(f"{BASE}/stop/getAll")
    except Exception as e:
        print(f"Warning: stop/getAll failed ({e}); stops.csv will only contain stops seen on routes")
        all_stops = []

    # 4. Flatten
    stop_info = {}                        # stop_id -> dict
    stop_routes = defaultdict(set)        # stop_id -> {bus numbers}

    for s in all_stops:
        stop_info[s["id"]] = {
            "stop_id": s["id"], "code": "", "name": "",
            "lat": float(s["latitude"]), "lon": float(s["longitude"]),
            "is_hub": s.get("isTransportHub", False),
        }

    bus_rows, seq_rows, features, route_rows = [], [], [], []
    for b in buses:
        stops = b.get("stops") or []
        dir_counts = defaultdict(int)
        seq_counter = defaultdict(int)

        for st in stops:
            d = st.get("directionTypeId")
            dir_counts[d] += 1
            seq_counter[d] += 1
            inner = st.get("stop") or {}
            sid = st.get("stopId") or inner.get("id")

            info = stop_info.setdefault(sid, {
                "stop_id": sid, "code": "", "name": "",
                "lat": float(inner["latitude"]) if inner.get("latitude") else None,
                "lon": float(inner["longitude"]) if inner.get("longitude") else None,
                "is_hub": inner.get("isTransportHub", False),
            })
            info["code"] = info["code"] or inner.get("code") or st.get("stopCode") or ""
            info["name"] = info["name"] or (inner.get("name") or st.get("stopName") or "").strip()
            stop_routes[sid].add(b.get("number"))

            seq_rows.append({
                "bus_id": b["id"], "bus_number": b.get("number"),
                "direction": d, "seq": seq_counter[d],
                "stop_id": sid, "stop_code": st.get("stopCode"),
                "stop_name": (st.get("stopName") or "").strip(),
                "lat": inner.get("latitude"), "lon": inner.get("longitude"),
            })

        tariff = b.get("tariff")
        bus_rows.append({
            "bus_id": b["id"],
            "number": b.get("number"),
            "carrier": b.get("carrier"),
            "first_point": (b.get("firstPoint") or "").strip(),
            "last_point": (b.get("lastPoint") or "").strip(),
            "route_length_km": b.get("routLength"),
            "duration_min": b.get("durationMinuts"),
            "tariff_qepik": tariff,
            "tariff_azn": tariff / 100 if isinstance(tariff, (int, float)) else None,
            "payment_type": name_of(b.get("paymentType")),
            "region": name_of(b.get("region")),
            "working_zone": name_of(b.get("workingZoneType")),
            "card_payment_since": b.get("cardPaymentDate"),
            "stops_dir1": dir_counts.get(1, 0),
            "stops_dir2": dir_counts.get(2, 0),
        })

        for r in b.get("routes") or []:
            coords = [[p["lng"], p["lat"]] for p in r.get("flowCoordinates") or []]
            if len(coords) < 2:
                continue
            route_rows.append((b["id"], r.get("directionTypeId"), r.get("destination"), coords))
            features.append({
                "type": "Feature",
                "properties": {
                    "bus_id": b["id"], "number": b.get("number"),
                    "direction": r.get("directionTypeId"),
                    "destination": r.get("destination"),
                    "carrier": b.get("carrier"),
                },
                "geometry": {"type": "LineString", "coordinates": coords},
            })

    # 5. Write files
    def write_csv(path, rows):
        if not rows:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: Excel shows ə/ş/ç correctly
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    write_csv(OUT / "buses.csv", bus_rows)
    write_csv(OUT / "bus_stops.csv", seq_rows)

    stop_rows = []
    for sid, info in sorted(stop_info.items(), key=lambda kv: (kv[0] is None, kv[0] or 0)):
        routes = sorted(stop_routes.get(sid, []), key=lambda n: (len(str(n)), str(n)))
        stop_rows.append({**info, "route_count": len(routes), "routes": " ".join(map(str, routes))})
    write_csv(OUT / "stops.csv", stop_rows)

    (OUT / "routes.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8",
    )

    write_sqlite(OUT / "ayna.db", bus_rows, stop_rows, seq_rows, route_rows)

    if failed:
        (OUT / "failed.txt").write_text(
            "\n".join(f"{i}\t{n}\t{e}" for i, n, e in failed), encoding="utf-8"
        )

    unnamed = sum(1 for r in stop_rows if not r["name"])
    print(f"Buses saved:   {len(bus_rows)}")
    print(f"Stops saved:   {len(stop_rows)}  ({unnamed} not served by any route, so no name)")
    print(f"Stop sequence: {len(seq_rows)} rows")
    print(f"Route shapes:  {len(features)}")
    if failed:
        print(f"Failed:        {len(failed)} (see failed.txt; re-run to retry, cached ones are skipped)")
    print(f"SQLite:        {(OUT / 'ayna.db').resolve()}")
    print(f"Output folder: {OUT.resolve()}")


if __name__ == "__main__":
    main()
