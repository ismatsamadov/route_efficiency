"""Bicycle lanes and parking points, and how they sit against the bus network.

AYNA publishes two files on opendata.az, both KMZ (zipped KML) saved from Google Earth:

  - the existing bicycle lanes: one folder, "Mövcud zolaqlar", of lines named after
    their streets (the file of 24 September 2026);
  - the bicycle parking points: a whole Google Earth session (the file of 4 May 2026)
    holding the 185 points named MPV-... in the folder "velosiped məntəqələri yeni",
    649 points named MPS-... under "My Places", the bicycle lanes of January 2025 in
    a folder of their own, and Google Earth's ten sample places (the Eiffel Tower and
    so on), which the readers below drop.

The measures put them beside the bus network: served stops and route paths within reach
of a lane, lanes with a bus route beside them, parking points near stops, lanes and
metro exits, and the people within the coverage radius of a lane, counted the way
coverage counts them."""

import math
import re
import statistics
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from .geo import PROJ, Polyline, haversine_m
from .graph import StopIndex
from .metrics import ZONE_EN, _route_key

KML = "{http://www.opengis.net/kml/2.2}"
LANES_FOLDER = "Mövcud zolaqlar"                      # existing lanes, in the lanes file
LANES_2025_FOLDER = "Velosiped yolları 2025 yanvar"   # the lanes of January 2025, kept in the parking file
PARKING_NAME = re.compile(r"^(MPV|MPS)-(\d+)(?:-(\d+))?$")
ABSHERON = (39.9, 40.7, 49.3, 50.45)                  # min lat, max lat, min lon, max lon

# Reporting thresholds, straight-line metres.
STOP_RADII_M = (50, 100, 200)   # a served stop near a lane, at three distances
NEAR_M = 100                    # the tables' "near": a stop near a lane, a parking point near a stop
LANE_M = 50                     # a parking point near a lane (the distance AYNA's hackathon task used)
ROUTE_WITHIN_M = 40             # a route path "along" a lane: within this of it, so that a lane on one side of
                                # a dual carriageway still counts for a bus on the other side
ALONG_MIN_M = 100               # the least a route must run along a street's lane to be listed on that street
ALONG_ROUTE_KM = 0.5            # a route "runs along the lanes" from this length
METRO_M = 300                   # a parking point near a metro exit
STEP_M = 20.0                   # sampling step along paths
SAME_POINT_M = 5.0              # an MPV point "on" an MPS point


@dataclass
class Lane:
    name: str            # the street, as the file names it
    line: Polyline

    @property
    def length_m(self):
        return self.line.length_m


@dataclass
class Parking:
    name: str            # MPV-12-2, MPS-305
    kind: str            # MPV or MPS, the prefix of the name
    number: int
    suffix: int | None   # the last number of an MPV name; the file does not say what it means
    lat: float
    lon: float


# ---------------------------------------------------------------- reading the files

def read_kml(path):
    """The KML document inside a .kmz, or a .kml file itself, as bytes."""
    path = Path(path)
    if path.suffix.lower() == ".kmz":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".kml")]
            if not names:
                raise ValueError(f"{path}: no .kml inside")
            return z.read(names[0])
    return path.read_bytes()


def placemarks(path):
    """Every placemark in a KMZ or KML file as (folders, name, geometry, points).

    folders: the names of the document and the folders above the placemark, outermost
    first; geometry: "Point", "LineString", "Polygon" or None; points: its coordinates
    as (lat, lon), in order."""
    out = []

    def walk(node, folders):
        for child in node:
            tag = child.tag.replace(KML, "")
            if tag in ("Document", "Folder"):
                walk(child, folders + ((child.findtext(KML + "name") or "").strip(),))
            elif tag == "Placemark":
                name = (child.findtext(KML + "name") or "").strip()
                geometry = next((g for g in ("Point", "LineString", "Polygon") if child.find(f".//{KML}{g}") is not None), None)
                points = []
                for item in (child.findtext(f".//{KML}coordinates") or "").split():
                    parts = item.split(",")
                    if len(parts) >= 2:
                        points.append((float(parts[1]), float(parts[0])))
                out.append((folders, name, geometry, points))

    walk(ElementTree.fromstring(read_kml(path)), ())
    return out


def load_lanes(path, folder=LANES_FOLDER):
    """(lanes, skipped): the lines in the named folder as Lane objects, and the names of
    its other placemarks, such as a line with fewer than two points (each file has one
    empty "8 Noyabr pr." placemark)."""
    lanes, skipped = [], []
    for folders, name, geometry, points in placemarks(path):
        if folder not in folders:
            continue
        if geometry == "LineString" and len(points) >= 2:
            lanes.append(Lane(name, Polyline(points)))
        else:
            skipped.append(name)
    return lanes, skipped


def load_parking(path, box=ABSHERON):
    """The points named MPV-n-k or MPS-n inside the box, by kind and number."""
    out = []
    for _, name, geometry, points in placemarks(path):
        m = PARKING_NAME.match(name)
        if geometry != "Point" or not m or not points:
            continue
        lat, lon = points[0]
        if box[0] <= lat <= box[1] and box[2] <= lon <= box[3]:
            out.append(Parking(name, m.group(1), int(m.group(2)), int(m.group(3)) if m.group(3) else None, lat, lon))
    out.sort(key=lambda p: (p.kind, p.number, p.suffix or 0))
    return out


# ---------------------------------------------------------------- geometry

class LineIndex:
    """Find the nearest of many lines to a point quickly: their segments on a square grid.

    Distances are in the flat projection, as in Polyline.project_all."""

    def __init__(self, lines, cell_m=200.0):
        """lines: [(key, Polyline)]; the key names what is found (a street, a route number)."""
        self.cell = cell_m
        self.lines = list(lines)
        self.grid = defaultdict(list)
        xs, ys = [], []
        for li, (_, line) in enumerate(self.lines):
            xy = line.xy
            xs += [p[0] for p in xy]
            ys += [p[1] for p in xy]
            for si in range(len(xy) - 1):
                (ax, ay), (bx, by) = xy[si], xy[si + 1]
                for i in range(int(min(ax, bx) // cell_m), int(max(ax, bx) // cell_m) + 1):
                    for j in range(int(min(ay, by) // cell_m), int(max(ay, by) // cell_m) + 1):
                        self.grid[(i, j)].append((li, si))
        self.box = (min(xs), max(xs), min(ys), max(ys)) if xs else None

    def nearest(self, lat, lon, max_m):
        """(distance_m, key, chainage_m) of the nearest line within max_m, or None."""
        if self.box is None:
            return None
        x, y = PROJ.to_xy(lat, lon)
        if x < self.box[0] - max_m or x > self.box[1] + max_m or y < self.box[2] - max_m or y > self.box[3] + max_m:
            return None
        k = int(math.ceil(max_m / self.cell))
        cx, cy = int(x // self.cell), int(y // self.cell)
        best = None
        for i in range(cx - k, cx + k + 1):
            for j in range(cy - k, cy + k + 1):
                for li, si in self.grid.get((i, j), ()):
                    line = self.lines[li][1]
                    (ax, ay), (bx, by) = line.xy[si], line.xy[si + 1]
                    dx, dy = bx - ax, by - ay
                    seg2 = dx * dx + dy * dy
                    t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / seg2))
                    d = math.hypot(x - ax - t * dx, y - ay - t * dy)
                    if d <= max_m and (best is None or d < best[0]):
                        best = (d, li, si, t)
        if best is None:
            return None
        d, li, si, t = best
        key, line = self.lines[li]
        return d, key, line.cum[si] + t * (line.cum[si + 1] - line.cum[si])

    def nearest_any(self, lat, lon, max_m=20000.0):
        """The nearest line however far, up to max_m, widening the search as StopIndex does."""
        r = self.cell
        while r <= max_m:
            hit = self.nearest(lat, lon, r)
            if hit:
                return hit
            r *= 2
        return self.nearest(lat, lon, max_m)


def along(path, index, within_m, step_m=STEP_M):
    """Metres of a path that run within within_m of the indexed lines, by key.

    The path is sampled every step_m; each sample counts the length it stands for
    towards its nearest line, so the metres add up to the path's length at most."""
    line = path if isinstance(path, Polyline) else Polyline(path)
    length = line.length_m
    out = defaultdict(float)
    for i in range(int(length // step_m) + 1):
        lo, hi = max(0.0, (i - 0.5) * step_m), min(length, (i + 0.5) * step_m)
        hit = index.nearest(*line.point_at(i * step_m), within_m)
        if hit and hi > lo:
            out[hit[1]] += hi - lo
    return dict(out)


def stops_near(network, index, radius_m):
    """{stop id: (distance_m, key)} for every served stop within radius_m of a line."""
    out = {}
    for s in sorted(network.served_stop_ids()):
        st = network.stops[s]
        hit = index.nearest(st.lat, st.lon, radius_m)
        if hit:
            out[s] = (hit[0], hit[1])
    return out


# ---------------------------------------------------------------- the measures

def measure(network, a, zones, observed, lanes, lanes_2025, parking, exits, skipped=()):
    """Everything bicycle.py writes: {"summary", "lanes", "routes", "stops", "parking", "geojson"}.

    network: the repaired Network; a: Assumptions (coverage_radius_m); zones: population
    points or None; observed: counted weekday boardings by route number or None; lanes
    and lanes_2025: [Lane]; parking: [Parking]; exits: [(station, lat, lon)];
    skipped: names of the lane placemarks that could not be read."""
    radius = a.coverage_radius_m
    lane_index = LineIndex([(lane.name, lane.line) for lane in lanes])
    served = sorted(network.served_stop_ids())
    stop_index = StopIndex([network.stops[s] for s in served])
    routes_at = network.routes_at_stop()
    number = {rid: r.number for rid, r in network.routes.items()}

    # The lanes by street.
    streets = defaultdict(lambda: {"km": 0.0, "segments": 0})
    for lane in lanes:
        streets[lane.name]["km"] += lane.length_m / 1000
        streets[lane.name]["segments"] += 1

    # Served stops near a lane.
    near_lane = stops_near(network, lane_index, max(STOP_RADII_M))        # stop id -> (m, street)
    stops_within = {str(r): sum(1 for d, _ in near_lane.values() if d <= r) for r in STOP_RADII_M}
    street_stops = defaultdict(int)
    for s, (d, street) in near_lane.items():
        if d <= NEAR_M:
            street_stops[street] += 1

    # Route paths along a lane, and the lanes with a bus route beside them.
    route_rows, street_routes = [], defaultdict(set)
    patterns = [(number[rid], Polyline(p.path)) for (rid, _), p in sorted(network.patterns.items())]
    route_index = LineIndex(patterns)
    for route in sorted(network.routes.values(), key=lambda r: _route_key(r.number)):
        pats = network.patterns_of(route.id)
        if not pats:
            continue
        per_dir = [along(p.path, lane_index, ROUTE_WITHIN_M) for p in pats]
        km_along = sum(sum(m.values()) for m in per_dir) / len(per_dir) / 1000
        one_way_km = sum(p.length_m for p in pats) / len(pats) / 1000
        most = defaultdict(float)
        for m in per_dir:
            for street, metres in m.items():
                most[street] = max(most[street], metres)
        on = sorted((s for s, m in most.items() if m >= ALONG_MIN_M), key=lambda s: (-most[s], s))
        for street in on:
            street_routes[street].add(route.number)
        if km_along <= 0:
            continue
        stop_ids = {s for p in pats for s in p.stop_ids}
        route_rows.append({
            "route": route.number, "zone": ZONE_EN.get(route.zone, route.zone), "carrier": route.carrier,
            "one_way_km": one_way_km, "km_along_lanes": km_along,
            "share_along_lanes": km_along / one_way_km if one_way_km else 0.0,
            "streets": "; ".join(on),
            "stops_within_100m_of_lane": sum(1 for s in stop_ids if s in near_lane and near_lane[s][0] <= NEAR_M),
            "weekday_boardings": (observed or {}).get(route.number),
        })
    route_rows.sort(key=lambda r: (-r["km_along_lanes"], _route_key(r["route"])))
    beside_bus = defaultdict(float)                                         # street -> lane metres with a bus route within reach
    for lane in lanes:
        beside_bus[lane.name] += sum(along(lane.line, route_index, ROUTE_WITHIN_M).values())

    # Parking points: the nearest stop, lane and metro exit of each.
    mps_index = StopIndex([p for p in parking if p.kind == "MPS"])
    mpv = [p for p in parking if p.kind == "MPV"]
    parking_rows, street_parking = [], defaultdict(lambda: {"MPV": 0, "MPS": 0})
    for p in parking:
        stop_hit = stop_index.nearest(p.lat, p.lon, max_m=50000.0)
        lane_hit = lane_index.nearest_any(p.lat, p.lon)
        exit_hit = min(((haversine_m(p.lat, p.lon, lat, lon), station) for station, lat, lon in exits), default=None)
        same = [s for d, s in mps_index.within(p.lat, p.lon, SAME_POINT_M) if s is not p] if p.kind == "MPV" else []
        if lane_hit and lane_hit[0] <= NEAR_M:
            street_parking[lane_hit[1]][p.kind] += 1
        parking_rows.append({
            "name": p.name, "kind": p.kind, "number": p.number, "suffix": p.suffix, "lat": p.lat, "lon": p.lon,
            "nearest_stop_id": stop_hit[1].id if stop_hit else None,
            "nearest_stop": stop_hit[1].name if stop_hit else None,
            "m_to_stop": stop_hit[0] if stop_hit else None,
            "routes_at_stop": len(routes_at[stop_hit[1].id]) if stop_hit else None,
            "nearest_lane": lane_hit[1] if lane_hit else None,
            "m_to_lane": lane_hit[0] if lane_hit else None,
            "nearest_metro_exit": exit_hit[1] if exit_hit else None,
            "m_to_metro_exit": exit_hit[0] if exit_hit else None,
            "mps_within_5m": " ".join(sorted(s.name for s in same)),
        })

    def parking_summary(kind):
        rows = [r for r in parking_rows if r["kind"] == kind]
        if not rows:
            return {"points": 0}
        return {
            "points": len(rows),
            "within_50m_of_lane": sum(1 for r in rows if r["m_to_lane"] is not None and r["m_to_lane"] <= LANE_M),
            "within_100m_of_lane": sum(1 for r in rows if r["m_to_lane"] is not None and r["m_to_lane"] <= NEAR_M),
            "median_m_to_lane": statistics.median(r["m_to_lane"] for r in rows if r["m_to_lane"] is not None),
            "within_100m_of_stop": sum(1 for r in rows if r["m_to_stop"] is not None and r["m_to_stop"] <= NEAR_M),
            "median_m_to_stop": statistics.median(r["m_to_stop"] for r in rows if r["m_to_stop"] is not None),
            "within_300m_of_metro_exit": sum(1 for r in rows if r["m_to_metro_exit"] is not None and r["m_to_metro_exit"] <= METRO_M),
        }

    # Stops near a lane, with the parking points near each.
    mpv_index = StopIndex(mpv)
    stop_rows = []
    for s, (d, street) in sorted(near_lane.items(), key=lambda kv: (kv[1][0], kv[0])):
        st = network.stops[s]
        numbers = sorted((number[r] for r in routes_at[s]), key=_route_key)
        stop_rows.append({
            "stop_id": s, "name": st.name, "lat": st.lat, "lon": st.lon,
            "routes": len(numbers), "route_numbers": " ".join(numbers),
            "nearest_lane": street, "m_to_lane": d,
            "parking_mpv_within_100m": len(mpv_index.within(st.lat, st.lon, NEAR_M)),
            "parking_mps_within_100m": len(mps_index.within(st.lat, st.lon, NEAR_M)),
        })

    lane_rows = []
    for street, v in sorted(streets.items(), key=lambda kv: (-kv[1]["km"], kv[0])):
        numbers = sorted(street_routes.get(street, ()), key=_route_key)
        lane_rows.append({
            "street": street, "km": v["km"], "segments": v["segments"],
            "km_beside_bus_route": beside_bus[street] / 1000,
            "bus_routes": " ".join(numbers), "bus_routes_count": len(numbers),
            "stops_within_100m": street_stops.get(street, 0),
            "parking_mpv_within_100m": street_parking[street]["MPV"],
            "parking_mps_within_100m": street_parking[street]["MPS"],
        })

    # People within the coverage radius of a lane, of a stop, of both, and of a bicycle parking point.
    people = None
    if zones:
        of_lane = of_stop = of_both = of_mpv = 0.0
        for lat, lon, n in zones:
            near_l = lane_index.nearest(lat, lon, radius) is not None
            near_s = bool(stop_index.within(lat, lon, radius))
            of_lane += n if near_l else 0
            of_stop += n if near_s else 0
            of_both += n if near_l and near_s else 0
            of_mpv += n if mpv_index.within(lat, lon, radius) else 0
        people = {"study_area": sum(z[2] for z in zones), "within_radius_of_lane": of_lane,
                  "within_radius_of_stop": of_stop, "within_radius_of_both": of_both,
                  "within_radius_of_mpv_parking": of_mpv}

    km = sum(lane.length_m for lane in lanes) / 1000
    summary = {
        "lanes": {
            "segments": len(lanes), "streets": len(streets), "km": km,
            "km_beside_bus_route": sum(beside_bus.values()) / 1000,
            "longest_streets": [{"street": r["street"], "km": r["km"]} for r in lane_rows[:10]],
            "january_2025": {"segments": len(lanes_2025), "km": sum(lane.length_m for lane in lanes_2025) / 1000},
            "skipped_placemarks": list(skipped),
            "bbox": [min(p[0] for lane in lanes for p in lane.line.latlon), max(p[0] for lane in lanes for p in lane.line.latlon),
                     min(p[1] for lane in lanes for p in lane.line.latlon), max(p[1] for lane in lanes for p in lane.line.latlon)] if lanes else None,
        },
        "parking": {
            "points": len(parking),
            "MPV": parking_summary("MPV"),
            "MPS": parking_summary("MPS"),
            "mpv_suffixes": {str(k): v for k, v in sorted(
                __import__("collections").Counter(p.suffix for p in mpv).items(), key=lambda kv: (kv[0] is None, kv[0]))},
            "mpv_on_an_mps_point": sum(1 for r in parking_rows if r["mps_within_5m"]),
        },
        "bus": {
            "served_stops": len(served),
            "stops_within_m_of_lane": stops_within,
            "routes_with_stop_within_100m_of_lane": sum(1 for r in route_rows if r["stops_within_100m_of_lane"]) +
                sum(1 for route in network.routes.values() if network.patterns_of(route.id) and
                    route.number not in {r["route"] for r in route_rows} and
                    any(s in near_lane and near_lane[s][0] <= NEAR_M for p in network.patterns_of(route.id) for s in p.stop_ids)),
            "routes_along_lanes": sum(1 for r in route_rows if r["km_along_lanes"] >= ALONG_ROUTE_KM),
            "routes_touching_lanes": len(route_rows),
            "route_km_along_lanes": sum(r["km_along_lanes"] for r in route_rows),
        },
        "people": people,
        "settings": {
            "coverage_radius_m": radius, "stop_radii_m": list(STOP_RADII_M), "near_m": NEAR_M, "lane_m": LANE_M,
            "route_within_m": ROUTE_WITHIN_M, "along_min_m": ALONG_MIN_M, "along_route_km": ALONG_ROUTE_KM,
            "metro_exit_m": METRO_M, "step_m": STEP_M, "same_point_m": SAME_POINT_M,
        },
    }
    return {"summary": summary, "lanes": lane_rows, "routes": route_rows, "stops": stop_rows,
            "parking": parking_rows, "geojson": geojson(lanes, parking_rows, street_routes)}


def geojson(lanes, parking_rows, street_routes):
    """The lanes and the parking points as a GeoJSON FeatureCollection (WGS84)."""
    features = []
    for lane in lanes:
        features.append({"type": "Feature",
                         "properties": {"kind": "lane", "street": lane.name, "km": round(lane.length_m / 1000, 3),
                                        "bus_routes": " ".join(sorted(street_routes.get(lane.name, ()), key=_route_key))},
                         "geometry": {"type": "LineString",
                                      "coordinates": [[round(lon, 6), round(lat, 6)] for lat, lon in lane.line.latlon]}})
    for r in parking_rows:
        features.append({"type": "Feature",
                         "properties": {"kind": r["kind"], "name": r["name"], "nearest_stop": r["nearest_stop"],
                                        "m_to_stop": round(r["m_to_stop"]) if r["m_to_stop"] is not None else None},
                         "geometry": {"type": "Point", "coordinates": [round(r["lon"], 6), round(r["lat"], 6)]}})
    return {"type": "FeatureCollection", "features": features}
