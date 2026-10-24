#!/usr/bin/env python3
"""
Build the Baku Metro tables in data/metro/ from the operator's API, OpenStreetMap,
Wikidata and the operator's files on opendata.az.

AYNA's map API, the source of the bus network (data/ayna.db), has nothing on the metro.
The metro's own API (data/metro_scraper.py) gives the train services, their running
times and some departure lists; OpenStreetMap gives the track, so the distances between
stations, and the entrances; Wikidata the opening dates; Bakı Metropoliteni's files on
opendata.az the station names used in the daily entry counts and the exits. All inputs
are committed under data/external/ (data/fetch_external.py and data/metro_scraper.py
download them again):
  metro_api/                      the operator's API: stations, services, journey
                                  planner answers, departure lists
  osm/osm_metro_routes.json       route relations: stops in order and track geometry
  osm/osm_metro_stations.json     stations and entrances
  wikidata/metro_stations.json    opening dates
  opendata/metro_exits.csv        the operator's 27 stations and their 98 exits
  opendata/metro_passengers-2025.csv, metro_passengers-2026.csv
                                  how the daily entry counts spell each station
Outputs, in data/metro/:
  stations.csv       one row per open station: its name in every source, lines,
                     coordinates, opening date, exits and entrances
  route_stops.csv    the stops of each OpenStreetMap route variant in order, with the
                     distance along the track from the previous stop
  routes.geojson     the track of each route variant
  run_times.csv      each train service end to end in both directions as the journey
                     planner times it: arrival at every station, seconds and track
                     kilometres from the previous one, and how that stretch is made
  departures.csv     the departure lists the operator publishes (a few terminals only)

Standard library only. Usage (from the repository root):
  python3 data/build_metro.py
"""

import csv
import datetime
import difflib
import io
import json
import math
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent
EXT = DATA / "external"
OUT = DATA / "metro"
EARTH_RADIUS_M = 6371008.8

# The daily counts call Şah İsmayıl Xətai just "Xətai" (2025) and "Khatai" (2026), too
# short for any spelling rule to match safely.
ENTRY_NAMES = {"Şah İsmayıl Xətai": ("Xətai", "Khatai")}


def dist(a, b):
    """Great-circle distance in metres between two (lat, lon) points."""
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def key(name):
    """A spelling-tolerant key: Azerbaijani letters and English digraphs folded to ASCII."""
    s = name.casefold().replace("i̇", "i").replace(" metrostansiyası", "").removesuffix(" st.")
    for a, b in (("ə", "e"), ("ı", "i"), ("ğ", "g"), ("ş", "s"), ("ç", "c"), ("ö", "o"), ("ü", "u"),
                 ("kh", "x"), ("sh", "s"), ("ch", "c"), ("gh", "g"), ("j", "c"), ("q", "g")):
        s = s.replace(a, b)
    return "".join(c for c in s if c.isalnum())


def read_csv(path):
    raw = path.read_text(encoding="utf-8-sig")
    rows = list(csv.reader(io.StringIO(raw), delimiter=";" if raw.count(";") > raw.count(",") else ","))
    return rows[1:]


def operator_stations():
    """{name: station} for the 27 stations of the exits file, in the file's order.

    The file's Azerbaijani column turned "28 May" into the date 28.05.2026, so a
    date there falls back to the English name; "Memar Əcəmi 2" is written with the
    hyphen the operator's 2025 counts and Wikidata use."""
    out = {}
    for row in read_csv(EXT / "opendata/metro_exits.csv"):
        az, en = row[0].strip(), row[1].strip()
        name = en if re.fullmatch(r"\d\d\.\d\d\.\d{4}.*", az) else re.sub(r" 2$", "-2", az)
        st = out.setdefault(name, {"station": name, "name_en": en, "name_exits_az": az, "name_exits_en": en, "exits": []})
        st["exits"].append((int(row[2]) / 1e6, int(row[3]) / 1e6))
    return out


def match_entry_names(stations, path, column):
    """Give each station the name the daily counts in `path` use for it."""
    names = sorted({row[1].strip() for row in read_csv(path)})
    taken = {}
    for st in stations.values():
        if st["station"] in ENTRY_NAMES:
            best = ENTRY_NAMES[st["station"]][0 if column.endswith("2025") else 1]
            assert best in names, f"{best} not in {path.name}"
        else:
            score = lambda n: max(difflib.SequenceMatcher(None, key(n), key(st[k])).ratio()
                                  for k in ("station", "name_exits_en"))
            ranked = sorted(names, key=score, reverse=True)
            best = ranked[0]
            # An exact match wins outright (Memar Əcəmi against Memar Əcəmi-2); a near
            # one must clearly beat the next best.
            assert score(best) == 1 or (score(best) >= 0.85 and score(best) - score(ranked[1]) >= 0.05), \
                (st["station"], ranked[:2])
        assert best not in taken, f"{best} matches both {taken.get(best)} and {st['station']}"
        taken[best] = st["station"]
        st[column] = best
    assert len(taken) == len(names) == len(stations), f"{path.name}: {sorted(set(names) - set(taken))} unmatched"


def nearest(point, candidates, coords, max_m):
    """The candidate closest to `point`, if within max_m metres."""
    scored = sorted((dist(point, coords(c)), i) for i, c in enumerate(candidates))
    return candidates[scored[0][1]] if scored and scored[0][0] <= max_m else None


def chain(ways):
    """Join the member ways of a route into one path, turning each way to fit."""
    line = ways[0]
    for i, g in enumerate(ways[1:]):
        options = [(dist(line[-1], g[0]), line, g), (dist(line[-1], g[-1]), line, g[::-1])]
        if i == 0:  # the first way may point backwards
            options += [(dist(line[0], g[0]), line[::-1], g), (dist(line[0], g[-1]), line[::-1], g[::-1])]
        gap, head, tail = min(options, key=lambda o: o[0])
        assert gap < 50, f"gap of {gap:.0f} m in the track"
        line = head + (tail[1:] if gap < 1 else tail)
    return line


def chainage(point, line):
    """Distance along `line` to the point on it closest to `point`, in metres."""
    kx = math.radians(1) * EARTH_RADIUS_M * math.cos(math.radians(point[0]))
    ky = math.radians(1) * EARTH_RADIUS_M
    px, py = point[1] * kx, point[0] * ky
    best, run = (float("inf"), 0.0), 0.0
    for a, b in zip(line, line[1:]):
        ax, ay, bx, by = a[1] * kx, a[0] * ky, b[1] * kx, b[0] * ky
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
        off = math.hypot(px - ax - t * dx, py - ay - t * dy)
        if off < best[0]:
            best = (off, run + t * math.sqrt(seg2))
        run += math.sqrt(seg2)
    return best[1]


def build(out=OUT):
    stations = operator_stations()
    match_entry_names(stations, EXT / "opendata/metro_passengers-2025.csv", "name_entries_2025")
    match_entry_names(stations, EXT / "opendata/metro_passengers-2026.csv", "name_entries_2026")

    osm = json.loads((EXT / "osm/osm_metro_stations.json").read_text(encoding="utf-8"))["elements"]
    nodes = [e for e in osm if e.get("tags", {}).get("railway") == "station" and "construction" not in e["tags"]]
    entrances = [e for e in osm if e.get("tags", {}).get("railway") == "subway_entrance"]
    latlon = lambda e: (e["lat"], e["lon"]) if "lat" in e else (e["center"]["lat"], e["center"]["lon"])

    # Each operator station takes the OpenStreetMap station of the same name nearest its
    # exits; the two stations called Memar Əcəmi there are told apart by distance.
    by_node = {}
    for st in stations.values():
        exits = st["exits"]
        centre = (sum(p[0] for p in exits) / len(exits), sum(p[1] for p in exits) / len(exits))
        base = key(st["station"].removesuffix("-2"))
        same = [e for e in nodes if key(e["tags"]["name"]) == base]
        node = nearest(centre, same, latlon, 300)
        assert node and node["id"] not in by_node, f"no OpenStreetMap station for {st['station']}"
        by_node[node["id"]] = st
        st["lat"], st["lon"] = latlon(node)
        st["osm_node"] = node["id"]
        st["opened_osm"] = node["tags"].get("start_date", "")
    open_nodes = [e for e in nodes if e["id"] in by_node]
    for e in entrances:
        node = nearest(latlon(e), open_nodes, latlon, 400)
        if node:
            by_node[node["id"]]["entrances_osm"] = by_node[node["id"]].get("entrances_osm", 0) + 1

    # Opening dates from Wikidata: the item of the same name (or contained name, as
    # "Xətai" in "Şah İsmayıl Xətai") nearest the station.
    items = {}
    for r in json.loads((EXT / "wikidata/metro_stations.json").read_text(encoding="utf-8"))["results"]["bindings"]:
        it = items.setdefault(r["item"]["value"].rsplit("/", 1)[1], {"opened": set(), "name": r.get("az", {}).get("value", "")})
        if "opened" in r:
            it["opened"].add(r["opened"]["value"][:10])
        if "coord" in r:
            lon, lat = map(float, re.findall(r"-?\d+\.?\d*", r["coord"]["value"]))
            it["coord"] = (lat, lon)
    for st in stations.values():
        k = key(st["station"])
        exact = [q for q, it in items.items() if "coord" in it and key(it["name"]) == k]
        loose = [q for q, it in items.items() if "coord" in it and (key(it["name"]) in k or k in key(it["name"]))]
        q = nearest((st["lat"], st["lon"]), exact or loose, lambda q: items[q]["coord"], 400)
        assert q, f"no Wikidata item for {st['station']}"
        st["wikidata"], st["opened"] = q, "/".join(sorted(items[q]["opened"]))

    # Route variants: stops in order, located on the chained track.
    features, stop_rows = [], []
    lines_of = {}
    routes = json.loads((EXT / "osm/osm_metro_routes.json").read_text(encoding="utf-8"))["elements"]
    for rel in sorted((r for r in routes if r["tags"].get("type") == "route"), key=lambda r: (r["tags"]["ref"], r["id"])):
        t = rel["tags"]
        ways = [[(p["lat"], p["lon"]) for p in m["geometry"]] for m in rel["members"] if m["type"] == "way" and "geometry" in m]
        line = chain(ways)
        stops = []
        for m in rel["members"]:
            if m["type"] == "node" and m.get("role", "").startswith("stop"):
                node = nearest((m["lat"], m["lon"]), open_nodes, latlon, 300)
                assert node, f"stop {m['ref']} of {t['name']} is far from every station"
                stops.append(by_node[node["id"]]["station"])
        at = [chainage((stations[s]["lat"], stations[s]["lon"]), line) for s in stops]
        if at[0] > at[-1]:
            line = line[::-1]
            at = [chainage((stations[s]["lat"], stations[s]["lon"]), line) for s in stops]
        hops = [b - a for a, b in zip(at, at[1:])]
        assert all(h > 0 for h in hops), f"stops of {t['name']} out of order"
        length = sum(dist(a, b) for a, b in zip(line, line[1:]))
        direction = f"{stops[0]} → {stops[-1]}"
        for i, s in enumerate(stops):
            lines_of.setdefault(s, set()).add(t["ref"])
            stop_rows.append({"route": rel["id"], "line": t["ref"], "direction": direction, "seq": i + 1, "station": s,
                              "km_from_previous": f"{hops[i - 1] / 1000:.3f}" if i else "",
                              "km_from_start": f"{(at[i] - at[0]) / 1000:.3f}"})
        features.append({"type": "Feature",
                         "properties": {"route": rel["id"], "line": t["ref"], "colour": t.get("colour", ""),
                                        "direction": direction, "stops": len(stops),
                                        "km_first_to_last_stop": round((at[-1] - at[0]) / 1000, 3),
                                        "km_of_track": round(length / 1000, 3)},
                         "geometry": {"type": "LineString", "coordinates": [[round(lon, 6), round(lat, 6)] for lat, lon in line]}})
        print(f"  line {t['ref']:2} {direction}: {len(stops)} stops, {(at[-1] - at[0]) / 1000:.2f} km "
              f"between the end stops, {length / 1000:.2f} km of track")

    # The operator's API: one station id for both Memar Əcəmi stations, which the line
    # of the service tells apart; journeys timed by its planner; published departures.
    api = EXT / "metro_api"
    api_stations = json.loads((api / "stations_map.json").read_text(encoding="utf-8"))["stations"]
    for st in stations.values():
        k = key(st["station"].removesuffix("-2"))
        found = ([a for a in api_stations if key(a["name"]) == k]
                 or [a for a in api_stations if key(a["name"]) in k or k in key(a["name"])])
        assert len(found) == 1, (st["station"], [a["name"] for a in found])
        st["metro_api_id"], st["name_metro_api"] = found[0]["id"], found[0]["name"]
    # The API names lines in the language asked for; their colours are fixed. Each maps
    # to a line name and the OpenStreetMap ref that tells the two Memar Əcəmi apart.
    by_colour = {"#FF0000": ("red", "1"), "#41A317": ("green", "2"), "#870AE0": ("purple", "3")}

    def canonical(api_id, osm_ref=None):
        names = [s for s, st in stations.items() if st["metro_api_id"] == api_id]
        if len(names) > 1:
            names = [s for s in names if osm_ref in lines_of.get(s, ())]
        assert len(names) == 1, (api_id, osm_ref, names)
        return names[0]

    track_km = {}
    for r in stop_rows:
        if r["km_from_previous"]:
            track_km[(prev_station, r["station"])] = track_km[(r["station"], prev_station)] = float(r["km_from_previous"])
        prev_station = r["station"]
    run_rows = []
    for path in sorted(api.glob("line_*.json")):
        line = json.loads(path.read_text(encoding="utf-8"))
        colour, ref = by_colour[line["lineColor"].upper()]
        for seg in line["segments"]:
            ends = seg["stations"][0]["id"], seg["stations"][-1]["id"]
            service = " – ".join(canonical(i, ref) for i in ends)
            for a, b in (ends, ends[::-1]):
                journey = json.loads((api / f"journeys/{a}-{b}.json").read_text(encoding="utf-8"))
                direction = f"{canonical(a, ref)} → {canonical(b, ref)}"
                prev, seq, total, train_s, train_km = None, 0, 0, 0, 0.0
                for leg in journey["lines"]:
                    for i, s in enumerate(leg["stations"]):
                        name = canonical(s["stationId"], ref)
                        t = datetime.time.fromisoformat(s["arrivalTime"])
                        sec = t.hour * 3600 + t.minute * 60 + t.second
                        km = ""
                        if prev is None:
                            by = "start"
                        elif i == 0:
                            by = "wait" if name == prev[0] else "walk"
                        elif prev[2]:
                            by = "bus " + "/".join(sorted(prev[2]))
                        else:
                            by = "train"
                            km = track_km.get((prev[0], name), "")
                        step = (sec - prev[1]) % 86400 if prev else 0
                        if by == "train":
                            train_s += step
                            train_km += km or 0
                        total += step
                        seq += 1
                        run_rows.append({"service": service, "line": colour, "direction": direction, "seq": seq,
                                         "station": name, "arrival": s["arrivalTime"], "s_from_previous": step,
                                         "km_from_previous": f"{km:.3f}" if km != "" else "", "by": by})
                        info = s.get("stationToInfo") or {}
                        prev = (name, sec, [b["routeName"] for b in info.get("busRoutes") or []])
                print(f"  {colour:6} {direction}: {total / 60:.1f} min end to end, {train_s / 60:.1f} min on "
                      f"trains over {train_km:.2f} km ({train_km / (train_s / 3600):.0f} km/h)")
    dep_rows = []
    for sch in json.loads((api / "schedule.json").read_text(encoding="utf-8")):
        for ss in sch["stationSchedules"]:
            for day, times in ss["schedulesByDayType"].items():
                dep_rows += [{"schedule": sch["name"], "station": canonical(ss["stationId"]), "day": day,
                              "departure": t} for t in times]

    out.mkdir(exist_ok=True)
    cols = ["station", "lines", "lat", "lon", "opened", "opened_osm", "exits", "entrances_osm", "name_en",
            "name_exits_az", "name_exits_en", "name_entries_2025", "name_entries_2026", "name_metro_api",
            "metro_api_id", "osm_node", "wikidata"]
    with open(out / "stations.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for st in stations.values():
            w.writerow({**st, "lines": " ".join(sorted(lines_of.get(st["station"], []))),
                        "lat": f"{st['lat']:.6f}", "lon": f"{st['lon']:.6f}",
                        "exits": len(st["exits"]), "entrances_osm": st.get("entrances_osm", 0)})
    with open(out / "route_stops.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(stop_rows[0]))
        w.writeheader()
        w.writerows(stop_rows)
    (out / "routes.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features},
                                                   ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for name, rows in (("run_times.csv", run_rows), ("departures.csv", dep_rows)):
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    missing = [s for s in stations if s not in lines_of]
    print(f"Wrote {len(stations)} stations, {len(stop_rows)} route stops, {len(features)} route tracks, "
          f"{len(run_rows)} timed stops and {len(dep_rows)} departures to {out}/"
          + (f"; on no route: {', '.join(missing)}" if missing else ""))


if __name__ == "__main__":
    build()
