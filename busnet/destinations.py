"""Places people travel to: OpenStreetMap destinations and Baku Metro stations.

They give each population zone a pull on trip ends beyond the people living there:

    attraction = (1 - destination_share) x population + destination_share x total population x destination share

OpenStreetMap features (saved from the Overpass API) are weighted by category with
destination_weights. A metro station weighs metro_weight_per_1000_entries for every
1,000 average weekday entries, split evenly across its exits."""

import csv
import datetime
import difflib
import json
import math
import re
import statistics
from collections import defaultdict

from .geo import PROJ


def _category(tags):
    for key in ("amenity", "shop"):
        if key in tags:
            return tags[key]
    if tags.get("railway") == "station":
        return "station"
    if "office" in tags:
        return "office"
    return None


def osm_points(paths, weights):
    """[(lat, lon, weight, category)] from Overpass JSON files; a feature found twice counts once."""
    seen, out = set(), []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            elements = json.load(f).get("elements", [])
        for e in elements:
            key = (e.get("type"), e.get("id"))
            if key in seen:
                continue
            seen.add(key)
            cat = _category(e.get("tags", {}))
            w = weights.get(cat, 0)
            centre = e.get("center") or {}
            lat, lon = e.get("lat", centre.get("lat")), e.get("lon", centre.get("lon"))
            if w and lat is not None and lon is not None:
                out.append((lat, lon, float(w), cat))
    return out


def _norm(name):
    return re.sub(r"[^0-9a-z]", "", name.lower())


def _match(name, candidates):
    """Best candidate for a station name: exact, contained, or closely spelled."""
    n = _norm(name)
    norm = {c: _norm(c) for c in candidates}
    for c, cn in norm.items():
        if cn == n:
            return c
    for c, cn in norm.items():
        if n and cn and (n in cn or cn in n):
            return c
    best = max(candidates, key=lambda c: difflib.SequenceMatcher(None, n, norm[c]).ratio(), default=None)
    if best and difflib.SequenceMatcher(None, n, norm[best]).ratio() >= 0.75:
        return best
    return None


def metro_points(passengers_csv, exits_csv, per_1000_entries):
    """([(lat, lon, weight, "metro")], unmatched station names).

    Entries are the weekday mean of the latest month in the passengers file
    (columns date, station, daily entries); exits come with English station names."""
    daily = defaultdict(dict)
    with open(passengers_csv, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f, delimiter=";" if ";" in f.readline() else ","))
    for row in rows:
        if len(row) < 3 or not row[2].strip().isdigit():
            continue
        day = datetime.date.fromisoformat(row[0].strip()[:10])
        daily[row[1].strip()][day] = int(row[2])
    last = max(d for days in daily.values() for d in days)
    entries = {}
    for station, days in daily.items():
        vals = [n for d, n in days.items() if (d.year, d.month) == (last.year, last.month) and d.weekday() < 5]
        if vals:
            entries[station] = statistics.mean(vals)

    exits = defaultdict(list)
    with open(exits_csv, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader)
        for row in reader:
            lat, lon = float(row[2]) / 1e6, float(row[3]) / 1e6
            exits[row[1].strip()].append((lat, lon))

    out, unmatched = [], []
    for station, n in entries.items():
        m = _match(station, list(exits))
        if not m:
            unmatched.append(station)
            continue
        w = per_1000_entries * n / 1000 / len(exits[m])
        out += [(lat, lon, w, "metro") for lat, lon in exits[m]]
    return out, sorted(unmatched)


def zone_attraction(zones, points, share, max_m=1500.0):
    """Pull of each zone on trip ends, given destination points; None without points.

    Each point is credited to its nearest zone within max_m; the result is scaled so
    it sums to the total population."""
    if not points or share <= 0:
        return None
    cell = 500.0
    grid = defaultdict(list)
    xy = [PROJ.to_xy(lat, lon) for lat, lon, _ in zones]
    for i, (x, y) in enumerate(xy):
        grid[(int(x // cell), int(y // cell))].append(i)
    dest = [0.0] * len(zones)
    k = int(math.ceil(max_m / cell))
    for lat, lon, w, _ in points:
        px, py = PROJ.to_xy(lat, lon)
        cx, cy = int(px // cell), int(py // cell)
        best, bd = None, max_m * max_m
        for i in range(cx - k, cx + k + 1):
            for j in range(cy - k, cy + k + 1):
                for z in grid.get((i, j), ()):
                    d2 = (xy[z][0] - px) ** 2 + (xy[z][1] - py) ** 2
                    if d2 < bd:
                        best, bd = z, d2
        if best is not None:
            dest[best] += w
    pop_total = sum(z[2] for z in zones)
    dest_total = sum(dest)
    if not dest_total:
        return None
    return [(1 - share) * z[2] + share * pop_total * d / dest_total for z, d in zip(zones, dest)]
