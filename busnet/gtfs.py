"""Write a network as a GTFS feed, the standard format other transit tools read.

Each route direction becomes one trip that repeats every headway between the start and
end of service (frequencies.txt). Times between stops follow the same model as the
metrics: distance at the zone's moving speed plus the fixed loss at each stop. A feed
written with estimated headways describes the model, not an official timetable."""

import csv
import io
import zipfile

from .geo import Polyline


def _hms(seconds):
    seconds = int(round(seconds))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def write_gtfs(path, network, a, headways, start_hour=6, feed_name="Baku buses, modelled from AYNA data"):
    """headways: {route id: (minutes, source)}; routes without one are left out."""
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
        line = Polyline(p.path) if len(p.path) > 1 else None
        for k, (lat, lon) in enumerate(p.path):
            shapes.append([shape, f"{lat:.6f}", f"{lon:.6f}", k + 1, f"{line.cum[k]:.1f}" if line else "0"])
        freqs.append([trip, _hms(start), _hms(end), int(round(headways[rid][0] * 60)), 0])

    tables = {
        "agency.txt": (["agency_id", "agency_name", "agency_url", "agency_timezone"],
                       [["baku", feed_name, "https://ayna.gov.az", "Asia/Baku"]]),
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
