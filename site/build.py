#!/usr/bin/env python3
"""
Build the data behind index.html, the one-page summary of the results served by GitHub Pages.

Reads the committed results in output/ and the network in data/ayna.db, repaired the same
way measure.py repairs it, and writes to ./site/ (or --out):
  data.js         routes, stops, detours with a shorter path where streets allow one,
                  near-duplicates, corridors, closely spaced stops, carriers, the people
                  who live farther than coverage_radius_m from a stop, the coverage at the
                  five radii recorded in output/robustness/coverage_radius.csv, and the
                  defects found in AYNA's map data, as one JavaScript object that index.html reads
  checklist.xlsx  the same lists as a workbook to go through line by line
  og.png          with --og: the 1200x630 picture that link previews show, drawn from
                  site/og.html by Google Chrome, headless

The numbers come from output/. What the page needs beyond them (route geometry, where each
detour runs and the shorter path the redesign search would use, the gap at each closely
spaced stop, people per population hexagon) is recomputed with the code that wrote output/,
and the script stops if a recomputed figure disagrees with output/. Run measure.py with
--scenario stop-balancing --min-gap 250 first after any change to the data or the settings.

Standard library only (Chrome only for --og). Usage:
  python3 site/build.py
  python3 site/build.py --og
"""

import argparse
import csv
import json
import math
import re
import sqlite3
import statistics
import struct
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from busnet.config import load_config                                          # noqa: E402
from busnet.geo import PROJ, Polyline, haversine_m                              # noqa: E402
from busnet.graph import StopIndex                                              # noqa: E402
from busnet.metrics import ZONE_EN, _route_key, find_detours                    # noqa: E402
from busnet.model import load_network                                           # noqa: E402
from busnet.optimize import Streets                                             # noqa: E402
from busnet.population import SPLIT, _gpkg_shape, _mercator_to_latlon, stops_bbox  # noqa: E402
from busnet.ridership import latest_month, load_daily_boardings, weekday_mean  # noqa: E402

# When the map data was taken; data.md explains both dates.
SCRAPED = "2026-10-23"
SAME_AS = "2026-05-06"
REPOSITORY = "https://github.com/ismatsamadov/route_efficiency"
PAGE = "https://ismatsamadov.github.io/route_efficiency/"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SHAPE_CLASSES = ["direct", "indirect", "very indirect", "loop"]
REGION_EN = {"Bakı": "Baku", "Sumqayıt": "Sumqayit"}
LINE_TOLERANCE_M = 6.0        # simplification of route lines; invisible below street level
SHORTER_BY_M = 500.0          # a shorter path counts only if it saves this much, as in optimize.candidates


# ---------------------------------------------------------------- reading output/

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def num(text):
    """A CSV cell as a number, or None when it is empty."""
    if text in ("", None):
        return None
    v = float(text)
    return int(v) if v.is_integer() and "." not in text else v


def check(label, ours, theirs, tol=1e-6):
    if not math.isclose(ours, theirs, rel_tol=tol, abs_tol=tol):
        sys.exit(f"{label}: recomputed {ours} but output/ has {theirs}; run measure.py first")


# ---------------------------------------------------------------- geometry

def simplify(points, tol_m):
    """Douglas-Peucker on (lat, lon) points with a tolerance in metres."""
    if len(points) < 3:
        return list(points)
    xy = [PROJ.to_xy(a, b) for a, b in points]
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        (ax, ay), (bx, by) = xy[i], xy[j]
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        far, k = -1.0, None
        for m in range(i + 1, j):
            px, py = xy[m]
            t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
            d = math.hypot(px - ax - t * dx, py - ay - t * dy)
            if d > far:
                far, k = d, m
        if k is not None and far > tol_m:
            keep[k] = True
            stack += [(i, k), (k, j)]
    return [p for p, kept in zip(points, keep) if kept]


def encode(points):
    """(lat, lon) points as an encoded polyline: Google's format, 5 decimals."""
    out, last = [], (0, 0)
    for lat, lon in points:
        cur = (round(lat * 1e5), round(lon * 1e5))
        for v in (cur[0] - last[0], cur[1] - last[1]):
            v = ~(v << 1) if v < 0 else v << 1
            while v >= 0x20:
                out.append(chr((0x20 | (v & 0x1F)) + 63))
                v >>= 5
            out.append(chr(v + 63))
        last = cur
    return "".join(out)


def line(points):
    return encode(simplify(points, LINE_TOLERANCE_M))


class Paths:
    """The drawn path of a pattern between two of its stops."""

    def __init__(self):
        self.cache = {}

    def between(self, p, i, j):
        key = (p.route_id, p.direction)
        if key not in self.cache:
            self.cache[key] = Polyline(p.path)
        return self.cache[key].slice_latlon(p.chainage_m[i], p.chainage_m[j])


def _ring(blob):
    """Outer ring of a GeoPackage polygon, in the layer's own coordinates."""
    flags = blob[3]
    env_len = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(flags >> 1) & 7]
    wkb = blob[8 + env_len:]
    order = "<" if wkb[0] == 1 else ">"
    if struct.unpack(order + "I", wkb[1:5])[0] % 1000 == 6:          # multipolygon: the first polygon
        wkb = wkb[9:]
        order = "<" if wkb[0] == 1 else ">"
    npts = struct.unpack(order + "I", wkb[9:13])[0]
    coords = struct.unpack(order + f"{2 * npts}d", wkb[13:13 + 16 * npts])
    return list(zip(coords[0::2], coords[1::2]))


def hexagons(path, bbox):
    """[(ring as (lat, lon), [(lat, lon, people)])]: each population hexagon with the seven
    parts that population.load_gpkg makes of it, keeping only parts inside bbox."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    table, geom_col, srs = con.execute(
        "SELECT c.table_name, g.column_name, g.srs_id FROM gpkg_contents c "
        "JOIN gpkg_geometry_columns g ON g.table_name = c.table_name "
        "WHERE c.data_type = 'features' LIMIT 1").fetchone()
    cols = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
    pop_col = next(c for c in cols if c.lower() in ("population", "pop", "people"))

    def latlon(x, y):
        return _mercator_to_latlon(x, y) if srs == 3857 else (y, x)

    out = []
    for blob, pop in con.execute(f'SELECT "{geom_col}", "{pop_col}" FROM "{table}"'):
        if not blob or not pop:
            continue
        cx, cy, w, h = _gpkg_shape(blob)
        step = 0.33 * max(w, h)
        offsets = SPLIT if step else [(0.0, 0.0)]
        share = float(pop) / len(offsets)
        parts = []
        for dx, dy in offsets:
            lat, lon = latlon(cx + dx * step, cy + dy * step)
            if bbox[0] <= lat <= bbox[1] and bbox[2] <= lon <= bbox[3]:
                parts.append((lat, lon, share))
        if parts:
            out.append(([latlon(x, y) for x, y in _ring(blob)], parts))
    con.close()
    return out


# ---------------------------------------------------------------- defects in the map data

REPAIR_KINDS = [
    ("repeated_stops", "stop list was repeated twice"),
    ("wrong_direction", "filed under the wrong direction"),
    ("backwards", "stored backwards"),
    ("swapped", "latitude and longitude swapped"),
    ("lat_equals_lon", "latitude equal to longitude"),
    ("scrambled", "cannot explain its stops"),
    ("far", "nowhere near"),
]


def parse_repairs(lines):
    """[{route, direction, kind, text, jump_km}] from output/repairs.txt."""
    out = []
    for text in lines:
        m = re.match(r"^(\S+?)(?: d(\d))?: (.*)$", text)
        if not m:
            continue
        kind = next((k for k, phrase in REPAIR_KINDS if phrase in m.group(3)), "other")
        jump = re.search(r"straight jump of ([\d.]+) km", m.group(3))
        out.append({"route": m.group(1), "direction": int(m.group(2)) if m.group(2) else None,
                    "kind": kind, "text": m.group(3), "jump_km": float(jump.group(1)) if jump else None})
    return out


def map_issues(net, db_path, ridership_path, routes_csv):
    """Defects of AYNA's map data that the repairs do not cover, counted from the snapshot."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    buses = con.execute("SELECT bus_id, number, route_length_km, duration_min FROM buses").fetchall()
    shaped = {r for (r,) in con.execute(
        "SELECT bus_id FROM route_points GROUP BY bus_id, direction HAVING COUNT(*) >= 2")}
    con.close()

    with_stops = {p.route_id for p in net.patterns.values()}
    numbers = {r.number for r in net.routes.values()}
    one_way = {r["route"]: float(r["one_way_km"]) for r in routes_csv}
    ratios = [length / one_way[n] for _, n, length, _ in buses if n in one_way and length]
    formula = sum(1 for _, _, length, minutes in buses
                  if length is not None and minutes == math.floor(length / 0.6))

    daily = load_daily_boardings(ridership_path)
    year, month = latest_month(daily)
    counted = weekday_mean(daily, year, month)

    served = net.served_stop_ids()
    cyrillic = sum(1 for s in net.stops.values() if s.name and re.search("[Ѐ-ӿ]", s.name))
    unnamed_unused = sum(1 for s in net.stops.values() if not (s.name or "").strip() and s.id not in served)
    by_name = defaultdict(list)
    for s in net.stops.values():
        if (s.name or "").strip():
            by_name[s.name.strip()].append(s)
    shared = [v for v in by_name.values() if len(v) > 1]
    far_apart = sum(1 for v in shared if max(haversine_m(a.lat, a.lon, b.lat, b.lon) for a in v for b in v) > 1000)

    by_key = sorted(net.routes.values(), key=lambda r: _route_key(r.number))
    return {
        "routes_in_table": len(buses),
        "no_stops": [r.number for r in by_key if r.id not in with_stops],
        "no_shape": [r.number for r in by_key if r.id in with_stops and r.id not in shaped],
        "straight_directions": [[net.number(p.route_id), p.direction] for _, p in sorted(net.patterns.items())
                                if p.path_source == "stops"],
        "length_round_trip_median": statistics.median(ratios),
        "duration_formula": formula,
        "missing_from_map": sorted((n for n in counted if n not in numbers), key=_route_key),
        "counts_month": f"{year}-{month:02d}",
        "stops_in_table": len(net.stops),
        "cyrillic_names": cyrillic,
        "unnamed_unused_stops": unnamed_unused,
        "shared_names": len(shared),
        "shared_names_far_apart": far_apart,
    }


# ---------------------------------------------------------------- the page's data

def shorter_path(net, streets, a, p, i, j):
    """The path the redesign search would straighten a detour to, or None: the shortest way
    along links buses drive today, if it saves at least SHORTER_BY_M (optimize.candidates)."""
    along = p.chainage_m[j] - p.chainage_m[i]
    path = streets.path(p.stop_ids[i], p.stop_ids[j], along - SHORTER_BY_M)
    if not path:
        return None
    new = sum(h for _, h, _ in path)
    speed = a.cruise_mps(net.routes[p.route_id].zone)
    saved_s = (along - new) / speed + max(0, (j - i - 1) - (len(path) - 2)) * a.stop_loss_s
    kept = {s for s, _, _ in path}
    return {"line": line(streets.geometry(path)), "km": new / 1000, "saved_km": (along - new) / 1000,
            "saved_min": saved_s / 60, "dropped": sum(1 for s in p.stop_ids[i + 1:j] if s not in kept)}


def tightest_gap(net, stop_id):
    """The shortest distance along any route from this stop to the stop before or after it."""
    best = math.inf
    for p in net.patterns.values():
        for i, s in enumerate(p.stop_ids):
            if s == stop_id and 0 < i < len(p.stop_ids) - 1:
                best = min(best, p.chainage_m[i] - p.chainage_m[i - 1], p.chainage_m[i + 1] - p.chainage_m[i])
    return best


def carrier_key(name):
    """Carrier names that differ only in case, spaces, hyphens or the dot of İ are one carrier
    (SAHİL MMC and Sahil MMC): 42 names in the data, 39 carriers, as the paper counts them."""
    return re.sub(r"[\s\-]+", "", name.replace("İ", "I").replace("ı", "i").upper())


def carriers_table(routes, duplicates, close_stops):
    """One row per carrier: the routes it runs and what they measure, from the route rows."""
    by_number = {r["n"]: r for r in routes}
    groups = defaultdict(list)
    for r in routes:
        groups[carrier_key(r["carrier"])].append(r)
    close = set(close_stops)
    out = []
    for rs in groups.values():
        names = Counter(r["carrier"] for r in rs)
        name = sorted(names, key=lambda n: (-names[n], n))[0]
        key = carrier_key(name)
        inside = [d for d in duplicates if carrier_key(by_number[d["r"]]["carrier"]) == key]
        counted = [r["boardings"] for r in rs if r["boardings"] is not None]
        circuity = [r["circuity"] for r in rs if r["circuity"] is not None]
        stops_served = {s for r in rs for d in r["dirs"] for s in d["stops"]}
        out.append({
            "name": name, "variants": sorted(names) if len(names) > 1 else [],
            "routes": sorted((r["n"] for r in rs), key=_route_key),
            "km": sum(r["km"] for r in rs),
            "direct": sum(1 for r in rs if r["shape"] == "direct"),
            "circuity": statistics.median(circuity) if circuity else None,
            "detours": sum(r["detours"] for r in rs), "detour_km": sum(r["detour_km"] for r in rs),
            "inside": len({d["r"] for d in inside}),
            "inside_other": len({d["r"] for d in inside if carrier_key(by_number[d["in"]]["carrier"]) != key}),
            "close_stops": len(stops_served & close),
            "pop_only": sum(r["pop_only"] for r in rs),
            "boardings": sum(counted) if counted else None,
        })
    out.sort(key=lambda c: (-len(c["routes"]), c["name"]))
    return out


def build(out_dir):
    a, data = load_config(ROOT / "busnet.toml")
    net = load_network(data["db"])
    out = ROOT / "output"
    summary = json.loads((out / "network.json").read_text(encoding="utf-8"))["network"]
    scenario = json.loads((out / "scenario.json").read_text(encoding="utf-8"))
    routes_csv = read_csv(out / "routes.csv")
    detours_csv = read_csv(out / "detours.csv")
    duplicates_csv = read_csv(out / "duplicates.csv")
    corridors_csv = read_csv(out / "corridors.csv")
    removed_csv = read_csv(out / "scenario_removed_stops.csv")
    repairs = parse_repairs((out / "repairs.txt").read_text(encoding="utf-8").splitlines())
    if [r for r in net.repairs] != (out / "repairs.txt").read_text(encoding="utf-8").splitlines():
        sys.exit("output/repairs.txt does not match the repairs of data/ayna.db; run measure.py first")

    # Stops: every served stop once, referred to by its position in this list.
    served = sorted(net.served_stop_ids())
    stop_ix = {s: i for i, s in enumerate(served)}
    # Six decimals (about 10 cm): the walks between stops the travel model allows end at 300 m exactly.
    stops = [[round(net.stops[s].lat, 6), round(net.stops[s].lon, 6), net.stops[s].name or "", s] for s in served]

    # Routes, in route-number order, with both directions.
    row_of = {r["route"]: r for r in routes_csv}
    paths = Paths()
    routes = []
    for route in sorted(net.routes.values(), key=lambda r: _route_key(r.number)):
        pats = net.patterns_of(route.id)
        if not pats:
            continue
        row = row_of[route.number]
        routes.append({
            "n": route.number,
            "from": route.first_point or "", "to": route.last_point or "",
            "carrier": route.carrier, "zone": ZONE_EN.get(route.zone, route.zone),
            "region": REGION_EN.get(route.region, route.region),
            "fare": route.fare_azn,
            "shape": row["shape"], "km": num(row["one_way_km"]),
            "circuity": num(row["end_to_end_circuity"]),
            "gap": num(row["median_stop_gap_m"]), "gaps200": num(row["gaps_under_200m"]),
            "gaps300": num(row["gaps_under_300m"]),
            "detours": num(row["detours"]), "detour_km": num(row["detour_excess_km"]),
            "shared": num(row["shared_share"]),
            "pop": num(row["population_within_radius"]), "pop_only": num(row["population_only_this_route"]),
            "boardings": num(row["weekday_boardings"]),
            "headway": num(row["headway_min"]), "headway_source": row["headway_source"],
            "speed": round(a.cruise_mps(route.zone), 9),
            "straight": [p.direction for p in pats if p.path_source == "stops"],
            "dirs": [{"d": p.direction, "line": line(p.path), "stops": [stop_ix[s] for s in p.stop_ids],
                      "hops": [round(h, 3) for _, _, h in p.hops()]}
                     for p in pats],
        })
    check("routes with stops", len(routes), summary["routes_with_stops"])
    check("route directions", sum(len(r["dirs"]) for r in routes), summary["route_directions"])

    # Detours: found again on the same patterns, in the order detour_table writes them, each
    # with the shorter path along today's bus links where one saves at least 500 m.
    found = []
    for _, p in sorted(net.patterns.items()):
        pts = [(net.stops[s].lat, net.stops[s].lon) for s in p.stop_ids]
        found += [(p, d) for d in find_detours(p, pts)]
    if len(found) != len(detours_csv):
        sys.exit(f"detours: found {len(found)} but output/detours.csv has {len(detours_csv)}; run measure.py first")
    streets = Streets(net)
    detours = []
    for (p, d), row in zip(found, detours_csv):
        i, j = d["from_index"], d["to_index"]
        if (net.number(p.route_id), str(p.direction), net.stops[p.stop_ids[i]].name, net.stops[p.stop_ids[j]].name) != \
                (row["route"], row["direction"], row["from_stop"], row["to_stop"]):
            sys.exit(f"detour of route {row['route']} does not match output/detours.csv; run measure.py first")
        check(f"detour excess on route {row['route']}", d["excess_m"] / 1000, float(row["excess_km"]), 1e-3)
        detours.append({
            "r": row["route"], "d": p.direction, "a": stop_ix[p.stop_ids[i]], "b": stop_ix[p.stop_ids[j]],
            "inside": num(row["stops_inside"]), "inside_only": num(row["inside_stops_only_this_route"]),
            "along": num(row["along_km"]), "straight": num(row["straight_km"]), "excess": num(row["excess_km"]),
            "minutes": num(row["extra_min_per_trip"]), "pop_only": num(row["population_only_this_route"]),
            "line": line(paths.between(p, i, j)),
            "alt": shorter_path(net, streets, a, p, i, j),
        })

    duplicates = [{
        "r": row["route"], "in": row["inside_route"], "share": num(row["share_of_stops"]),
        "stops": num(row["route_stops"]), "other_stops": num(row["other_route_stops"]),
        "same": row["same_carrier"] == "True",
    } for row in duplicates_csv]

    # Corridors: the drawn path of the first route direction that drives each link.
    first_hop = {}
    for _, p in sorted(net.patterns.items()):
        for i, hop in enumerate(zip(p.stop_ids, p.stop_ids[1:])):
            first_hop.setdefault(hop, (p, i))
    corridors = []
    for row in corridors_csv:
        ids = [int(s) for s in row["stop_ids"].split()]
        pts = []
        for hop in zip(ids, ids[1:]):
            p, i = first_hop[hop]
            seg = paths.between(p, i, i + 1)
            pts += seg[1:] if pts else seg
        corridors.append({
            "from": row["from_stop"], "to": row["to_stop"], "via": row["via_stop"],
            "km": num(row["km"]), "stops": num(row["stops"]),
            "mean": num(row["mean_routes_per_link"]), "max": num(row["max_routes_on_a_link"]),
            "routes": row["routes"].split(), "line": line(pts),
        })

    # Closely spaced stops: the ones stop balancing removes (measure.py --scenario stop-balancing).
    details = scenario["details"]
    if len(removed_csv) != details["removed_stops"]:
        sys.exit("output/scenario_removed_stops.csv does not match output/scenario.json; run measure.py first")
    close = [[stop_ix[int(r["stop_id"])], round(tightest_gap(net, int(r["stop_id"])))] for r in removed_csv]
    before, after = scenario["before"], scenario["after"]
    spacing = {
        "stops": close, "visits": details["removed_stop_visits"],
        "min_gap_m": details["min_gap_m"], "max_gap_after_m": details["max_gap_after_m"],
        "hours_saved": before["hours_one_trip_each_direction_every_route"] - after["hours_one_trip_each_direction_every_route"],
        "residents_losing": before["population_within_coverage_radius"] - after["population_within_coverage_radius"],
    }

    # People farther than the coverage radius from a served stop, per population hexagon.
    index = StopIndex([net.stops[s] for s in served])
    radius = a.coverage_radius_m
    hexes, total, covered = [], 0.0, 0.0
    for ring, parts in hexagons(data["population"], stops_bbox(net)):
        people = sum(p for _, _, p in parts)
        reached = sum(p for lat, lon, p in parts if index.within(lat, lon, radius))
        total += people
        covered += reached
        if people - reached > 0.5:
            hexes.append([encode(ring), round(people - reached), round(people)])
    check("population in the study area", total, summary["population_in_study_area"], 1e-9)
    check("population within the coverage radius", covered, summary["population_within_coverage_radius"], 1e-9)

    issues = map_issues(net, data["db"], data["ridership"], routes_csv)
    shapes = Counter(r["shape"] for r in routes)
    carriers = carriers_table(routes, duplicates, [s for s, _ in close])
    coverage_sensitivity = [
        {"radius_m": int(r["radius_m"]), "population_within": float(r["population_within"]),
         "share": float(r["share_population_covered"])}
        for r in read_csv(out / "robustness" / "coverage_radius.csv")
    ]
    for row in coverage_sensitivity:
        check("coverage sensitivity share", row["population_within"] / total, row["share"], 5e-5)
        if row["radius_m"] == radius:
            check("coverage sensitivity baseline", row["population_within"], covered, 1e-9)
    # The same coverage with the walk measured along streets and paths, when robustness.py
    # had the walking network: shown beside the straight line in the coverage lab.
    walk_check = None
    walk_csv = out / "robustness" / "coverage_walk.csv"
    if walk_csv.exists():
        by_radius = {int(r["radius_m"]): r for r in read_csv(walk_csv)}
        for row in coverage_sensitivity:
            w = by_radius.get(row["radius_m"])
            if w:
                check("walking check, straight-line population", float(w["population_within_line"]), row["population_within"], 1e-6)
                row["population_within_walk"] = float(w["population_within_walk"])
                row["share_walk"] = float(w["share_walk"])
        rb = json.loads((out / "robustness" / "summary.json").read_text(encoding="utf-8")).get("coverage_walk") or {}
        if rb:
            walk_check = {"osm_date": rb["network"]["osm_date"][:10], "ways_walkable": rb["network"]["ways_walkable"],
                          "median_ratio": rb["walk_over_line"]["median"],
                          "share_over_detour": rb["walk_over_line"]["share_over_detour_setting"]}
    site = {
        "meta": {
            "scraped": SCRAPED, "same_as": SAME_AS, "counts_month": issues["counts_month"],
            "radius_m": radius, "transfer_walk_m": a.max_transfer_walk_m, "stop_loss_s": a.stop_loss_s,
            "walk_speed_mps": a.walk_speed_mps, "walk_detour": a.walk_detour,
            "transfer_penalty_s": a.transfer_penalty_s, "max_trip_min": a.max_trip_min,
            "headway_sources": json.loads((out / "network.json").read_text(encoding="utf-8"))["headway_sources"],
            "repository": REPOSITORY, "page": PAGE, "walk_check": walk_check,
        },
        "summary": {
            "routes": len(routes), "directions": summary["route_directions"], "stops": summary["served_stops"],
            "shapes": {k: shapes[k] for k in SHAPE_CLASSES},
            "detours": len(detours), "detour_km": sum(d["excess"] for d in detours),
            "detours_nobody_only": sum(1 for d in detours if d["pop_only"] == 0),
            "detours_with_shorter_path": sum(1 for d in detours if d["alt"]),
            "duplicate_pairs": len(duplicates),
            "duplicate_pairs_two_carriers": sum(1 for d in duplicates if not d["same"]),
            "duplicate_routes": len({d["r"] for d in duplicates}),
            "corridors": len(corridors),
            "routes_per_link": summary["duplication_ratio"],
            "most_routes_on_a_link": summary["most_routes_on_one_link"],
            "route_km": summary["route_km_one_way_total"], "street_km": summary["corridor_km"],
            "median_stop_gap_m": summary["median_stop_gap_m"],
            "share_gaps_under_200m": summary["share_stop_gaps_under_200m"],
            "close_stops": len(close),
            "carriers": len(carriers),
            "carrier_names": len({r["carrier"] for r in routes}),
            "population": summary["population_in_study_area"],
            "covered": summary["population_within_coverage_radius"],
            "routes_with_counts": sum(1 for r in routes if r["boardings"] is not None),
        },
        "issues": {**issues, "repairs": repairs},
        "stops": stops,
        "routes": routes,
        "detours": detours,
        "duplicates": duplicates,
        "corridors": corridors,
        "spacing": spacing,
        "carriers": carriers,
        "coverage_sensitivity": coverage_sensitivity,
        "hexes": hexes,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps(site, ensure_ascii=False, separators=(",", ":"))
    (out_dir / "data.js").write_text(
        "// Generated by site/build.py from output/ and data/; do not edit.\n"
        f"window.SITE_DATA = {text};\n", encoding="utf-8")
    write_xlsx(out_dir / "checklist.xlsx", workbook(site))
    return site


def write_og(site_dir):
    """site/og.png, the link-preview picture, from site/og.html (which reads data.js)."""
    if not Path(CHROME).exists():
        print("  (Google Chrome not found; og.png not written)")
        return
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--window-size=1200,630", "--virtual-time-budget=5000", f"--screenshot={site_dir / 'og.png'}",
                    (site_dir / "og.html").resolve().as_uri()], check=True, capture_output=True)


# ---------------------------------------------------------------- the checklist workbook

TEXT = {
    "title": "Baku bus network: checklist",
    "lines": [
        "Source: AYNA's public map (map-api.ayna.gov.az), taken on {scraped}; the data is identical "
        "to a copy taken on {same_as}.",
        "These lists are candidates to check, not recommendations. Every line needs checking on the "
        "ground by someone who knows the city.",
        "Coverage uses the November 2023 population grid and straight-line distance, not walking "
        "access. Finding no uniquely covered population does not establish that riders are unaffected. "
        "Geometric detour excess is relative to a straight line, not an achievable saving. "
        "Shorter graph paths need checks for legal turns, one-way streets and skipped stops. "
        "Shared stops alone do not establish redundant service; close stops are scenario candidates.",
        "Data issues: defects found in AYNA's map data that could be fixed at the source.",
        "Detours: stretches where the bus travels at least 2.5 times the straight line between two of "
        "its stops, and at least 1.5 km more. Extra minutes are estimates from assumed speeds. The "
        "shorter path runs along links buses already drive and is listed when it saves at least 0.5 km.",
        "Near-duplicate routes: at least 85% of one route's stops are also served by another route "
        "(express routes are left out).",
        "Corridors: stretches of at least 1 km where every link between consecutive stops carries at "
        "least 8 routes.",
        "Close stops: stops less than {gap} m along the route from the next stop on every route that "
        "uses them, whose removal leaves no gap over {max_gap} m. Terminals and interchange hubs are kept.",
        "Carriers: the routes each carrier runs and what they measure. AYNA plans the routes, so these "
        "figures describe the routes, not how well a carrier runs them. Names that differ only in "
        "spelling are counted once.",
        "Routes: the measured figures for every route. Residents are counted within {radius} m; "
        "boardings are published for BakuBus routes only.",
        "Page: {page}",
        "Code, data and paper: {repository}",
    ],
    "sheets": ["About", "Data issues", "Detours", "Near-duplicate routes", "Corridors", "Close stops", "Carriers",
               "Routes"],
    "carrier_cols": ["Carrier", "Also spelled", "Routes", "Route numbers", "One-way km", "Direct routes",
                     "Median path / straight line", "Detours", "Detour extra km",
                     "Routes mostly inside another route", "… inside another carrier's route", "Close stops served",
                     "Residents only one of its routes reaches", "Weekday boardings (BakuBus, {month})"],
    "issue_cols": ["Route", "Direction", "Issue", "What would fix it"],
    "detour_cols": ["Route", "Direction", "From stop", "To stop", "Stops inside",
                    "Stops inside served only by this route", "Along the route, km", "Straight line, km",
                    "Extra distance, km", "Extra minutes per trip (estimate)",
                    "Population uniquely covered (estimate)", "No uniquely covered population (grid model)",
                    "Graph candidate, km", "Graph distance difference, km", "Modelled time difference, minutes",
                    "Stops it would no longer serve"],
    "dup_cols": ["Route", "Carrier", "Its stops are mostly on route", "Carrier", "Share of stops shared",
                 "Stops of the route", "Stops of the other route", "Same carrier"],
    "corridor_cols": ["From", "To", "Turns at", "Length, km", "Stops", "Routes per link, mean",
                      "Routes on the busiest link", "Routes"],
    "close_cols": ["Stop", "AYNA stop id", "Nearest stop along a route, m", "Routes"],
    "route_cols": ["Route", "From", "To", "Carrier", "Zone", "Region", "Fare, AZN", "One-way km", "Shape",
                   "Path / straight line between ends", "Median stop spacing, m", "Stop gaps under 200 m",
                   "Detours", "Detour extra distance, km", "Share of path shared with other routes",
                   "Residents within {radius} m", "Residents only this route reaches",
                   "Weekday boardings (BakuBus, {month})"],
    "yes": "Yes", "no": "No", "both": "both", "jump": "a straight jump of {km} km",
    "kinds": {
        "repeated_stops": ("The stop list is repeated twice in a row", "Keep one copy"),
        "wrong_direction": ("A route line is filed under the wrong direction",
                            "File the line under the right direction"),
        "backwards": ("The line is stored backwards", "Reverse the order of its points"),
        "swapped": ("The line has latitude and longitude swapped", "Swap the coordinates back"),
        "lat_equals_lon": ("Latitude equals longitude at every point of the line", "Redraw the line"),
        "scrambled": ("The line does not follow the order of the stops", "Redraw the line"),
        "far": ("The line lies far from the route's stops", "Redraw the line"),
        "other": ("Other defect", "Check it"),
        "no_shape": ("The route has no line", "Add the line"),
        "no_stops": ("The route is listed but has no stops and no line",
                     "Add its stops and line, or remove the route"),
        "missing_from_map": ("In BakuBus's boarding counts but not on the map ({month})",
                             "Add the route to the map"),
    },
}


def workbook(site):
    """[(sheet name, column widths, rows, style per column, is a table)]."""
    t = TEXT
    meta, issues, spacing = site["meta"], site["issues"], site["spacing"]
    fill = {"scraped": meta["scraped"], "same_as": meta["same_as"], "radius": meta["radius_m"],
            "page": meta["page"], "repository": meta["repository"], "month": meta["counts_month"],
            "gap": round(spacing["min_gap_m"]), "max_gap": round(spacing["max_gap_after_m"])}
    carrier = {r["n"]: r["carrier"] for r in site["routes"]}
    stops = site["stops"]
    yes_no = {True: t["yes"], False: t["no"]}
    at_stop = defaultdict(set)
    for r in site["routes"]:
        for d in r["dirs"]:
            for s in d["stops"]:
                at_stop[s].add(r["n"])

    about = [[t["title"]], []] + [[s.format(**fill)] for s in t["lines"]]

    issue_rows = []
    for r in issues["repairs"]:
        what, fix = t["kinds"][r["kind"]]
        if r["kind"] == "other":
            what = r["text"]
        elif r["jump_km"]:
            jump = f"{r['jump_km']:.1f}"
            what += f" ({t['jump'].format(km=jump)})"
        issue_rows.append([r["route"], r["direction"] or t["both"], what, fix])
    for kind in ("no_shape", "no_stops", "missing_from_map"):
        what, fix = t["kinds"][kind]
        for n in issues[kind]:
            issue_rows.append([n, t["both"] if kind != "missing_from_map" else "", what.format(**fill), fix])

    detour_rows = []
    for d in sorted(site["detours"], key=lambda d: -d["minutes"]):
        alt = d["alt"] or {}
        detour_rows.append([d["r"], d["d"], stops[d["a"]][2], stops[d["b"]][2], d["inside"], d["inside_only"],
                            d["along"], d["straight"], d["excess"], d["minutes"], d["pop_only"],
                            yes_no[d["pop_only"] == 0], alt.get("km"), alt.get("saved_km"), alt.get("saved_min"),
                            alt.get("dropped")])
    dup_rows = [[d["r"], carrier[d["r"]], d["in"], carrier[d["in"]], d["share"], d["stops"], d["other_stops"],
                 yes_no[d["same"]]] for d in site["duplicates"]]
    corridor_rows = [[c["from"], c["to"], c["via"], c["km"], c["stops"], c["mean"], c["max"], " ".join(c["routes"])]
                     for c in site["corridors"]]
    close_rows = [[stops[s][2], stops[s][3], gap, " ".join(sorted(at_stop[s], key=_route_key))]
                  for s, gap in sorted(spacing["stops"], key=lambda x: (x[1], stops[x[0]][2]))]
    carrier_rows = [[c["name"], ", ".join(v for v in c["variants"] if v != c["name"]), len(c["routes"]),
                     " ".join(c["routes"]), c["km"], c["direct"], c["circuity"], c["detours"], c["detour_km"],
                     c["inside"], c["inside_other"], c["close_stops"], c["pop_only"], c["boardings"]]
                    for c in site["carriers"]]
    route_rows = [[r["n"], r["from"], r["to"], r["carrier"], r["zone"], r["region"], r["fare"], r["km"], r["shape"],
                   r["circuity"], r["gap"], r["gaps200"], r["detours"], r["detour_km"], r["shared"], r["pop"],
                   r["pop_only"], r["boardings"]] for r in site["routes"]]

    def cols(names):
        return [c.format(**fill) for c in names]

    names = t["sheets"]
    return [
        (names[0], [110], about, ["title"] + ["wrap"] * 20, False),
        (names[1], [10, 10, 60, 45], [cols(t["issue_cols"])] + issue_rows, ["text", "text", "wrap", "wrap"], True),
        (names[2], [9, 10, 34, 34, 10, 12, 10, 10, 10, 12, 14, 14, 10, 10, 12, 12],
         [cols(t["detour_cols"])] + detour_rows,
         ["text", "int", "wrap", "wrap", "int", "int", "1", "1", "1", "1", "int", "text", "1", "1", "1", "int"], True),
        (names[3], [9, 30, 12, 30, 12, 12, 12, 10], [cols(t["dup_cols"])] + dup_rows,
         ["text", "wrap", "text", "wrap", "pct", "int", "int", "text"], True),
        (names[4], [34, 34, 26, 10, 10, 12, 12, 60], [cols(t["corridor_cols"])] + corridor_rows,
         ["wrap", "wrap", "wrap", "1", "int", "1", "int", "wrap"], True),
        (names[5], [40, 12, 16, 40], [cols(t["close_cols"])] + close_rows, ["wrap", "int", "int", "wrap"], True),
        (names[6], [30, 24, 8, 40, 10, 9, 12, 9, 10, 12, 12, 10, 14, 14], [cols(t["carrier_cols"])] + carrier_rows,
         ["wrap", "wrap", "int", "wrap", "1", "int", "2", "int", "1", "int", "int", "int", "int", "int"], True),
        (names[7], [9, 26, 26, 26, 18, 10, 9, 10, 12, 12, 12, 10, 9, 10, 12, 12, 12, 14],
         [cols(t["route_cols"])] + route_rows,
         ["text", "wrap", "wrap", "wrap", "text", "text", "2", "1", "text", "2", "int", "int", "int", "1", "pct",
          "int", "int", "int"], True),
    ]


STYLE_IDS = {"text": 0, "header": 1, "int": 2, "1": 3, "2": 4, "pct": 5, "wrap": 6, "title": 7}
STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<numFmts count="2"><numFmt numFmtId="164" formatCode="#,##0"/><numFmt numFmtId="165" formatCode="0.0"/></numFmts>'
    '<fonts count="3"><font><sz val="11"/><name val="Calibri"/><family val="2"/></font>'
    '<font><b/><sz val="11"/><name val="Calibri"/><family val="2"/></font>'
    '<font><b/><sz val="14"/><name val="Calibri"/><family val="2"/></font></fonts>'
    '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
    '<fill><patternFill patternType="solid"><fgColor rgb="FFE8F0FB"/><bgColor indexed="64"/></patternFill></fill></fills>'
    '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="8">'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top"/></xf>'
    '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1">'
    '<alignment vertical="top" wrapText="1"/></xf>'
    '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment vertical="top"/></xf>'
    '<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment vertical="top"/></xf>'
    '<xf numFmtId="2" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment vertical="top"/></xf>'
    '<xf numFmtId="9" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment vertical="top"/></xf>'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
    '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
    '</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'
)
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTROL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _col(i):
    s, i = "", i + 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell(ref, value, style):
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        value = str(value)
    if isinstance(value, (int, float)):
        return f'<c r="{ref}" s="{style}"><v>{value!r}</v></c>' if isinstance(value, float) else \
            f'<c r="{ref}" s="{style}"><v>{value}</v></c>'
    text = escape(CONTROL.sub("", str(value)))
    space = ' xml:space="preserve"' if text != text.strip() else ""
    return f'<c r="{ref}" t="inlineStr" s="{style}"><is><t{space}>{text}</t></is></c>'


def _sheet(widths, rows, styles, table):
    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n',
           f'<worksheet xmlns="{MAIN}" xmlns:r="{REL}">']
    if table:
        out.append('<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" '
                   'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>')
    else:
        out.append('<sheetViews><sheetView workbookViewId="0"/></sheetViews>')
    out.append('<sheetFormatPr defaultRowHeight="15"/><cols>')
    out += [f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths)]
    out.append("</cols><sheetData>")
    for n, row in enumerate(rows, 1):
        cells = []
        for i, v in enumerate(row):
            if not table:
                kind = styles[min(n - 1, len(styles) - 1)]          # a text sheet is styled by row
            else:
                kind = "header" if n == 1 else styles[i]
            cells.append(_cell(f"{_col(i)}{n}", v, STYLE_IDS[kind]))
        out.append(f'<row r="{n}">{"".join(cells)}</row>')
    out.append("</sheetData>")
    if table and len(rows) > 1:
        out.append(f'<autoFilter ref="A1:{_col(len(rows[0]) - 1)}{len(rows)}"/>')
    out.append("</worksheet>")
    return "".join(out)


def write_xlsx(path, sheets):
    """A minimal Office Open XML workbook: inline strings, a few number formats, frozen headers
    and filters. Entries carry a fixed date, so the same input gives the same bytes."""
    names = [s[0] for s in sheets]
    filters = "".join(
        f'<definedName name="_xlnm._FilterDatabase" localSheetId="{i}" hidden="1">'
        f"'{escape(name)}'!$A$1:${_col(len(rows[0]) - 1)}${len(rows)}</definedName>"
        for i, (name, _, rows, _, table) in enumerate(sheets) if table and len(rows) > 1)
    files = {
        "[Content_Types].xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            + "".join(f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" '
                      'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                      for i in range(len(sheets)))
            + '<Override PartName="/xl/styles.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '<Override PartName="/docProps/core.xml" '
            'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            '</Types>',
        "_rels/.rels":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<Relationships xmlns="{PKG}">'
            f'<Relationship Id="rId1" Type="{REL}/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/'
            'metadata/core-properties" Target="docProps/core.xml"/></Relationships>',
        "docProps/core.xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/">'
            f"<dc:title>{escape(sheets[0][2][0][0])}</dc:title></cp:coreProperties>",
        "xl/workbook.xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<workbook xmlns="{MAIN}" xmlns:r="{REL}"><bookViews><workbookView/></bookViews><sheets>'
            + "".join(f'<sheet name="{escape(n)}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, n in enumerate(names))
            + "</sheets>" + (f"<definedNames>{filters}</definedNames>" if filters else "") + "</workbook>",
        "xl/_rels/workbook.xml.rels":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<Relationships xmlns="{PKG}">'
            + "".join(f'<Relationship Id="rId{i + 1}" Type="{REL}/worksheet" Target="worksheets/sheet{i + 1}.xml"/>'
                      for i in range(len(sheets)))
            + f'<Relationship Id="rId{len(sheets) + 1}" Type="{REL}/styles" Target="styles.xml"/></Relationships>',
        "xl/styles.xml": STYLES,
    }
    for i, (_, widths, rows, styles, table) in enumerate(sheets):
        files[f"xl/worksheets/sheet{i + 1}.xml"] = _sheet(widths, rows, styles, table)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, content.encode("utf-8"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "site"))
    ap.add_argument("--og", action="store_true", help="also draw og.png, the link-preview picture (needs Chrome)")
    args = ap.parse_args()
    site = build(Path(args.out))
    s, i = site["summary"], site["issues"]
    print(f"{s['routes']} routes, {len(site['stops']):,} stops, {s['detours']} detours "
          f"({s['detours_with_shorter_path']} with a shorter path), {s['duplicate_pairs']} near-duplicate pairs, "
          f"{s['corridors']} corridors, {s['close_stops']} close stops, "
          f"{len(site['hexes']):,} hexagons with people farther than {site['meta']['radius_m']} m from a stop")
    print(f"Map data: {len(i['repairs'])} repairs, {len(i['no_stops'])} routes without stops, "
          f"{len(i['missing_from_map'])} counted routes missing from the map")
    if args.og:
        write_og(Path(args.out))
    print(f"Wrote {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
