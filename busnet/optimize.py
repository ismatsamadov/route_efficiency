"""Search for a better route network with today's fleet.

Starting from today's routes, the search tries the kinds of change that network
redesigns elsewhere have used, and keeps a change only if it lowers riders' average
door-to-door time (a trip that cannot be made within max_trip_min counts at that limit)
without leaving more people than allowed with no stop within max_access_walk_m:

  merge       drop a route whose stops are mostly served by another route that remains;
              its buses go to the routes it overlaps
  drop        drop a route that carries few modelled riders per bus; its buses go to
              the routes it overlaps, or across the network if none do
  straighten  replace a detour with the shortest path along streets that buses already
              use, stopping at the stops on that path
  stops       remove closely spaced stops (stop balancing)
  shift       move buses from the routes with the fewest modelled riders per bus to the
              routes with the most

The fleet never changes. A route that gets shorter keeps its buses and runs more often;
a dropped route's buses go to other routes. No route runs less often than
max_headway_min or more often than min_headway_min. Every candidate is scored on the
same sample of trips, so comparisons are fair; redesign.py then checks the result on a
different sample.
"""

import heapq
import math
import random
from collections import Counter, defaultdict

from .geo import PROJ, Polyline
from .graph import StopIndex, TransitGraph
from .metrics import find_detours, near_duplicates
from .model import Network, Pattern
from .scenarios import balance_stops
from .service import run_time_s


# ---------------------------------------------------------------- plans

def patterns_by_route(network):
    out = defaultdict(list)
    for key in sorted(network.patterns):
        out[key[0]].append(network.patterns[key])
    return out


class Plan:
    """A network plus the buses assigned to each route; headways follow from the two."""

    def __init__(self, network, fleet):
        self.network = network
        self.by_route = patterns_by_route(network)
        self.fleet = {r: f for r, f in fleet.items() if f > 0 and r in self.by_route}

    @classmethod
    def from_headways(cls, network, a, headways):
        blank = cls(network, {})
        return cls(network, {rid: blank.cycle_min(rid, a) / h for rid, (h, _) in headways.items() if rid in blank.by_route})

    def cycle_min(self, rid, a):
        """Minutes for one bus to go out and back, including layover."""
        pats = self.by_route[rid]
        return sum(run_time_s(p, self.network, a) for p in pats) * (2 / len(pats)) / 60 * (1 + a.layover_share)

    def headways(self, a):
        return {rid: (max(a.min_headway_min, self.cycle_min(rid, a) / buses), "plan") for rid, buses in self.fleet.items()}

    def total_fleet(self):
        return sum(self.fleet.values())

    def stops_of(self, rid):
        return {s for p in self.by_route.get(rid, ()) for s in p.stop_ids}

    def changed(self, patterns=None, drop=(), fleet=None):
        """A new plan with some patterns replaced, some routes dropped and/or another fleet."""
        pats = dict(self.network.patterns)
        if patterns:
            pats.update(patterns)
        for rid in drop:
            for key in [k for k in pats if k[0] == rid]:
                del pats[key]
        f = dict(self.fleet if fleet is None else fleet)
        for rid in drop:
            f.pop(rid, None)
        return Plan(Network(self.network.routes, self.network.stops, pats, self.network.repairs), f)


def allocate(plan, fleet, amount, weights, a):
    """Add `amount` buses to routes in proportion to weights, never beyond min_headway_min.

    Returns what could not be placed."""
    weights = {r: w for r, w in weights.items() if w > 0}
    while amount > 1e-9 and weights:
        total = sum(weights.values())
        placed, full = 0.0, []
        for r, w in sorted(weights.items()):
            room = plan.cycle_min(r, a) / a.min_headway_min - fleet[r]
            give = min(amount * w / total, max(0.0, room))
            fleet[r] += give
            placed += give
            if give >= room - 1e-9:
                full.append(r)
        amount -= placed
        for r in full:
            weights.pop(r)
        if placed <= 1e-9:
            break
    return amount


# ---------------------------------------------------------------- scoring

class Evaluator:
    """Repeatable scoring: the same origins, destinations and access walks every time.

    zones are (lat, lon, people); trips start at origins sampled by population and end at
    every zone in proportion to attraction x exp(-distance / trip_decay_km). The lightest
    destinations are dropped once keep_weight of each origin's trips is covered.
    coverage_zones, finer if given, count the people who still have a stop within reach."""

    def __init__(self, network, a, zones, attraction=None, coverage_zones=None,
                 n_origins=100, seed=11, keep_weight=0.995):
        self.a = a
        index = StopIndex([network.stops[s] for s in sorted(network.served_stop_ids())])
        walk = a.walk_detour / a.walk_speed_mps
        self.access = [[(s.id, d * walk) for d, s in index.within(lat, lon, a.max_access_walk_m)] for lat, lon, _ in zones]
        cz = coverage_zones or zones
        self.cover = [(z[2], [s.id for _, s in index.within(z[0], z[1], a.max_access_walk_m)]) for z in cz]
        xy = [PROJ.to_xy(lat, lon) for lat, lon, _ in zones]
        pull = attraction or [z[2] for z in zones]
        rng = random.Random(seed)
        keyed = sorted(((rng.random() ** (1.0 / z[2]), i) for i, z in enumerate(zones) if z[2] > 0), reverse=True)
        self.origins = [i for _, i in keyed[:n_origins]]
        self.dests = []
        for o in self.origins:
            ox, oy = xy[o]
            cand = []
            for d, (x, y) in enumerate(xy):
                if d != o and pull[d] > 0:
                    dm = math.hypot(x - ox, y - oy)
                    cand.append((pull[d] * math.exp(-dm / (a.trip_decay_km * 1000)), d, dm))
            cand.sort(reverse=True)
            total = sum(w for w, _, _ in cand)
            kept, acc = [], 0.0
            for w, d, dm in cand:
                kept.append((d, w / total, dm * walk if dm <= 2000 else math.inf))
                acc += w / total
                if acc >= keep_weight:
                    break
            norm = sum(w for _, w, _ in kept)
            self.dests.append([(d, w / norm, wk) for d, w, wk in kept])

    def people_with_stop(self, plan):
        served = plan.network.served_stop_ids()
        return sum(pop for pop, stops in self.cover if any(s in served for s in stops))

    def score(self, plan, boardings=False):
        """Average door-to-door minutes (capped at max_trip_min) and supporting figures."""
        a = self.a
        graph = TransitGraph(plan.network, a, plan.headways(a))
        si = graph.stop_index
        cap = a.max_trip_min * 60
        penalty = a.transfer_penalty_s
        tot = Counter()
        rides = Counter()
        for o, dests in zip(self.origins, self.dests):
            sources = {}
            for s, w in self.access[o]:
                if s in si:
                    node = graph.departure(s)
                    sources[node] = min(w, sources.get(node, math.inf))
            dist = boards = pred = settled = None
            if sources:
                dist, boards, pred, settled = graph.search(sources, cap)
            flow = {}
            for d, w, walk_s in dests:
                best, nb, end = walk_s, 0, None
                if dist is not None:
                    for s, e in self.access[d]:
                        i = si.get(s)
                        if i is not None:
                            c = dist[i] + e - penalty
                            if c < best:
                                best, nb, end = c, boards[i], i
                tot["time"] += w * min(best, cap)
                if best > cap:
                    tot["unreachable"] += w
                else:
                    tot["within_45"] += w * (best <= 2700)
                    tot["changes_2plus"] += w * (nb >= 3)
                    if boardings and end is not None:
                        flow[end] = flow.get(end, 0.0) + w
            if boardings and flow and settled:
                for n in reversed(settled):
                    f = flow.get(n)
                    if not f or pred[n] < 0:
                        continue
                    p = pred[n]
                    flow[p] = flow.get(p, 0.0) + f
                    if graph.node_route[n] >= 0 and graph.is_departure(p):
                        rides[graph.node_route[n]] += f
        n = len(self.origins)
        out = {"minutes": tot["time"] / n / 60, "unreachable": tot["unreachable"] / n,
               "within_45": tot["within_45"] / n, "changes_2plus": tot["changes_2plus"] / n}
        if boardings:
            out["boardings"] = dict(rides)
        return out


# ---------------------------------------------------------------- streets for straightening

class Streets:
    """Directed graph of the stop-to-stop links buses drive today.

    Each link remembers the route direction it came from, so a new path can be drawn
    along real streets. Stops less than link_m apart are joined both ways, which lets a
    path pass between routes that use different stop poles at one junction."""

    def __init__(self, network, link_m=60.0):
        self.network = network
        self.adj = defaultdict(dict)
        for key in sorted(network.patterns):
            p = network.patterns[key]
            ch = p.chainage_m
            for i, (x, y, d) in enumerate(p.hops()):
                if x != y and d < self.adj[x].get(y, (math.inf, None))[0]:
                    self.adj[x][y] = (d, (key, ch[i], ch[i + 1]))
        served = [network.stops[s] for s in sorted(network.served_stop_ids())]
        index = StopIndex(served)
        for s in served:
            for d, t in index.within(s.lat, s.lon, link_m):
                if t.id != s.id and d < self.adj[s.id].get(t.id, (math.inf, None))[0]:
                    self.adj[s.id][t.id] = (d, None)
        self._lines = {}

    def path(self, src, dst, limit_m):
        """[(stop, metres from the previous stop, source link)] from src to dst, or None."""
        dist, prev, heap = {src: 0.0}, {}, [(0.0, src)]
        while heap:
            c, u = heapq.heappop(heap)
            if u == dst:
                break
            if c > dist.get(u, math.inf) or c > limit_m:
                continue
            for v, (w, link) in sorted(self.adj[u].items()):
                if c + w < dist.get(v, math.inf):
                    dist[v] = c + w
                    prev[v] = (u, w, link)
                    heapq.heappush(heap, (c + w, v))
        if dst not in prev or dist[dst] > limit_m:
            return None
        out, v = [], dst
        while v != src:
            u, w, link = prev[v]
            out.append((v, w, link))
            v = u
        out.append((src, 0.0, None))
        return out[::-1]

    def line(self, key):
        if key not in self._lines:
            self._lines[key] = Polyline(self.network.patterns[key].path)
        return self._lines[key]

    def geometry(self, path):
        stops = self.network.stops
        pts = []
        for k in range(1, len(path)):
            s, _, link = path[k]
            if link is None:
                a, b = stops[path[k - 1][0]], stops[s]
                seg = [(a.lat, a.lon), (b.lat, b.lon)]
            else:
                key, c0, c1 = link
                seg = self.line(key).slice_latlon(c0, c1)
            pts += seg if not pts else seg[1:]
        return pts


def _join(*parts):
    out = []
    for part in parts:
        for pt in part:
            if not out or pt != out[-1]:
                out.append(pt)
    return out


def straightened(pattern, i, j, path, streets):
    """The pattern with stops i..j replaced by a street path; connector hops merge stop poles."""
    stops, ch = pattern.stop_ids, pattern.chainage_m
    seg_stops, seg_hops = [path[0][0]], []
    for s, h, link in path[1:]:
        if link is None and len(seg_stops) > 1:
            seg_stops[-1] = s                    # two poles at one junction: stop once, at the later
            seg_hops[-1] += h
        else:
            seg_stops.append(s)
            seg_hops.append(h)
    new_stops = list(stops[:i]) + seg_stops + list(stops[j + 1:])
    hops = [ch[k + 1] - ch[k] for k in range(i)] + seg_hops + [ch[k + 1] - ch[k] for k in range(j, len(stops) - 1)]
    chain = [0.0]
    for h in hops:
        chain.append(chain[-1] + h)
    line = Polyline(pattern.path) if len(pattern.path) > 1 else None
    if line:
        geom = _join(line.slice_latlon(0, ch[i]), streets.geometry(path), line.slice_latlon(ch[j], ch[-1]))
    else:
        geom = _join(pattern.path[:1], streets.geometry(path), pattern.path[-1:])
    return Pattern(pattern.route_id, pattern.direction, new_stops, chain, geom, pattern.path_source)


# ---------------------------------------------------------------- changes

class Drop:
    """Drop a route and hand its buses to the routes it overlaps (for a merge, the target first)."""

    def __init__(self, rid, kind, reason, target=None):
        self.rid, self.kind, self.reason, self.target = rid, kind, reason, target
        self.routes = [rid]
        self.receivers = []

    def apply(self, plan, ctx):
        if self.rid not in plan.fleet or len(plan.fleet) < 2:
            return None
        if self.target is not None and self.target not in plan.fleet:
            return None                          # merging into a route that is gone would just drop it
        mine = plan.stops_of(self.rid)
        shared = sorted(((len(mine & plan.stops_of(r)), r) for r in plan.fleet if r != self.rid), reverse=True)
        receivers = [(n, r) for n, r in shared if n > 0][:3]
        fleet = dict(plan.fleet)
        buses = fleet.pop(self.rid)
        weights = {r: n for n, r in receivers} if receivers else dict(fleet)
        left = allocate(plan, fleet, buses, weights, ctx.a)
        if left > 1e-6:                          # receivers are full: spread the rest network-wide
            allocate(plan, fleet, left, {r: f for r, f in fleet.items() if r not in weights}, ctx.a)
        self.receivers = [r for _, r in receivers]
        return plan.changed(drop=[self.rid], fleet=fleet)

    def describe(self, net):
        to = ", ".join(net.number(r) for r in self.receivers) or "the whole network"
        return f"{self.reason}; its buses go to {to}"


class Straighten:
    kind = "straighten"

    def __init__(self, key, i, j, path, along_m, new_m, original, inner):
        self.key, self.i, self.j, self.path = key, i, j, path
        self.along_m, self.new_m, self.original, self.inner = along_m, new_m, original, inner
        self.routes = [key[0]]

    def apply(self, plan, ctx):
        p = plan.network.patterns.get(self.key)
        if p is None or p.stop_ids != self.original:
            return None
        return plan.changed(patterns={self.key: straightened(p, self.i, self.j, self.path, ctx.streets)})

    def describe(self, net):
        st = net.stops
        a, b = st[self.original[self.i]].name, st[self.original[self.j]].name
        kept = {s for s, _, _ in self.path}
        left = sum(1 for s in self.inner if s not in kept)
        return (f"Straighten {net.number(self.key[0])} direction {self.key[1]} between {a} and {b}: "
                f"{(self.along_m - self.new_m) / 1000:.1f} km shorter, {left} of its stops dropped")


class BalanceStops:
    """Stop balancing that never takes away anyone's last stop within walking reach.

    After each pass, a removed stop is kept after all if some people would have no other
    served stop within max_access_walk_m; the pass then runs again with those stops kept."""
    kind = "stops"
    routes = []

    def __init__(self, min_gap_m):
        self.min_gap_m = min_gap_m
        self.removed = 0

    def apply(self, plan, ctx):
        before = plan.network.served_stop_ids()
        protect = set()
        for _ in range(10):
            new, details = balance_stops(plan.network, self.min_gap_m, 700, protect)
            removed = set(details["removed_stops"])
            after = before - removed
            stranding = {s for _, stops in ctx.evaluator.cover
                         if stops and any(s in before for s in stops) and not any(s in after for s in stops)
                         for s in stops if s in removed}
            if not stranding:
                break
            protect |= stranding
        self.removed = len(removed)
        return Plan(new, plan.fleet) if self.removed else None

    def describe(self, net):
        return (f"Remove {self.removed} stops closer than {self.min_gap_m:.0f} m to a neighbour on every route "
                f"that uses them, keeping any stop that is someone's only one within reach")


class Shift:
    """Move buses from the routes with the fewest modelled riders per bus to those with the most.

    No donor drops below the buses it needs to run every max_headway_min."""
    kind = "shift"

    def __init__(self, k, share):
        self.k, self.share = k, share
        self.routes, self.moved = [], 0.0

    def apply(self, plan, ctx):
        a, rides = ctx.a, ctx.boardings
        per_bus = sorted((rides.get(r, 0.0) / plan.fleet[r], r) for r in plan.fleet)
        if len(per_bus) < 2 * self.k:
            return None
        donors = [r for _, r in per_bus[:self.k]]
        takers = [r for _, r in per_bus[-self.k:]]
        fleet = dict(plan.fleet)
        moved = 0.0
        for r in donors:
            floor = plan.cycle_min(r, a) / a.max_headway_min
            give = max(0.0, min(fleet[r] * self.share, fleet[r] - floor))
            fleet[r] -= give
            moved += give
        left = allocate(plan, fleet, moved, {r: rides.get(r, 0.0) for r in takers}, a)
        for r in donors:                         # anything the takers cannot use goes back
            fleet[r] += left / len(donors)
        moved -= left
        if moved < 0.5:
            return None
        self.moved, self.donors, self.takers = moved, donors, takers
        return plan.changed(fleet=fleet)

    def describe(self, net):
        return (f"Move {self.moved:.0f} buses from the {self.k} routes with the fewest riders per bus "
                f"({', '.join(net.number(r) for r in self.donors)}) to the {self.k} with the most "
                f"({', '.join(net.number(r) for r in self.takers)})")


# ---------------------------------------------------------------- candidates and search

class Context:
    def __init__(self, network, a, evaluator):
        self.a = a
        self.evaluator = evaluator
        self.streets = Streets(network)
        self.boardings = {}


def candidates(plan, ctx, base_score):
    """Changes worth trying on today's network, from the inefficiency measures."""
    a, net = ctx.a, plan.network
    out, seen = [], set()
    number_to_id = {r.number: k for k, r in net.routes.items()}
    for d in near_duplicates(net):                         # sorted by share: first match is the closest
        a_id, b_id = number_to_id[d["route"]], number_to_id[d["inside_route"]]
        if a_id in seen or a_id not in plan.fleet:
            continue
        seen.add(a_id)
        out.append(Drop(a_id, "merge", f"Merge {d['route']} into {d['inside_route']}: "
                                       f"{d['share_of_stops']:.0%} of its stops are also on {d['inside_route']}", b_id))
    rides = base_score.get("boardings", {})
    per_bus = sorted((rides.get(r, 0.0) / plan.fleet[r], r) for r in plan.fleet)
    for _, rid in per_bus[:a.redesign_max_drop]:
        if rid not in seen:
            out.append(Drop(rid, "drop", f"Drop {net.number(rid)}: few riders per bus in the model"))
    straight = []
    for key in sorted(net.patterns):
        p = net.patterns[key]
        pts = [(net.stops[s].lat, net.stops[s].lon) for s in p.stop_ids]
        for det in find_detours(p, pts):
            i, j = det["from_index"], det["to_index"]
            along = p.chainage_m[j] - p.chainage_m[i]
            path = ctx.streets.path(p.stop_ids[i], p.stop_ids[j], along - 500)
            if not path:
                continue
            new = sum(h for _, h, _ in path)
            speed = a.cruise_mps(net.routes[key[0]].zone)
            saved_s = (along - new) / speed + max(0, (j - i - 1) - (len(path) - 2)) * a.stop_loss_s
            straight.append((saved_s, Straighten(key, i, j, path, along, new, list(p.stop_ids), p.stop_ids[i + 1:j])))
    straight.sort(key=lambda t: (-t[0], t[1].key, t[1].i))
    out += [s for _, s in straight[:a.redesign_max_straighten]]
    return out


def search(plan, evaluator, ctx, say=print):
    """Improve the plan step by step. Returns (plan, changes, score before, score after, people check)."""
    a = ctx.a
    start = evaluator.score(plan, boardings=True)
    ctx.boardings = start["boardings"]
    people0 = evaluator.people_with_stop(plan)
    current, cur, people = plan, start["minutes"], people0
    say(f"  today: {cur:.2f} min average door-to-door on the search sample; {people0:,.0f} people with a stop within reach")
    log = []

    def check(new_plan):
        """Score a candidate if it keeps enough people within reach of a stop, else None."""
        new_people = evaluator.people_with_stop(new_plan)
        if people - new_people > a.redesign_max_people_losing_stop or people0 - new_people > a.redesign_max_people_losing_stop_total:
            return None, new_people
        return evaluator.score(new_plan), new_people

    def accept(change, new_plan, score, new_people):
        nonlocal current, cur, people
        log.append({"step": len(log) + 1, "kind": change.kind,
                    "routes": " ".join(plan.network.number(r) for r in change.routes),
                    "change": change.describe(plan.network),
                    "minutes_before": cur, "minutes_after": score["minutes"], "gain_min": cur - score["minutes"],
                    "people_losing_stop": people - new_people})
        say(f"  + {log[-1]['change']}  ({cur:.2f} -> {score['minutes']:.2f} min)")
        current, cur, people = new_plan, score["minutes"], new_people

    # 1. screen each structural change alone, then apply the winners in order of gain
    cands = candidates(plan, ctx, start)
    say(f"  screening {len(cands)} candidate changes")
    screened, blocked = [], 0
    for c in cands:
        p = c.apply(plan, ctx)
        if p is None:
            continue
        s, _ = check(p)
        if s is None:
            blocked += 1
        elif cur - s["minutes"] > a.redesign_min_gain_min:
            screened.append((cur - s["minutes"], c))
    screened.sort(key=lambda t: -t[0])
    say(f"  {len(screened)} improve on their own; {blocked} rejected for cutting people off; applying in order of gain")
    for _, c in screened:
        p = c.apply(current, ctx)
        if p is None:
            continue
        s, new_people = check(p)
        if s is not None and s["minutes"] < cur - a.redesign_min_gain_min:
            accept(c, p, s, new_people)

    # 2. stop balancing on the result
    for gap in (250, 300):
        c = BalanceStops(gap)
        p = c.apply(current, ctx)
        if p is not None:
            s, new_people = check(p)
            if s is not None and s["minutes"] < cur - a.redesign_min_gain_min:
                accept(c, p, s, new_people)
                break

    # 3. move buses towards the routes that carry the most riders
    for _ in range(a.redesign_shift_rounds):
        ctx.boardings = evaluator.score(current, boardings=True)["boardings"]
        best = None
        for k in (5, 10, 20):
            c = Shift(k, a.redesign_shift_share)
            p = c.apply(current, ctx)
            if p is not None:
                s, new_people = check(p)
                if s is not None and s["minutes"] < cur - a.redesign_min_gain_min and (best is None or s["minutes"] < best[2]["minutes"]):
                    best = (c, p, s, new_people)
        if not best:
            break
        accept(*best)
    return current, log, start, evaluator.score(current)


def fleet_for_same_time(plan, evaluator, target_minutes, lo=0.5, steps=8):
    """Smallest share of the plan's fleet (scaled evenly) that keeps door-to-door time at target."""
    if evaluator.score(plan)["minutes"] > target_minutes:
        return 1.0
    hi = 1.0
    for _ in range(steps):
        mid = (lo + hi) / 2
        scaled = plan.changed(fleet={r: f * mid for r, f in plan.fleet.items()})
        if evaluator.score(scaled)["minutes"] <= target_minutes:
            hi = mid
        else:
            lo = mid
    return hi
