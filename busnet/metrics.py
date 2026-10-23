"""Route and network efficiency metrics.

Geometry metrics (length, stop spacing, directness, duplication, detours) come
straight from the data. Time, fuel and accessibility metrics apply the values in
assumptions.py, so treat them as estimates for comparing one version of the
network with another, not as measurements of today's service."""

import heapq
import math
import random
from collections import Counter, defaultdict

from .geo import PROJ, haversine_m
from .graph import StopIndex, TransitGraph
from .service import fuel_l, operations, run_time_s

ZONE_EN = {
    "Şəhərdaxili": "Urban", "Şəhərdaxili (ekspres)": "Urban express",
    "Şəhərətrafı": "Suburban", "Şəhərətrafı (ekspres)": "Suburban express",
    "Qəsəbədaxili": "Within a settlement", "Qəsəbələrarası": "Between settlements",
    "Şəhərlərarası": "Intercity",
}


# ---------------------------------------------------------------- street graph for directness

class StreetGraph:
    """Undirected graph of the stop-to-stop links buses drive, plus short connectors
    between stops less than link_m apart (opposite sides of a street, corners of a
    junction). Shortest paths on it approximate the most direct way a bus could go
    using streets that some route already uses."""

    def __init__(self, network, link_m=80.0):
        self.adj = defaultdict(dict)
        for p in network.patterns.values():
            for a, b, d in p.hops():
                if a != b and d < self.adj[a].get(b, math.inf):
                    self.adj[a][b] = self.adj[b][a] = d
        served = [network.stops[s] for s in network.served_stop_ids()]
        index = StopIndex(served)
        for s in served:
            for d, t in index.within(s.lat, s.lon, link_m):
                if t.id != s.id and d < self.adj[s.id].get(t.id, math.inf):
                    self.adj[s.id][t.id] = self.adj[t.id][s.id] = d

    def shortest_m(self, src, dst):
        dist, heap = {src: 0.0}, [(0.0, src)]
        while heap:
            c, u = heapq.heappop(heap)
            if u == dst:
                return c
            if c > dist[u]:
                continue
            for v, w in self.adj[u].items():
                if c + w < dist.get(v, math.inf):
                    dist[v] = c + w
                    heapq.heappush(heap, (c + w, v))
        return math.inf


# ---------------------------------------------------------------- per route direction

def find_detours(pattern, pts, min_excess_m=1500.0, min_ratio=2.5, max_span=12):
    """Stretches where the bus travels far more than the straight line between two of its stops.

    A candidate runs from stop i to stop j (at most max_span stops, and at most 40% of
    the route) with along-path distance at least min_ratio times the straight line and
    at least min_excess_m longer. Overlapping candidates keep the largest."""
    ch, n = pattern.chainage_m, len(pts)
    span = max(3, min(max_span, int(0.4 * n)))
    cands = []
    for i in range(n):
        for j in range(i + 2, min(n, i + span + 1)):
            along = ch[j] - ch[i]
            if along < min_excess_m:
                continue
            straight = haversine_m(*pts[i], *pts[j])
            if along - straight >= min_excess_m and along >= min_ratio * straight:
                cands.append((along - straight, i, j, along, straight))
    chosen = []
    for c in sorted(cands, reverse=True):
        if all(c[2] <= o[1] or c[1] >= o[2] for o in chosen):
            chosen.append(c)
    return [{"from_index": i, "to_index": j, "along_m": along, "straight_m": straight, "excess_m": exc}
            for exc, i, j, along, straight in sorted(chosen, key=lambda c: c[1])]


def pattern_metrics(p, network, a, street, hop_routes):
    stops = network.stops
    pts = [(stops[s].lat, stops[s].lon) for s in p.stop_ids]
    gaps = [d for _, _, d in p.hops()]
    straight_ends = haversine_m(*pts[0], *pts[-1])
    shortest = street.shortest_m(p.stop_ids[0], p.stop_ids[-1])
    ratios = []
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            sl = haversine_m(*pts[i], *pts[j])
            if sl >= 1000:
                ratios.append((p.chainage_m[j] - p.chainage_m[i]) / sl)
    shared = sum(d for x, y, d in p.hops() if len(hop_routes[(x, y)]) >= 2)
    heavy = sum(d for x, y, d in p.hops() if len(hop_routes[(x, y)]) >= 5)
    run = run_time_s(p, network, a)
    detours = find_detours(p, pts)
    e2e = p.length_m / straight_ends if straight_ends >= 1000 else None
    return {
        "stops": len(p.stop_ids),
        "length_km": p.length_m / 1000,
        "shape": route_shape(e2e, p.length_m / 1000, straight_ends / 1000),
        "path_source": p.path_source,
        "median_gap_m": sorted(gaps)[len(gaps) // 2] if gaps else 0.0,
        "gaps_under_200m": sum(g < 200 for g in gaps),
        "gaps_under_300m": sum(g < 300 for g in gaps),
        "end_to_end_circuity": e2e,
        "excess_over_shortest_pct": (100 * (p.length_m / shortest - 1)) if 0 < shortest < math.inf else None,
        "rider_circuity": sum(ratios) / len(ratios) if ratios else None,
        "detours": detours,
        "shared_share": shared / p.length_m if p.length_m else 0.0,
        "heavy_shared_share": heavy / p.length_m if p.length_m else 0.0,
        "run_min": run / 60,
        "stop_time_share": (len(p.stop_ids) - 1) * a.stop_loss_s / run if run else 0.0,
        "fuel_l": fuel_l(p, a),
    }


def hop_route_sets(network):
    out = defaultdict(set)
    for p in network.patterns.values():
        for x, y, _ in p.hops():
            out[(x, y)].add(p.route_id)
    return out


def near_duplicates(network, min_share=0.85, min_stops=10):
    """Pairs where most of one route's stops are also served by one other route.

    Express routes are left out: skipping stops of a local route is their purpose."""
    stops_of = defaultdict(set)
    for p in network.patterns.values():
        stops_of[p.route_id] |= set(p.stop_ids)
    local = [r for r in stops_of if "ekspres" not in network.routes[r].zone]
    rows = []
    for a in local:
        for b in local:
            if a != b and len(stops_of[a]) >= min_stops:
                share = len(stops_of[a] & stops_of[b]) / len(stops_of[a])
                if share >= min_share:
                    rows.append({"route": network.number(a), "inside_route": network.number(b),
                                 "share_of_stops": share, "route_stops": len(stops_of[a]),
                                 "other_route_stops": len(stops_of[b]),
                                 "same_carrier": network.routes[a].carrier == network.routes[b].carrier})
    rows.sort(key=lambda r: (-r["share_of_stops"], _route_key(r["route"])))
    return rows


def route_shape(end_to_end_circuity, length_km, straight_km):
    """Classify a route direction by how directly it connects its two ends."""
    if straight_km < 1.0 or end_to_end_circuity is None or end_to_end_circuity > 3.0:
        return "loop"
    if end_to_end_circuity > 2.0:
        return "very indirect"
    if end_to_end_circuity > 1.4:
        return "indirect"
    return "direct"


def trunk_corridors(network, min_routes=8, min_km=1.0):
    """Stretches of consecutive stop-to-stop links that at least min_routes routes share.

    These are where many routes stack up on one street, the usual candidates for a
    single high-frequency trunk line, bus lanes or consolidation."""
    hop_routes = hop_route_sets(network)
    length = {}
    for p in network.patterns.values():
        for x, y, d in p.hops():
            length[(x, y)] = min(d, length.get((x, y), math.inf))
    heavy = {h for h, rs in hop_routes.items() if len(rs) >= min_routes}
    out_edges, in_deg = defaultdict(list), Counter()
    for x, y in heavy:
        out_edges[x].append(y)
        in_deg[y] += 1
    starts = [x for x in out_edges if in_deg[x] != 1 or len(out_edges[x]) != 1]
    seen, corridors = set(), []
    for x in starts:
        for y in out_edges[x]:
            if (x, y) in seen:
                continue
            seen.add((x, y))
            path, cur = [x, y], y
            while in_deg[cur] == 1 and len(out_edges[cur]) == 1 and (cur, out_edges[cur][0]) not in seen:
                nxt = out_edges[cur][0]
                seen.add((cur, nxt))
                path.append(nxt)
                cur = nxt
            hops = list(zip(path, path[1:]))
            km = sum(length[h] for h in hops) / 1000
            if km >= min_km:
                routes = set().union(*(hop_routes[h] for h in hops))
                first, last = network.stops[path[0]], network.stops[path[-1]]
                via = ""
                if haversine_m(first.lat, first.lon, last.lat, last.lon) < 1000:     # out and back: name the turn
                    far = max(path, key=lambda s: haversine_m(first.lat, first.lon, network.stops[s].lat, network.stops[s].lon))
                    via = network.stops[far].name
                corridors.append({
                    "from_stop": first.name, "to_stop": last.name, "via_stop": via,
                    "km": km, "stops": len(path),
                    "mean_routes_per_link": sum(len(hop_routes[h]) for h in hops) / len(hops),
                    "max_routes_on_a_link": max(len(hop_routes[h]) for h in hops),
                    "routes": " ".join(sorted((network.number(r) for r in routes), key=_route_key)),
                    "stop_ids": path,
                })
    corridors.sort(key=lambda c: -c["km"] * c["mean_routes_per_link"])
    return corridors


# ---------------------------------------------------------------- population

def coverage_by_route(network, zones, radius_m):
    """For each population zone, which routes have a stop within radius_m."""
    rat = network.routes_at_stop()
    index = StopIndex([network.stops[s] for s in network.served_stop_ids()])
    out = []
    for lat, lon, pop in zones:
        routes = set()
        for _, s in index.within(lat, lon, radius_m):
            routes |= rat[s.id]
        out.append(routes)
    return out


# ---------------------------------------------------------------- route table

def route_table(network, a, zones=None, ridership=None, headways=None):
    """One row per route that has stops, combining both directions.

    ridership, if given, maps route number to observed weekday boardings;
    headways, if given, adds the daily service they imply (see service.py)."""
    ops = operations(network, a, headways)[0] if headways else {}
    street = StreetGraph(network)
    hop_routes = hop_route_sets(network)
    pop_cov = coverage_by_route(network, zones, a.coverage_radius_m) if zones else None
    pop_route, pop_unique = Counter(), Counter()
    if pop_cov:
        for (_, _, pop), routes in zip(zones, pop_cov):
            for r in routes:
                pop_route[r] += pop
            if len(routes) == 1:
                pop_unique[next(iter(routes))] += pop
    rows = []
    for rid, route in sorted(network.routes.items(), key=lambda kv: _route_key(kv[1].number)):
        pats = network.patterns_of(rid)
        if not pats:
            continue
        ms = [pattern_metrics(p, network, a, street, hop_routes) for p in pats]

        def avg(key):
            vals = [m[key] for m in ms if m[key] is not None]
            return sum(vals) / len(vals) if vals else None

        row = {
            "route": route.number,
            "zone": ZONE_EN.get(route.zone, route.zone),
            "region": route.region,
            "carrier": route.carrier,
            "fare_azn": route.fare_azn,
            "stops_per_direction": avg("stops"),
            "one_way_km": avg("length_km"),
            "geometry": "shape" if all(m["path_source"] == "shape" for m in ms) else "partly straight lines",
            "shape": max((m["shape"] for m in ms), key=["direct", "indirect", "very indirect", "loop"].index),
            "median_stop_gap_m": avg("median_gap_m"),
            "gaps_under_200m": sum(m["gaps_under_200m"] for m in ms),
            "gaps_under_300m": sum(m["gaps_under_300m"] for m in ms),
            "end_to_end_circuity": avg("end_to_end_circuity"),
            "excess_over_shortest_pct": avg("excess_over_shortest_pct"),
            "rider_circuity": avg("rider_circuity"),
            "detours": sum(len(m["detours"]) for m in ms),
            "detour_excess_km": sum(d["excess_m"] for m in ms for d in m["detours"]) / 1000,
            "shared_share": avg("shared_share"),
            "heavy_shared_share": avg("heavy_shared_share"),
            "round_trip_min": sum(m["run_min"] for m in ms) * (2 / len(ms)),
            "stop_time_share": avg("stop_time_share"),
            "fuel_l_round_trip": sum(m["fuel_l"] for m in ms) * (2 / len(ms)),
        }
        row["co2_kg_round_trip"] = row["fuel_l_round_trip"] * a.co2_kg_per_l
        if pop_cov:
            row["population_within_radius"] = pop_route[rid]
            row["population_only_this_route"] = pop_unique[rid]
        if ridership is not None:
            b = ridership.get(route.number)
            row["weekday_boardings"] = b
            row["boardings_per_km"] = b / row["one_way_km"] if b is not None and row["one_way_km"] else None
        if rid in ops:
            row.update({k: ops[rid][k] for k in ("headway_min", "headway_source", "trips_per_day", "fleet",
                                                 "bus_hours_per_day", "bus_km_per_day", "fuel_l_per_day")})
        rows.append(row)
    return rows


def detour_table(network, a, zones=None):
    """Every detour found, with what it costs through-riders and whom it serves."""
    rat = network.routes_at_stop()
    pop_cov = coverage_by_route(network, zones, a.coverage_radius_m) if zones else None
    stop_zones = defaultdict(set)
    if pop_cov:
        index = StopIndex([network.stops[s] for s in network.served_stop_ids()])
        for zi, (lat, lon, _) in enumerate(zones):
            for _, s in index.within(lat, lon, a.coverage_radius_m):
                stop_zones[s.id].add(zi)
    rows = []
    for key, p in sorted(network.patterns.items()):
        stops = network.stops
        pts = [(stops[s].lat, stops[s].lon) for s in p.stop_ids]
        speed = a.cruise_mps(network.routes[p.route_id].zone)
        for d in find_detours(p, pts):
            inner = p.stop_ids[d["from_index"] + 1:d["to_index"]]
            row = {
                "route": network.number(p.route_id), "direction": p.direction,
                "from_stop": stops[p.stop_ids[d["from_index"]]].name,
                "to_stop": stops[p.stop_ids[d["to_index"]]].name,
                "stops_inside": len(inner),
                "inside_stops_only_this_route": sum(1 for s in inner if rat[s] == {p.route_id}),
                "along_km": d["along_m"] / 1000, "straight_km": d["straight_m"] / 1000,
                "excess_km": d["excess_m"] / 1000,
                "extra_min_per_trip": (d["excess_m"] / speed + len(inner) * a.stop_loss_s) / 60,
            }
            if pop_cov:
                zs = set().union(*(stop_zones[s] for s in inner)) if inner else set()
                row["population_only_this_route"] = sum(zones[z][2] for z in zs if pop_cov[z] == {p.route_id})
            rows.append(row)
    return rows


# ---------------------------------------------------------------- door-to-door accessibility

def evaluate_od(network, a, zones, n_origins=300, seed=7, headways=None, attraction=None):
    """Estimated door-to-door travel between places, weighted by a gravity model.

    Origins are sampled in proportion to population. From each origin, trips go to
    every other zone in proportion to population x exp(-distance / trip_decay_km).
    A trip may walk to a stop up to max_access_walk_m away, ride, change buses
    (walking up to max_transfer_walk_m), and walk to the destination. Trips under
    2 km may also be walked entirely. Each trip is pushed back along its path to
    count the boardings it makes on every route.

    headways sets each route's waiting time; attraction, if given, replaces
    population as the pull of each zone on trip ends (see destinations.py)."""
    graph = TransitGraph(network, a, headways)
    index = StopIndex([network.stops[s] for s in graph.stop_ids])
    walk = a.walk_detour / a.walk_speed_mps
    access = [[(s.id, d * walk) for d, s in index.within(lat, lon, a.max_access_walk_m)] for lat, lon, _ in zones]
    acc_nodes = [[graph.arrival(s) for s, _ in acc] for acc in access]
    acc_walk = [[w for _, w in acc] for acc in access]
    xy = [PROJ.to_xy(lat, lon) for lat, lon, _ in zones]
    zx, zy, zpop = [p[0] for p in xy], [p[1] for p in xy], [z[2] for z in zones]
    zatt = attraction or zpop

    rng = random.Random(seed)
    keyed = sorted(((rng.random() ** (1.0 / w), i) for i, w in enumerate(zpop) if w > 0), reverse=True)
    origins = [i for _, i in keyed[:n_origins]]

    cutoff = a.max_trip_min * 60
    decay_m = a.trip_decay_km * 1000
    penalty = a.transfer_penalty_s
    acc = Counter()
    transfers = Counter()
    boardings = Counter()                       # route id -> modelled boardings (relative)
    for o in origins:
        sources = {}
        for s, w in access[o]:
            node = graph.departure(s)
            sources[node] = min(w, sources.get(node, math.inf))
        dist = boards = pred = settled = None
        if sources:
            dist, boards, pred, settled = graph.search(sources, cutoff)
        ox, oy, o_access = zx[o], zy[o], bool(access[o])
        weights, results = [], []
        for d in range(len(zones)):
            if d == o or zatt[d] <= 0:
                continue
            dm = math.hypot(zx[d] - ox, zy[d] - oy)
            weights.append(zatt[d] * math.exp(-dm / decay_m))
            best, nb, end = math.inf, None, None
            if dist is not None:
                for node, w in zip(acc_nodes[d], acc_walk[d]):
                    c = dist[node] + w - penalty
                    if c < best:
                        best, nb, end = c, boards[node], node
            if dm <= 2000 and dm * walk < best:
                best, nb, end = dm * walk, 0, None
            results.append((best, nb, o_access and bool(acc_nodes[d]), end, dm))
        total = sum(weights)
        if not total:
            continue
        flow = {}
        for w, (t, nb, has_access, end, dm) in zip(weights, results):
            w /= total
            acc["demand"] += w
            acc["trip_km"] += w * dm / 1000
            if not has_access:
                acc["no_stop_nearby"] += w
            if t <= cutoff:
                acc["reachable"] += w
                acc["time_s"] += w * t
                for m in (30, 45, 60):
                    if t <= m * 60:
                        acc[f"within_{m}"] += w
                transfers["walk only" if nb == 0 else min(nb - 1, 3)] += w
                if end is not None:
                    flow[end] = flow.get(end, 0.0) + w
        # Push each trip back along its path; every boarding edge it crosses is a boarding on that route.
        if flow and settled:
            for n in reversed(settled):
                f = flow.get(n)
                if not f or pred[n] < 0:
                    continue
                p = pred[n]
                flow[p] = flow.get(p, 0.0) + f
                if graph.node_route[n] >= 0 and graph.is_departure(p):
                    boardings[graph.node_route[n]] += f
    n = acc["demand"] or 1
    reach = acc["reachable"] or 1
    return {
        "origins_sampled": len(origins),
        "mean_door_to_door_min": acc["time_s"] / reach / 60,
        "share_reachable": acc["reachable"] / n,
        "share_within_30_min": acc["within_30"] / n,
        "share_within_45_min": acc["within_45"] / n,
        "share_within_60_min": acc["within_60"] / n,
        "share_trips_without_stop_nearby": acc["no_stop_nearby"] / n,
        "mean_trip_km_straight_line": acc["trip_km"] / n,
        "transfers": {("3+" if k == 3 else str(k)): v / reach for k, v in sorted(transfers.items(), key=lambda kv: str(kv[0]))},
        "modelled_boardings": dict(boardings),
    }


def compare_ridership(network, modelled, observed):
    """Observed against modelled boardings for routes present in both.

    Both are turned into shares of their own total over the shared routes, so the
    gravity model only has to get the relative pattern right. Returns (rows, fit)
    where fit has Spearman's rank correlation and the correlation of log shares."""
    num = {r.number: k for k, r in network.routes.items() if network.patterns_of(k)}
    common = [(n, num[n]) for n in observed if n in num]
    if len(common) < 3:
        return [], {"routes_compared": len(common)}
    obs_total = sum(observed[n] for n, _ in common)
    mod_total = sum(modelled.get(rid, 0.0) for _, rid in common) or 1.0
    rows = []
    for n, rid in common:
        o, m = observed[n] / obs_total, modelled.get(rid, 0.0) / mod_total
        rows.append({"route": n, "observed_weekday_boardings": observed[n], "observed_share": o,
                     "modelled_share": m, "modelled_over_observed": m / o if o else None})
    rows.sort(key=lambda r: -r["observed_share"])

    def ranks(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        out = [0.0] * len(vals)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            for k in range(i, j + 1):
                out[order[k]] = (i + j) / 2
            i = j + 1
        return out

    def pearson(x, y):
        mx, my = sum(x) / len(x), sum(y) / len(y)
        sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
        sx = math.sqrt(sum((a - mx) ** 2 for a in x))
        sy = math.sqrt(sum((b - my) ** 2 for b in y))
        return sxy / (sx * sy) if sx and sy else None

    obs = [r["observed_share"] for r in rows]
    mod = [r["modelled_share"] for r in rows]
    floor = min((v for v in mod if v > 0), default=1e-9) / 2
    return rows, {"routes_compared": len(rows), "spearman": pearson(ranks(obs), ranks(mod)),
                  "pearson_of_log_shares": pearson([math.log(v) for v in obs], [math.log(max(v, floor)) for v in mod])}


# ---------------------------------------------------------------- network summary

def network_summary(network, a, zones=None, od_origins=300, headways=None, attraction=None):
    pats = list(network.patterns.values())
    route_km = sum(p.length_m for p in pats) / 1000
    corridor = {}
    for p in pats:
        for x, y, d in p.hops():
            corridor[(x, y)] = min(d, corridor.get((x, y), math.inf))
    corridor_km = sum(corridor.values()) / 1000
    gaps = sorted(d for p in pats for _, _, d in p.hops())
    run_h = sum(run_time_s(p, network, a) for p in pats) / 3600
    stop_h = sum((len(p.stop_ids) - 1) * a.stop_loss_s for p in pats) / 3600
    fuel = sum(fuel_l(p, a) for p in pats)
    stop_fuel = sum((len(p.stop_ids) - 1) * a.fuel_l_per_stop for p in pats)
    hop_routes = hop_route_sets(network)
    busiest = max(len(v) for v in hop_routes.values())

    served = [network.stops[s] for s in network.served_stop_ids()]
    cells = set()
    r = a.coverage_radius_m
    for s in served:
        x, y = PROJ.to_xy(s.lat, s.lon)
        for i in range(int((x - r) // 100), int((x + r) // 100) + 1):
            for j in range(int((y - r) // 100), int((y + r) // 100) + 1):
                if (i * 100 + 50 - x) ** 2 + (j * 100 + 50 - y) ** 2 <= r * r:
                    cells.add((i, j))

    out = {
        "routes_with_stops": len({p.route_id for p in pats}),
        "route_directions": len(pats),
        "served_stops": len(served),
        "route_km_one_way_total": route_km,
        "corridor_km": corridor_km,
        "duplication_ratio": route_km / corridor_km if corridor_km else None,
        "median_stop_gap_m": gaps[len(gaps) // 2],
        "share_stop_gaps_under_200m": sum(g < 200 for g in gaps) / len(gaps),
        "share_stop_gaps_under_300m": sum(g < 300 for g in gaps) / len(gaps),
        "most_routes_on_one_link": busiest,
        "hours_one_trip_each_direction_every_route": run_h,
        "share_of_that_time_lost_at_stops": stop_h / run_h,
        "fuel_l_one_trip_each_direction_every_route": fuel,
        "share_of_that_fuel_from_stops": stop_fuel / fuel,
        "area_within_coverage_radius_km2": len(cells) * 0.01,
    }
    if zones:
        cov = coverage_by_route(network, zones, a.coverage_radius_m)
        total = sum(z[2] for z in zones)
        covered = sum(z[2] for z, c in zip(zones, cov) if c)
        out["population_in_study_area"] = total
        out["population_within_coverage_radius"] = covered
        out["share_population_covered"] = covered / total if total else None
        if od_origins:
            out["accessibility"] = evaluate_od(network, a, zones, od_origins, headways=headways, attraction=attraction)
    if headways:
        out["operations"] = operations(network, a, headways)[1]
    return out


def _route_key(number):
    digits = "".join(c for c in number if c.isdigit())
    return (int(digits) if digits else 0, number)
