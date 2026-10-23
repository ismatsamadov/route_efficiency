"""Geometry helpers: great-circle distance, a local metric projection for Baku,
polylines with distance-along-line ("chainage"), and stop-to-shape matching."""

import math

EARTH_RADIUS_M = 6371008.8


def haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in metres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


class LocalProjection:
    """Flat (equirectangular) projection centred on Baku.

    Good to better than 1% across the Absheron peninsula, which is all we need
    for nearest-point searches, buffers and grids."""

    def __init__(self, lat0=40.4, lon0=49.85):
        self.lat0, self.lon0 = lat0, lon0
        self.kx = math.radians(1) * EARTH_RADIUS_M * math.cos(math.radians(lat0))
        self.ky = math.radians(1) * EARTH_RADIUS_M

    def to_xy(self, lat, lon):
        return (lon - self.lon0) * self.kx, (lat - self.lat0) * self.ky

    def to_latlon(self, x, y):
        return self.lat0 + y / self.ky, self.lon0 + x / self.kx


PROJ = LocalProjection()


class Polyline:
    """A path given as (lat, lon) points, with cumulative length in metres."""

    def __init__(self, latlon):
        self.latlon = list(latlon)
        self.xy = [PROJ.to_xy(a, b) for a, b in self.latlon]
        self.cum = [0.0]
        for i in range(1, len(self.latlon)):
            self.cum.append(self.cum[-1] + haversine_m(*self.latlon[i - 1], *self.latlon[i]))

    @property
    def length_m(self):
        return self.cum[-1]

    def max_jump_m(self):
        """Longest straight segment between consecutive vertices."""
        return max((self.cum[i] - self.cum[i - 1] for i in range(1, len(self.cum))), default=0.0)

    def reversed(self):
        return Polyline(self.latlon[::-1])

    def project_all(self, lat, lon):
        """(offset_m, chainage_m) of the closest point on every segment."""
        px, py = PROJ.to_xy(lat, lon)
        out = []
        p, cum = self.xy, self.cum
        for j in range(len(p) - 1):
            (ax, ay), (bx, by) = p[j], p[j + 1]
            dx, dy = bx - ax, by - ay
            seg2 = dx * dx + dy * dy
            t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
            out.append((math.hypot(px - ax - t * dx, py - ay - t * dy), cum[j] + t * (cum[j + 1] - cum[j])))
        return out

    def point_at(self, chainage_m):
        """(lat, lon) at a distance along the line."""
        c = max(0.0, min(self.length_m, chainage_m))
        lo, hi = 0, len(self.cum) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.cum[mid] <= c:
                lo = mid
            else:
                hi = mid
        seg = self.cum[hi] - self.cum[lo]
        t = 0.0 if seg == 0 else (c - self.cum[lo]) / seg
        (a1, o1), (a2, o2) = self.latlon[lo], self.latlon[hi]
        return a1 + t * (a2 - a1), o1 + t * (o2 - o1)

    def slice_latlon(self, c0, c1):
        """The part of the line between two chainages, as (lat, lon) points."""
        if c1 < c0:
            c0, c1 = c1, c0
        pts = [self.point_at(c0)]
        pts += [p for p, c in zip(self.latlon, self.cum) if c0 < c < c1]
        pts.append(self.point_at(c1))
        return pts


def match_stops(line, stops_latlon, slack_m=150.0, tol_m=30.0, break_penalty_m=5000.0):
    """Place each stop on the line so that positions never go backwards.

    Every stop is projected onto every segment. Candidates are the best point of
    each run of segments within `slack_m` of the stop's nearest distance. A
    dynamic program then picks one candidate per stop, minimising total offset,
    while chainage may drop by at most `tol_m` between consecutive stops. A stop
    with no feasible in-order candidate costs `break_penalty_m` and counts as an
    order break.

    Returns one dict per stop: nearest_m (closest distance to the line),
    offset_m (distance at the chosen position), chainage_m, order_break."""
    cands, nearest = [], []
    for lat, lon in stops_latlon:
        proj = line.project_all(lat, lon)
        best = min(d for d, _ in proj)
        limit = best + slack_m
        runs, run = [], None
        for d, ch in proj:
            if d <= limit:
                if run is None or d < run[0]:
                    run = (d, ch)
            elif run is not None:
                runs.append(run)
                run = None
        if run is not None:
            runs.append(run)
        cands.append(runs)
        nearest.append(best)

    n = len(stops_latlon)
    cost = [[math.inf] * len(c) for c in cands]
    back = [[0] * len(c) for c in cands]
    brk = [[False] * len(c) for c in cands]
    for k, (d, _) in enumerate(cands[0]):
        cost[0][k] = d
    for i in range(1, n):
        prev = cands[i - 1]
        best_prev = min(range(len(prev)), key=lambda k: cost[i - 1][k])
        for k, (d, ch) in enumerate(cands[i]):
            bc, bk = math.inf, None
            for kp, (_, chp) in enumerate(prev):
                if chp <= ch + tol_m and cost[i - 1][kp] < bc:
                    bc, bk = cost[i - 1][kp], kp
            if bk is None:
                bc, bk, brk[i][k] = cost[i - 1][best_prev] + break_penalty_m, best_prev, True
            cost[i][k] = bc + d
            back[i][k] = bk
    k = min(range(len(cands[-1])), key=lambda k: cost[-1][k])
    out = [None] * n
    for i in range(n - 1, -1, -1):
        d, ch = cands[i][k]
        out[i] = {"nearest_m": nearest[i], "offset_m": d, "chainage_m": ch, "order_break": brk[i][k]}
        k = back[i][k]
    return out


def fit_score(line, stops_latlon):
    """How well a line explains a stop sequence: (order breaks, median offset in m)."""
    m = match_stops(line, stops_latlon)
    offsets = sorted(x["offset_m"] for x in m)
    return sum(x["order_break"] for x in m), offsets[len(offsets) // 2], m
