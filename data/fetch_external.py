#!/usr/bin/env python3
"""
Download every external dataset the measurements use into data/external/.

All of these files are committed to git, so results can be regenerated without the
internet. Run this only to refresh them or to rebuild a missing file. Sources and
licences are listed in data/SOURCES.md.

Standard library only. Usage (from the repository root):
  python3 data/fetch_external.py                 # download files that are missing
  python3 data/fetch_external.py --refresh       # download everything again
  python3 data/fetch_external.py --only osm      # one group: kontur, opendata, stat, osm, wikidata, utrp

The walking network (osm/osm_walk_network.json.gz) is cut from Geofabrik's daily extract
of Azerbaijan with osm_pbf.py, because a query for 100,000 ways is refused by the
Overpass servers whenever they are busy; the 47 MB extract itself is not kept.
"""

import argparse
import gzip
import http.client
import json
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import osm_pbf                                                                  # noqa: E402

OUT = Path(__file__).resolve().parent / "external"
GEOFABRIK = "https://download.geofabrik.de/asia/azerbaijan-latest.osm.pbf"
HEADERS = {"User-Agent": "route_efficiency/0.1 (bus network research)", "Accept": "*/*"}
OPENDATA = "https://admin.opendata.az/dataset"
AZSTAT = "https://www.azstat.gov.az/AsisOpenDataApi/csv?lang=az&table_id="

# Wikidata: every station on the three Baku Metro lines (red Q3832654, green Q3832656,
# purple Q25547220), with opening date and neighbouring stations.
METRO_SPARQL = """
SELECT ?item ?az ?en ?line ?opened ?coord ?adj ?towards WHERE {
  VALUES ?line { wd:Q3832654 wd:Q3832656 wd:Q25547220 }
  ?item wdt:P81 ?line .
  OPTIONAL { ?item wdt:P1619 ?opened }
  OPTIONAL { ?item wdt:P625 ?coord }
  OPTIONAL { ?item p:P197 ?a . ?a ps:P197 ?adj . OPTIONAL { ?a pq:P5051 ?towards } }
  OPTIONAL { ?item rdfs:label ?az FILTER(LANG(?az) = "az") }
  OPTIONAL { ?item rdfs:label ?en FILTER(LANG(?en) = "en") }
}
ORDER BY ?item ?line ?adj ?towards
"""
WIKIDATA = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(METRO_SPARQL)

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
    ("opendata", "opendata/ayna_bicycle_lanes.kmz",
     f"{OPENDATA}/74727856-3e72-4d49-ab34-9d4aac8f4ab0/resource/f0bccfe6-0639-46a7-8cfe-7e5f1be741d8/download/movcud-zolaqlar-velo.kmz"),
    ("opendata", "opendata/ayna_bicycle_parking.kmz",
     f"{OPENDATA}/8d61b508-7f13-4219-984f-08d769c61251/resource/6902ae9f-e2ae-4c20-bdee-6fd55c701645/download/mpv-v-mps.-son.kmz"),
    ("opendata", "opendata/stat_avg_trip_distance.csv", AZSTAT + "DT_BJ_050"),
    ("opendata", "opendata/stat_passengers_by_mode.csv", AZSTAT + "DT_BJ_004"),
    ("opendata", "opendata/stat_urban_electric_transport.csv", AZSTAT + "DT_BJ_049"),
    ("stat", "stat/population_by_district_2026.xls", "https://www.stat.gov.az/source/demoqraphy/en/001_15en.xls"),
    ("wikidata", "wikidata/metro_stations.json", WIKIDATA),
    # Mumford's (2013) benchmark networks and best route sets. Her Cardiff page now sits behind a
    # browser check, so the copy the Wayback Machine took on 16 December 2025 is read instead.
    ("utrp", "utrp/CEC2013Supp.zip",
     "http://web.archive.org/web/20251216204206id_/https://users.cs.cf.ac.uk/C.L.Mumford/Research%20Topics/UTRP/CEC2013Supp.zip"),
]

# OpenStreetMap through the Overpass API, for the Absheron peninsula.
BBOX = "39.9,49.3,40.7,50.45"
# The study area of the coverage measures: the served stops plus 2 km
# (busnet.population.stops_bbox on data/ayna.db), rounded outwards.
STUDY_BBOX = "39.92,49.37,40.66,50.39"
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
    # The metro: route relations with their stops in order and the track geometry, then
    # stations, stop positions and entrances.
    ("osm/osm_metro_routes.json", f'(relation["route"="subway"]({BBOX});relation["route_master"="subway"]({BBOX}););out body geom;'),
    ("osm/osm_metro_stations.json", f'(nwr["railway"="station"]["station"="subway"]({BBOX});'
                                    f'node["public_transport"="stop_position"]["subway"="yes"]({BBOX});'
                                    f'nwr["railway"="subway_entrance"]({BBOX}););out body center;'),
]
# Every highway in the study area with its tags and nodes, for walking distances along
# streets and paths (busnet/walking.py decides which ways can be walked): about 100,000
# ways and 570,000 nodes, in the shape of an Overpass answer, gzipped.
WALK_NETWORK = "osm/osm_walk_network.json.gz"


def fetch(url, data=None, timeout=300, tries=3):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, http.client.HTTPException) as e:   # a dropped connection too
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{url}: {last}")


def save(path, body):
    """Write body to path; a path ending in .gz is written gzip-compressed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".gz":
        body = gzip.compress(body, mtime=0)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(body)
    tmp.replace(path)
    print(f"  wrote {path.relative_to(OUT.parent.parent)} ({len(body) / 1024:,.0f} KB)")


def overpass(query):
    """Run a query on the first Overpass server that answers with valid JSON.

    Mirrors can lag the main server by months, so the date of the data is printed."""
    body = urllib.parse.urlencode({"data": f"[out:json][timeout:600][maxsize:1073741824];{query}"}).encode()
    errors = []
    for server in OVERPASS_SERVERS:
        try:
            raw = fetch(server, body, timeout=640, tries=3)
            answer = json.loads(raw)
            if not answer.get("elements") and answer.get("remark"):     # ran out of time or memory
                raise RuntimeError(answer["remark"])
            print(f"  {server}: OpenStreetMap data as of {answer.get('osm3s', {}).get('timestamp_osm_base', 'unknown')}")
            return raw
        except (RuntimeError, ValueError) as e:
            errors.append(f"{server}: {e}")
    raise RuntimeError("; ".join(errors))


def walk_network():
    """Every highway in the study area, cut from Geofabrik's extract of Azerbaijan."""
    with tempfile.TemporaryDirectory() as tmp:
        pbf = Path(tmp) / GEOFABRIK.rsplit("/", 1)[1]
        print(f"  downloading {GEOFABRIK}")
        pbf.write_bytes(fetch(GEOFABRIK, timeout=900))
        print(f"  {pbf.stat().st_size / 1e6:.1f} MB; reading it")
        answer = osm_pbf.extract(pbf, STUDY_BBOX, lambda tags: "highway" in tags and tags.get("area") != "yes")
    print(f"  OpenStreetMap data as of {answer['osm3s']['timestamp_osm_base']}")
    return json.dumps(answer, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--refresh", action="store_true", help="download files that already exist too")
    ap.add_argument("--only", choices=["kontur", "opendata", "stat", "osm", "wikidata", "utrp"])
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
    path = OUT / WALK_NETWORK
    if (not args.only or args.only == "osm") and (args.refresh or not path.exists()):
        print(f"osm: {WALK_NETWORK}")
        try:
            save(path, walk_network())
        except (RuntimeError, ValueError) as e:
            failed.append(f"{WALK_NETWORK}: {e}")
    if failed:
        print("\nFailed (run again later):\n  " + "\n  ".join(failed))
    else:
        print("\nAll external data present.")


if __name__ == "__main__":
    main()
