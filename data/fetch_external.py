#!/usr/bin/env python3
"""
Download every external dataset the measurements use into data/external/.

All of these files are committed to git, so results can be regenerated without the
internet. Run this only to refresh them or to rebuild a missing file. Sources and
licences are listed in data/SOURCES.md.

Standard library only. Usage (from the repository root):
  python3 data/fetch_external.py                 # download files that are missing
  python3 data/fetch_external.py --refresh       # download everything again
  python3 data/fetch_external.py --only osm      # one group: kontur, opendata, stat, osm
"""

import argparse
import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / "external"
HEADERS = {"User-Agent": "route_efficiency/0.1 (bus network research)", "Accept": "*/*"}
OPENDATA = "https://admin.opendata.az/dataset"
AZSTAT = "https://www.azstat.gov.az/AsisOpenDataApi/csv?lang=az&table_id="

FILES = [
    # group, path under data/external, url
    ("kontur", "kontur/kontur_population_AZ_20231101.gpkg",
     "https://geodata-eu-central-1-kontur-public.s3.amazonaws.com/kontur_datasets/kontur_population_AZ_20231101.gpkg.gz"),
    ("opendata", "opendata/bakubus_passenger-2026.csv",
     f"{OPENDATA}/32766a9d-479c-41ff-a660-7b739b4ff034/resource/bbed6c16-79dc-4b3d-a0b6-b0411dcda473/download/bakubus_passenger-2026.csv"),
    ("opendata", "opendata/bakubus_payment_type-2026.csv",
     f"{OPENDATA}/a98b2492-680a-401a-ab39-4e2b6ad0f270/resource/578ff0f7-7096-47c3-a682-f3e621fff622/download/bakubus_payment_type.csv"),
    ("opendata", "opendata/metro_passengers-2025.csv",
     f"{OPENDATA}/66051a52-1172-4c59-8ea2-1062562c991f/resource/7f84c392-bee9-4fce-8fde-d60e53520913/download/passenger_2025.csv"),
    ("opendata", "opendata/metro_passengers-2026.csv",
     f"{OPENDATA}/66051a52-1172-4c59-8ea2-1062562c991f/resource/01d12a6f-c4d9-4bb3-a0e2-01b244ca9c00/download/passenger-2026.csv"),
    ("opendata", "opendata/metro_payment_type-2026.csv",
     f"{OPENDATA}/2d3f1d95-5465-4e54-a14e-555c02785729/resource/d0893636-47a2-43c3-95c2-eb7e54cb54d9/download/payment-type_2026.csv"),
    ("opendata", "opendata/metro_exits.csv",
     f"{OPENDATA}/3108fb32-8483-4126-8283-17f2f1452548/resource/6540e9a6-97d5-41c6-a05a-3365ed69805a/download/pathways.csv"),
    ("opendata", "opendata/ayna_buslines.kmz",
     f"{OPENDATA}/366c03c3-f60a-4198-b8e4-959af2082296/resource/df2edcdc-2af2-4f78-8c49-d6c5b78402b6/download/buslines.kmz"),
    ("opendata", "opendata/ayna_bus_stations.geojson",
     f"{OPENDATA}/0d42439f-191f-40f5-82df-21742123465e/resource/7e03227f-15bd-44e8-bea3-7012f2914097/download/map.geojson"),
    ("opendata", "opendata/stat_avg_trip_distance.csv", AZSTAT + "DT_BJ_050"),
    ("opendata", "opendata/stat_passengers_by_mode.csv", AZSTAT + "DT_BJ_004"),
    ("opendata", "opendata/stat_urban_electric_transport.csv", AZSTAT + "DT_BJ_049"),
    ("stat", "stat/population_by_district_2026.xls", "https://www.stat.gov.az/source/demoqraphy/en/001_15en.xls"),
]

# OpenStreetMap through the Overpass API, for the Absheron peninsula.
BBOX = "39.9,49.3,40.7,50.45"
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
OSM_QUERIES = [
    ("osm/osm_bus_routes_tags.json", f'relation["type"="route"]["route"~"^(bus|trolleybus|minibus)$"]({BBOX});out tags;'),
    ("osm/osm_education.json", f'nwr["amenity"~"^(school|university|college|kindergarten)$"]({BBOX});out center tags;'),
    ("osm/osm_health.json", f'nwr["amenity"~"^(hospital|clinic)$"]({BBOX});out center tags;'),
    ("osm/osm_shopping.json", f'(nwr["shop"~"^(mall|supermarket|department_store)$"]({BBOX});'
                              f'nwr["amenity"="marketplace"]({BBOX}););out center tags;'),
    ("osm/osm_offices.json", f'(nwr["office"]({BBOX});nwr["amenity"~"^(townhall|courthouse)$"]({BBOX}););out center tags;'),
    ("osm/osm_transport.json", f'(nwr["railway"="station"]({BBOX});nwr["amenity"="bus_station"]({BBOX}););out center tags;'),
]


def fetch(url, data=None, timeout=300, tries=3):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def save(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(body)
    tmp.replace(path)
    print(f"  wrote {path.relative_to(OUT.parent.parent)} ({len(body) / 1024:,.0f} KB)")


def overpass(query):
    """Run a query on the first Overpass server that answers with valid JSON."""
    body = urllib.parse.urlencode({"data": f"[out:json][timeout:280];{query}"}).encode()
    errors = []
    for server in OVERPASS_SERVERS:
        try:
            raw = fetch(server, body, timeout=320, tries=2)
            json.loads(raw)
            return raw
        except (RuntimeError, ValueError) as e:
            errors.append(f"{server}: {e}")
    raise RuntimeError("; ".join(errors))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true", help="download files that already exist too")
    ap.add_argument("--only", choices=["kontur", "opendata", "stat", "osm"])
    args = ap.parse_args()
    failed = []
    for group, rel, url in FILES:
        path = OUT / rel
        if (args.only and args.only != group) or (path.exists() and not args.refresh):
            continue
        print(f"{group}: {rel}")
        try:
            body = fetch(url)
            save(path, gzip.decompress(body) if url.endswith(".gz") else body)
        except RuntimeError as e:
            failed.append(f"{rel}: {e}")
    for rel, query in OSM_QUERIES:
        path = OUT / rel
        if (args.only and args.only != "osm") or (path.exists() and not args.refresh):
            continue
        print(f"osm: {rel}")
        try:
            save(path, overpass(query))
        except RuntimeError as e:
            failed.append(f"{rel}: {e}")
        time.sleep(2)
    if failed:
        print("\nFailed (run again later):\n  " + "\n  ".join(failed))
    else:
        print("\nAll external data present.")


if __name__ == "__main__":
    main()
