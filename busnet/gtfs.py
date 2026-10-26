"""Write a network as a GTFS feed, the standard format other transit tools read.

Each route direction becomes one trip that repeats every headway between the start and
end of service (frequencies.txt). Times between stops follow the same model as the
metrics: distance at the zone's moving speed plus the fixed loss at each stop. A feed
written with estimated headways describes the model, not an official timetable.

Shapes are the repaired route lines with two changes the MobilityData GTFS validator asks
for: a point that repeats the one before it is written once, and a line that ends before
the last stops of its direction (or starts after the first) is carried on to them in
straight lines, the way the model measures those hops."""

import csv
import io
import zipfile

from .geo import Polyline

FEED_URL = "https://github.com/ismatsamadov/route_efficiency"
FAR_FROM_LINE_M = 100.0      # the validator's limit for a stop's distance from its trip's shape


def _hms(seconds):
    seconds = int(round(seconds))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def _beyond_ends(line, pts, far_m=FAR_FROM_LINE_M):
    """How many stops at the start and at the end lie past the ends of the line: more than
    far_m from it, with the line's first (or last) point the nearest point on it."""
    def past(pt, at_end):
        offset, chainage = min(line.project_all(*pt))
        return offset > far_m and (chainage >= line.length_m - 1.0 if at_end else chainage <= 1.0)

    lead = 0
    while lead < len(pts) and past(pts[lead], False):
        lead += 1
    trail = 0
    while trail < len(pts) - lead and past(pts[-1 - trail], True):
        trail += 1
    return lead, trail


def shape_points(pattern, network):
    """(lat, lon) points of a direction's shape, reaching its first and last stops."""
    if len(pattern.path) < 2:
        return list(pattern.path)
    pts = [(network.stops[s].lat, network.stops[s].lon) for s in pattern.stop_ids]
    lead, trail = _beyond_ends(Polyline(pattern.path), pts)
    return pts[:lead] + list(pattern.path) + pts[len(pts) - trail:]


def write_gtfs(path, network, a, headways, version, start_hour=6, feed_name="Baku buses, modelled from AYNA data"):
    """headways: {route id: (minutes, source)}; routes without one are left out.
    version names the network in feed_info.txt, e.g. "today" or "redesign"."""
    start = start_hour * 3600
    end = (start_hour + a.service_hours) * 3600
    served = sorted({s for (rid, _), p in network.patterns.items() if rid in headways for s in p.stop_ids})
    trips, stop_times, shapes, freqs = [], [], [], []
    for (rid, d), p in sorted(network.patterns.items()):
        if rid not in headways:
            continue
        trip, shape = f"{rid}_{d}", f"shape_{rid}_{d}"
        trips.append([rid, "daily", trip, network.stops[p.stop_ids[-1]].name, d - 1, shape])
        speed = a.cruise_mps(network.routes[rid].zone)
        t = 0.0
        for i, s in enumerate(p.stop_ids):
            if i:
                t += (p.chainage_m[i] - p.chainage_m[i - 1]) / speed + a.stop_loss_s
            stop_times.append([trip, _hms(start + t), _hms(start + t), s, i + 1])
        pts = shape_points(p, network)
        line = Polyline(pts) if len(pts) > 1 else None
        last, n = None, 0
        for k, (lat, lon) in enumerate(pts):
            dist = f"{line.cum[k]:.1f}" if line else "0"
            if dist == last:                     # a repeated point, or one within 5 cm of the last
                continue
            n += 1
            shapes.append([shape, f"{lat:.6f}", f"{lon:.6f}", n, dist])
            last = dist
        freqs.append([trip, _hms(start), _hms(end), int(round(headways[rid][0] * 60)), 0])

    tables = {
        "agency.txt": (["agency_id", "agency_name", "agency_url", "agency_timezone"],
                       [["baku", feed_name, "https://ayna.gov.az", "Asia/Baku"]]),
        "feed_info.txt": (["feed_publisher_name", "feed_publisher_url", "feed_lang", "feed_start_date",
                           "feed_end_date", "feed_version", "feed_contact_url"],
                          [["Ismat Samadov, independent researcher", FEED_URL, "az", "20260101", "20261231",
                            version, f"{FEED_URL}/issues"]]),
        "stops.txt": (["stop_id", "stop_code", "stop_name", "stop_lat", "stop_lon"],
                      [[s, network.stops[s].code or "", network.stops[s].name or "",
                        f"{network.stops[s].lat:.6f}", f"{network.stops[s].lon:.6f}"] for s in served]),
        "routes.txt": (["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
                       [[rid, "baku", network.routes[rid].number,
                         f"{network.routes[rid].first_point} - {network.routes[rid].last_point}", 3]
                        for rid in sorted(headways) if rid in network.routes]),
        "calendar.txt": (["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
                          "sunday", "start_date", "end_date"], [["daily", 1, 1, 1, 1, 1, 1, 1, "20260101", "20261231"]]),
        "trips.txt": (["route_id", "service_id", "trip_id", "trip_headsign", "direction_id", "shape_id"], trips),
        "stop_times.txt": (["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"], stop_times),
        "shapes.txt": (["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence", "shape_dist_traveled"], shapes),
        "frequencies.txt": (["trip_id", "start_time", "end_time", "headway_secs", "exact_times"], freqs),
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, (header, rows) in tables.items():
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator="\n")
            w.writerow(header)
            w.writerows(rows)
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))   # fixed date: same input, same file
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, buf.getvalue())
