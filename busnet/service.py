"""How often each route runs, and what that service costs to operate.

The AYNA data has no timetables, so each route's headway comes from the first of:
  1. a headways file you supply (real data from AYNA or the operators),
  2. observed boardings, when headway_from_ridership is on: enough trips in each
     direction for each to carry boardings_per_trip riders over service_hours,
     kept between min_headway_min and max_headway_min,
  3. headway_by_zone for the route's working zone,
  4. default_headway_min.
Every headway carries its source, so results show what rests on assumptions."""

import csv
import math

SOURCES = ("supplied", "ridership", "zone", "default")


def run_time_s(pattern, network, a):
    """One trip in one direction: moving time plus the fixed loss at each stop after the first."""
    speed = a.cruise_mps(network.routes[pattern.route_id].zone)
    return pattern.length_m / speed + (len(pattern.stop_ids) - 1) * a.stop_loss_s


def fuel_l(pattern, a):
    """Diesel-equivalent litres for one trip: distance plus one stop-start cycle per stop."""
    return pattern.length_m / 1000 * a.fuel_l_per_km + (len(pattern.stop_ids) - 1) * a.fuel_l_per_stop


def load_headways(path):
    """{route number: headway in minutes} from a CSV with columns route and headway_min."""
    out = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row.get("route") and row.get("headway_min"):
                out[row["route"].strip()] = float(row["headway_min"])
    return out


def route_headways(network, a, observed=None, supplied=None):
    """{route id: (headway minutes, source)} for every route that has stops."""
    out = {}
    for rid, route in network.routes.items():
        if not network.patterns_of(rid):
            continue
        n = route.number
        if supplied and n in supplied:
            out[rid] = (supplied[n], "supplied")
        elif a.headway_from_ridership and observed and observed.get(n, 0) > 0:
            trips = observed[n] / 2 / a.boardings_per_trip
            out[rid] = (min(a.max_headway_min, max(a.min_headway_min, a.service_hours * 60 / trips)), "ridership")
        elif route.zone in a.headway_by_zone:
            out[rid] = (a.headway_by_zone[route.zone], "zone")
        else:
            out[rid] = (a.default_headway_min, "default")
    return out


def operations(network, a, headways):
    """Daily service the headways imply, per route and in total.

    A route with one direction is counted as if it ran the same way back."""
    per_route, total = {}, {"trips_per_day": 0.0, "bus_hours_per_day": 0.0, "bus_km_per_day": 0.0,
                            "fleet": 0, "fuel_l_per_day": 0.0}
    for rid, (headway, source) in headways.items():
        pats = network.patterns_of(rid)
        both = 2 / len(pats)
        trips_each_way = a.service_hours * 60 / headway
        run_s = sum(run_time_s(p, network, a) for p in pats) * both
        row = {
            "headway_min": headway, "headway_source": source,
            "trips_per_day": 2 * trips_each_way,
            "fleet": math.ceil(run_s / 60 * (1 + a.layover_share) / headway),
            "bus_hours_per_day": trips_each_way * run_s / 3600,
            "bus_km_per_day": trips_each_way * sum(p.length_m for p in pats) * both / 1000,
            "fuel_l_per_day": trips_each_way * sum(fuel_l(p, a) for p in pats) * both,
        }
        per_route[rid] = row
        for k in total:
            total[k] += row[k]
    total["co2_t_per_day"] = total["fuel_l_per_day"] * a.co2_kg_per_l / 1000
    total["fleet_vs_reference"] = total["fleet"] / a.reference_fleet if a.reference_fleet else None
    total["headway_sources"] = {s: sum(1 for h in headways.values() if h[1] == s) for s in SOURCES}
    return per_route, total
