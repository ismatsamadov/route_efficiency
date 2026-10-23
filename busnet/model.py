"""Load the AYNA SQLite snapshot into plain objects, repairing the defects found in the audit.

Repairs are detected from the data rather than hard-coded, so they still apply after a re-scrape:
  - a stop list repeated twice back to back is cut to one copy
  - shape coordinates that only make sense with latitude and longitude swapped are swapped
  - shapes with unusable coordinates (latitude equal to longitude, or nowhere near the stops) are dropped
  - shapes stored under the wrong direction are swapped, and shapes stored backwards are reversed,
    when that puts the stops in order and closer to the line
  - shapes that still cannot explain their stops (many order breaks, straight jumps over 5 km) are
    dropped; those directions fall back to straight lines between stops
Every repair is listed in Network.repairs."""

import copy
import sqlite3
import statistics
from collections import defaultdict
from dataclasses import dataclass

from .geo import Polyline, fit_score, haversine_m


@dataclass
class Stop:
    id: int
    code: str
    name: str
    lat: float
    lon: float
    is_hub: bool


@dataclass
class Route:
    id: int
    number: str
    carrier: str
    first_point: str
    last_point: str
    declared_length_km: float     # round trip, see the audit
    zone: str                     # working zone, e.g. Şəhərdaxili (urban)
    region: str
    fare_azn: float
    payment: str                  # Kart (card) or Nəğd (cash)
    card_since: str


@dataclass
class Pattern:
    """One direction of one route: its ordered stops and the path between them."""
    route_id: int
    direction: int
    stop_ids: list
    chainage_m: list      # distance along the path at each stop; starts at 0
    path: list            # (lat, lon) points from the first stop to the last
    path_source: str      # "shape", or "stops" when drawn as straight lines between stops

    @property
    def length_m(self):
        return self.chainage_m[-1]

    def hops(self):
        """(from_stop, to_stop, metres along the path) for each consecutive pair."""
        return [(a, b, cb - ca) for a, b, ca, cb in
                zip(self.stop_ids, self.stop_ids[1:], self.chainage_m, self.chainage_m[1:])]


class Network:
    def __init__(self, routes, stops, patterns, repairs=()):
        self.routes = routes          # route id -> Route
        self.stops = stops            # stop id -> Stop
        self.patterns = patterns      # (route id, direction) -> Pattern
        self.repairs = list(repairs)

    def number(self, route_id):
        return self.routes[route_id].number

    def patterns_of(self, route_id):
        return [p for (r, _), p in sorted(self.patterns.items()) if r == route_id]

    def served_stop_ids(self):
        return {s for p in self.patterns.values() for s in p.stop_ids}

    def routes_at_stop(self):
        out = defaultdict(set)
        for p in self.patterns.values():
            for s in p.stop_ids:
                out[s].add(p.route_id)
        return out

    def copy(self):
        """A copy whose patterns can be edited without touching this network."""
        return Network(self.routes, self.stops, copy.deepcopy(self.patterns), self.repairs)


# ---------------------------------------------------------------- loading

def _read(db_path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    routes = {r["bus_id"]: Route(r["bus_id"], r["number"], " ".join((r["carrier"] or "").split()),
                                 r["first_point"], r["last_point"], r["route_length_km"],
                                 r["working_zone"], r["region"], r["tariff_azn"], r["payment_type"],
                                 r["card_payment_since"])
              for r in con.execute("SELECT * FROM buses")}
    stops = {r["stop_id"]: Stop(r["stop_id"], r["code"], r["name"], r["lat"], r["lon"], bool(r["is_hub"]))
             for r in con.execute("SELECT * FROM stops")}
    seqs = defaultdict(list)
    for r in con.execute("SELECT bus_id, direction, stop_id FROM bus_stops ORDER BY bus_id, direction, seq"):
        seqs[(r["bus_id"], r["direction"])].append(r["stop_id"])
    shapes = defaultdict(list)
    for r in con.execute("SELECT bus_id, direction, lat, lon FROM route_points ORDER BY bus_id, direction, seq"):
        shapes[(r["bus_id"], r["direction"])].append((r["lat"], r["lon"]))
    con.close()
    return routes, stops, dict(seqs), dict(shapes)


def _chainages(match, stop_pts):
    """Monotone distance along the path at each stop, starting at 0.

    A hop is never shorter than the straight line between its stops, which also
    absorbs the occasional out-of-order match."""
    out = [0.0]
    for i in range(1, len(match)):
        along = match[i]["chainage_m"] - match[i - 1]["chainage_m"]
        out.append(out[-1] + max(along, haversine_m(*stop_pts[i - 1], *stop_pts[i])))
    return out


def _straight_pattern(route_id, d, seq, pts):
    ch = [0.0]
    for a, b in zip(pts, pts[1:]):
        ch.append(ch[-1] + haversine_m(*a, *b))
    return Pattern(route_id, d, seq, ch, list(pts), "stops")


def load_network(db_path, repair=True):
    """Read ayna.db. With repair=True, fix the known defect types and log each fix."""
    routes, stops, seqs, shapes = _read(db_path)
    log = []
    num = {k: r.number for k, r in routes.items()}

    if repair:
        for key, seq in seqs.items():
            h = len(seq) // 2
            if len(seq) % 2 == 0 and h > 2 and seq[:h] == seq[h:]:
                seqs[key] = seq[:h]
                log.append(f"{num[key[0]]} d{key[1]}: stop list was repeated twice; kept one copy")

    patterns = {}
    for rid in sorted(routes):
        dirs = [d for d in (1, 2) if seqs.get((rid, d))]
        if not dirs:
            continue
        pts = {d: [(stops[s].lat, stops[s].lon) for s in seqs[(rid, d)]] for d in dirs}
        raw = {d: shapes[(rid, d)] for d in (1, 2) if len(shapes.get((rid, d), [])) >= 2}
        if not repair:
            for d in dirs:
                if d in raw:
                    line = Polyline(raw[d])
                    _, _, m = fit_score(line, pts[d])
                    patterns[(rid, d)] = _pattern_from(rid, d, seqs[(rid, d)], pts[d], line, m)
                else:
                    patterns[(rid, d)] = _straight_pattern(rid, d, seqs[(rid, d)], pts[d])
            continue
        lines = _usable_shapes(num[rid], raw, [p for d in dirs for p in pts[d]], log)
        chosen = _assign_shapes(num[rid], dirs, pts, lines, log)
        for d in dirs:
            if d in chosen:
                line, m = chosen[d]
                patterns[(rid, d)] = _pattern_from(rid, d, seqs[(rid, d)], pts[d], line, m)
            else:
                patterns[(rid, d)] = _straight_pattern(rid, d, seqs[(rid, d)], pts[d])
    return Network(routes, stops, patterns, log)


def _pattern_from(rid, d, seq, pts, line, match):
    ch = _chainages(match, pts)
    c0, c1 = match[0]["chainage_m"], max(match[0]["chainage_m"], match[-1]["chainage_m"])
    return Pattern(rid, d, seq, ch, line.slice_latlon(c0, c1), "shape")


def _usable_shapes(number, raw, stop_pts, log):
    """Drop or swap shapes whose coordinates cannot belong to this route."""
    clat = statistics.median(a for a, _ in stop_pts)
    clon = statistics.median(b for _, b in stop_pts)

    def far(pts):
        mlat = statistics.median(a for a, _ in pts)
        mlon = statistics.median(b for _, b in pts)
        return haversine_m(clat, clon, mlat, mlon) > 50_000

    out = {}
    for d, pts in raw.items():
        if all(a == b for a, b in pts):
            log.append(f"{number} d{d}: shape has latitude equal to longitude everywhere; dropped")
        elif far(pts):
            swapped = [(b, a) for a, b in pts]
            if far(swapped):
                log.append(f"{number} d{d}: shape lies nowhere near the route's stops; dropped")
            else:
                out[d] = Polyline(swapped)
                log.append(f"{number} d{d}: shape had latitude and longitude swapped; swapped back")
        else:
            out[d] = Polyline(pts)
    return out


def _best_variant(line, stop_pts):
    """Score a shape and its reverse against a stop sequence; return the better one."""
    b1, m1, match1 = fit_score(line, stop_pts)
    if b1 == 0:
        return (b1, m1, line, match1, False)
    rev = line.reversed()
    b2, m2, match2 = fit_score(rev, stop_pts)
    if (b2, m2) < (b1, m1):
        return (b2, m2, rev, match2, True)
    return (b1, m1, line, match1, False)


def _assign_shapes(number, dirs, pts, lines, log):
    """Decide which stored shape belongs to which direction, and which way round."""
    if not lines:
        return {}
    fits = {(d, sd): _best_variant(lines[sd], pts[d]) for d in dirs for sd in lines}

    def total(assign):
        return (sum(fits[(d, sd)][0] for d, sd in assign.items()),
                sum(fits[(d, sd)][1] for d, sd in assign.items()))

    options = []
    if len(dirs) == 2 and len(lines) == 2:
        options = [{1: 1, 2: 2}, {1: 2, 2: 1}]
    elif len(lines) == 1:
        (sd,) = lines
        options = [{d: sd} for d in dirs]
        options.sort(key=lambda a: next(iter(a)) != sd)        # stored direction first
    else:
        options = [{d: d for d in dirs if d in lines}]
    # Move a shape only on clear evidence: many fewer stops out of order, or no more
    # breaks and a line that sits much closer to the stops.
    n_total = sum(len(pts[d]) for d in dirs)
    best = options[0]
    for alt in options[1:]:
        (b0, m0), (b1, m1) = total(best), total(alt)
        if b1 <= b0 - max(2, 0.2 * n_total) or (b1 <= b0 and m1 < 0.7 * m0):
            best = alt
    if any(d != sd for d, sd in best.items()):
        moved = ", ".join(f"stored d{sd} -> d{d}" for d, sd in best.items() if d != sd)
        log.append(f"{number}: shapes were filed under the wrong direction ({moved})")

    chosen = {}
    for d, sd in best.items():
        breaks, median, line, match, reversed_ = fits[(d, sd)]
        n = len(pts[d])
        if breaks > max(2, 0.1 * n) or median > 60 or line.max_jump_m() > 5_000:
            why = (f"{breaks} stops out of order" if breaks > max(2, 0.1 * n)
                   else f"median offset {median:.0f} m" if median > 60
                   else f"straight jump of {line.max_jump_m() / 1000:.1f} km")
            log.append(f"{number} d{d}: shape cannot explain its stops ({why}); using straight lines between stops")
            continue
        if reversed_:
            log.append(f"{number} d{d}: shape was stored backwards; reversed")
        chosen[d] = (line, match)
    return chosen
