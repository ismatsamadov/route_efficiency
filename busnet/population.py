"""Load gridded population as (lat, lon, people) zones, using only the standard library.

Supported inputs:
  - GeoPackage (.gpkg), e.g. Kontur Population, with polygon or point features and a
    population column; each feature becomes one zone at its centre
  - CSV with latitude, longitude and population columns (header names are matched loosely)
Zones are clipped to a bounding box, normally the served stops plus a margin."""

import csv
import math
import sqlite3
import struct

WEB_MERCATOR_R = 6378137.0


def _mercator_to_latlon(x, y):
    lon = math.degrees(x / WEB_MERCATOR_R)
    lat = math.degrees(2 * math.atan(math.exp(y / WEB_MERCATOR_R)) - math.pi / 2)
    return lat, lon


def _gpkg_centre(blob):
    """Centre (x, y) of a GeoPackage geometry: its envelope centre, else its vertices' mean."""
    if blob[:2] != b"GP":
        raise ValueError("not a GeoPackage geometry")
    flags = blob[3]
    order = "<" if flags & 1 else ">"
    env_len = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(flags >> 1) & 7]
    if env_len:
        minx, maxx, miny, maxy = struct.unpack(order + "4d", blob[8:40])
        return (minx + maxx) / 2, (miny + maxy) / 2
    wkb = blob[8:]
    worder = "<" if wkb[0] == 1 else ">"
    gtype = struct.unpack(worder + "I", wkb[1:5])[0] % 1000
    if gtype == 1:                                           # point
        return struct.unpack(worder + "2d", wkb[5:21])
    if gtype == 6:                                           # multipolygon: use the first polygon
        wkb = wkb[9:]
        worder = "<" if wkb[0] == 1 else ">"
    if struct.unpack(worder + "I", wkb[1:5])[0] % 1000 != 3:
        raise ValueError("unsupported geometry type")
    npts = struct.unpack(worder + "I", wkb[9:13])[0]
    coords = struct.unpack(worder + f"{2 * npts}d", wkb[13:13 + 16 * npts])
    xs, ys = coords[0::2][:-1] or coords[0::2], coords[1::2][:-1] or coords[1::2]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def load_gpkg(path, bbox=None):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    table, geom_col, srs = con.execute(
        "SELECT c.table_name, g.column_name, g.srs_id FROM gpkg_contents c "
        "JOIN gpkg_geometry_columns g ON g.table_name = c.table_name "
        "WHERE c.data_type = 'features' LIMIT 1").fetchone()
    cols = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
    pop_col = next((c for c in cols if c.lower() in ("population", "pop", "people")), None)
    if pop_col is None:
        raise ValueError(f"no population column in {table}: {cols}")
    zones = []
    for blob, pop in con.execute(f'SELECT "{geom_col}", "{pop_col}" FROM "{table}"'):
        if not blob or not pop:
            continue
        x, y = _gpkg_centre(blob)
        lat, lon = _mercator_to_latlon(x, y) if srs == 3857 else (y, x)
        if bbox is None or (bbox[0] <= lat <= bbox[1] and bbox[2] <= lon <= bbox[3]):
            zones.append((lat, lon, float(pop)))
    con.close()
    return zones


def load_csv(path, bbox=None):
    zones = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        names = {n.lower(): n for n in reader.fieldnames}
        lat_k = next(names[n] for n in names if n in ("lat", "latitude", "y"))
        lon_k = next(names[n] for n in names if n in ("lon", "lng", "longitude", "x"))
        pop_k = next(names[n] for n in names if "pop" in n)
        for row in reader:
            lat, lon, pop = float(row[lat_k]), float(row[lon_k]), float(row[pop_k] or 0)
            if pop > 0 and (bbox is None or (bbox[0] <= lat <= bbox[1] and bbox[2] <= lon <= bbox[3])):
                zones.append((lat, lon, pop))
    return zones


def load_population(path, bbox=None):
    return load_gpkg(path, bbox) if str(path).lower().endswith(".gpkg") else load_csv(path, bbox)


def stops_bbox(network, margin_km=2.0):
    """(min_lat, max_lat, min_lon, max_lon) of served stops, widened by margin_km."""
    stops = [network.stops[s] for s in network.served_stop_ids()]
    dlat = margin_km / 111.2
    mid = sum(s.lat for s in stops) / len(stops)
    dlon = margin_km / (111.2 * math.cos(math.radians(mid)))
    return (min(s.lat for s in stops) - dlat, max(s.lat for s in stops) + dlat,
            min(s.lon for s in stops) - dlon, max(s.lon for s in stops) + dlon)
