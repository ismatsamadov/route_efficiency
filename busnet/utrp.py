"""The benchmark networks of the urban transit routing problem: Mandl's and Mumford's four.

Mumford (2013) published four made-up networks, Mumford0 to Mumford3, beside Mandl's
Swiss network, with the best route sets her evolutionary algorithm found and their
scores. Her supplement (data/external/utrp/CEC2013Supp.zip) holds the networks, the route
sets and the scores. Two later studies publish their best route sets too: Hüsselmann,
van Vuuren and Andersen (2024), whose results repository holds the sets behind their
Tables 9 and 10 (data/external/utrp/husselmann2024/), and Jiao (2026), whose archive
holds the sets with the lowest average travel times reported so far
(data/external/utrp/jiao2026/). This module reads all of them, scores a route set the way
that literature does, and runs the redesign's straightening on a published route set under
the benchmark's rules (benchmark.py).

A route set is scored on the network's link times, with every route ridden both ways. Each
trip takes its quickest path, where every change of route costs PENALTY_MIN minutes; of
equally quick paths, the one with fewer changes counts:
  att          average travel time of all trips, weighted by demand, in minutes
  d0, d1, d2   the share of demand whose path has 0, 1 or 2 changes, in %
  dun          the share that needs 3 or more changes, in %
  route_time   the minutes it takes to drive every route once one way (the operator's cost)

The rules (Mumford 2013, Table II): exactly the published number of routes; every route a
path along the network's links that visits no node twice and has between the minimum and
the maximum number of nodes; every node on some route; and every node reachable from every
other. Stops cannot be removed, since that would make another network, and there are no
frequencies to change."""

import heapq
import io
import json
import math
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

PENALTY_MIN = 5.0
RULES = {                        # routes, fewest and most nodes on a route (Mumford 2013, Table II)
    "Mandl": (6, 2, 8),
    "Mumford0": (12, 2, 15),
    "Mumford1": (15, 10, 30),
    "Mumford2": (56, 10, 22),
    "Mumford3": (60, 12, 25),
}
ROUTE_SETS = "Results/MainResults/Best Route Sets.docx"
SCORES = "Results/MainResults/README.docx"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass
class Instance:
    name: str
    time: list            # minutes along each link, n x n; math.inf where there is no link
    demand: list          # trips from each node to each node, n x n
    routes: int
    min_nodes: int
    max_nodes: int

    @property
    def n(self):
        return len(self.time)


def _matrix(text):
    return [[math.inf if v.lower() == "inf" else float(v) for v in line.split()]
            for line in text.splitlines() if line.split()]


def load_instance(supplement, name):
    with zipfile.ZipFile(supplement) as z:
        time = _matrix(z.read(f"Instances/{name}TravelTimes.txt").decode("ascii"))
        demand = _matrix(z.read(f"Instances/{name}Demand.txt").decode("ascii"))
    return Instance(name, time, demand, *RULES[name])


def _document(supplement, path):
    """The body of a Word file inside the supplement."""
    with zipfile.ZipFile(supplement) as z:
        inner = zipfile.ZipFile(io.BytesIO(z.read(path)))
    return ET.fromstring(inner.read("word/document.xml"))


def _text(element):
    return "".join(t.text or "" for t in element.iter(W + "t")).strip()


def published_route_sets(supplement):
    """{(network, "passenger" or "operator"): routes}, nodes numbered from 0.

    The file lists, for each network, the route set best for passengers and the one best
    for the operator, as Matlab lines such as  routeset(1).route = [5 4 12 11 10 8 15 9];"""
    sets, key = {}, None
    for p in _document(supplement, ROUTE_SETS).iter(W + "p"):
        text = _text(p)
        m = re.match(r"%\s*Best\s+(?:rout\w*\s+)?for\s+(passenger|operator)s?\s+(Mandl|Mumford\d)", text, re.I)
        if m:
            key = (m.group(2), m.group(1).lower())
            sets[key] = []
            continue
        m = re.match(r"routeset\(\d+\)\.route\s*=\s*\[([^\]]*)\]", text)
        if m and key:
            sets[key].append([int(v) - 1 for v in m.group(1).split()])
    return sets


def published_scores(supplement):
    """Table IV of Mumford (2013), from the supplement's README: {(network, who): {measure: value}}.

    The table gives lower bounds in brackets after some values; they are left out."""
    table = next(_document(supplement, SCORES).iter(W + "tbl"))
    rows = [[_text(c) for c in r.findall(W + "tc")] for r in table.iter(W + "tr")]
    names = [c for c in rows[0] if c]
    measure = {"cp": "att", "co": "route_time", "d0": "d0", "d1": "d1", "d2": "d2", "dun": "dun"}
    out = {}
    for start in range(1, len(rows), 6):           # six rows for passengers, then six for the operator
        block = rows[start:start + 6]
        who = "passenger" if "passenger" in " ".join(r[0] for r in block).lower() else "operator"
        for r in block:
            for name, cell in zip(names, r[2:]):
                out.setdefault((name, who), {})[measure[r[1].lower()]] = float(re.match(r"[\d.]+", cell).group())
    return out


# The route sets later studies published, under data/external/utrp/. Each file of
# Hüsselmann et al. (2024) is the "Extreme solutions.txt" of one run of their results
# repository (the original path is in husselmann2024/ORIGINAL_PATHS.txt): the two ends of
# the run's Pareto set, best for the operator and best for passengers, with the scores
# their own code gave them. The file named for each network and method holds the sets
# behind their Tables 9 and 10; for NSGA-II on Mumford3 the two ends come from different
# runs, so two files are listed, each for one end.
LATER_SETS = (
    # source, method, network, file, which of its two ends are the published ones
    ("Hüsselmann et al. (2024)", "DBMOSA", "Mandl", "husselmann2024/Results_34_1_Mandl6_SA_Long_run.txt", ("passenger", "operator")),
    ("Hüsselmann et al. (2024)", "NSGA-II", "Mandl", "husselmann2024/Results_1_1_Mandl6_GA_Initial_solutions.txt", ("passenger", "operator")),
    ("Hüsselmann et al. (2024)", "DBMOSA", "Mumford0", "husselmann2024/Results_34_2_Mumford0_SA_Long_run.txt", ("passenger", "operator")),
    ("Hüsselmann et al. (2024)", "NSGA-II", "Mumford0", "husselmann2024/Results_10_2_Mumford0_GA_Long_run.txt", ("passenger", "operator")),
    ("Hüsselmann et al. (2024)", "DBMOSA", "Mumford1", "husselmann2024/Results_34_3_Mumford1_SA_Long_run.txt", ("passenger", "operator")),
    ("Hüsselmann et al. (2024)", "NSGA-II", "Mumford1", "husselmann2024/Results_10_3_Mumford1_GA_Long_run.txt", ("passenger", "operator")),
    ("Hüsselmann et al. (2024)", "DBMOSA", "Mumford2", "husselmann2024/Results_34_4_Mumford2_SA_Long_run.txt", ("passenger", "operator")),
    ("Hüsselmann et al. (2024)", "NSGA-II", "Mumford2", "husselmann2024/Results_11_4_Mumford2_GA_Very_Long_run.txt", ("passenger", "operator")),
    ("Hüsselmann et al. (2024)", "DBMOSA", "Mumford3", "husselmann2024/Results_34_5_Mumford3_SA_Long_run.txt", ("passenger", "operator")),
    ("Hüsselmann et al. (2024)", "NSGA-II", "Mumford3", "husselmann2024/Results_11_5_Mumford3_GA_Very_Long_run.txt", ("passenger",)),
    ("Hüsselmann et al. (2024)", "NSGA-II", "Mumford3", "husselmann2024/Results_10_5_Mumford3_GA_Long_run.txt", ("operator",)),
)
JIAO_FILE = "jiao2026/best_networks.json"
# The scores Jiao (2026) reports for those sets beside their ATT: route time from the
# archive's solutions.csv and the Mandl search log (the preprint prints no operator cost),
# d0 and d1 from the preprint's Table 6; every set has d2 = dun = 0.
JIAO_SCORES = {
    "Mandl": {"route_time": 212, "d0": 97.17, "d1": 2.83, "d2": 0.0, "dun": 0.0},
    "Mumford0": {"route_time": 747, "d0": 92.55, "d1": 7.45, "d2": 0.0, "dun": 0.0},
    "Mumford1": {"route_time": 1976, "d0": 72.49, "d1": 27.51, "d2": 0.0, "dun": 0.0},
    "Mumford2": {"route_time": 5493, "d0": 75.29, "d1": 24.71, "d2": 0.0, "dun": 0.0},
    "Mumford3": {"route_time": 6652, "d0": 70.71, "d1": 29.29, "d2": 0.0, "dun": 0.0},
}


def husselmann_route_sets(path):
    """The two route sets in one "Extreme solutions.txt" of Hüsselmann et al. (2024):
    {"passenger": routes, "operator": routes, "scores": {who: {measure: value}}}, nodes
    numbered from 0 as in the file.

    The file gives a table of f1_ATT, f2_TRT, d_0, d_1, d_2 and d_un with an Operator and
    a Passenger column, then each route set as a Python-style list of lists."""
    text = Path(path).read_text(encoding="utf-8")
    measure = {"f1_ATT": "att", "f2_TRT": "route_time", "d_0": "d0", "d_1": "d1", "d_2": "d2", "d_un": "dun"}
    scores = {"operator": {}, "passenger": {}}
    for m in re.finditer(r"^(f1_ATT|f2_TRT|d_0|d_1|d_2|d_un)\t([\d.]+)\t+([\d.]+)", text, re.M):
        scores["operator"][measure[m.group(1)]] = float(m.group(2))
        scores["passenger"][measure[m.group(1)]] = float(m.group(3))
    out = {"scores": scores}
    for who in ("operator", "passenger"):
        block = re.search(rf"Best {who.capitalize()} Route set:\s*\\?\s*(\[\[.*?\]\])", text, re.S).group(1)
        out[who] = [[int(v) for v in r.split(",")] for r in re.findall(r"\[([\d,\s]+)\]", block)]
    return out


def jiao_route_sets(path):
    """{network: (routes, att)} from best_networks.json of Jiao (2026): for each network
    the set with the benchmark's number of routes (the file also holds Mandl sets with
    other counts), nodes numbered from 0 (the file numbers them from 1) and the average
    travel time the author's evaluator gives it."""
    names = {"mandl": "Mandl", "mumford0": "Mumford0", "mumford1": "Mumford1", "mumford2": "Mumford2", "mumford3": "Mumford3"}
    out = {}
    for entry in json.loads(Path(path).read_text(encoding="utf-8")):
        name = names[entry["instance"]]
        if entry["S"] == RULES[name][0]:
            out[name] = ([[v - 1 for v in r] for r in entry["routes"]], float(entry["ATT"]))
    return out


# ---------------------------------------------------------------- scoring

def route_time(inst, routes):
    return sum(inst.time[a][b] for r in routes for a, b in zip(r, r[1:]))


def evaluate(inst, routes, penalty=PENALTY_MIN):
    """att, d0, d1, d2, dun and route_time of a route set, or None if some trip has no path.

    Dijkstra from every origin over a graph with one node per route and stop on it, and a
    transfer node per stop that costs the penalty to reach and nothing to leave."""
    at = [[] for _ in range(inst.n)]
    adj = []
    for r in routes:
        base = len(adj)
        for k, v in enumerate(r):
            at[v].append(base + k)
            adj.append([])
        for k in range(len(r) - 1):
            w = inst.time[r[k]][r[k + 1]]
            adj[base + k].append((base + k + 1, w, 0))
            adj[base + k + 1].append((base + k, w, 0))
    hub = len(adj)
    for v in range(inst.n):
        adj.append([(x, 0.0, 0) for x in at[v]])
        for x in at[v]:
            adj[x].append((hub + v, penalty, 1))
    total = att = 0.0
    changes = [0.0] * 4
    for i in range(inst.n):
        row = inst.demand[i]
        if not any(row[j] for j in range(inst.n) if j != i):
            continue
        best = [(math.inf, math.inf)] * len(adj)
        heap = []
        for x in at[i]:
            best[x] = (0.0, 0)
            heap.append((0.0, 0, x))
        heapq.heapify(heap)
        while heap:
            c, t, u = heapq.heappop(heap)
            if (c, t) > best[u]:
                continue
            for v, w, change in adj[u]:
                d = (c + w, t + change)
                if d < best[v]:
                    best[v] = d
                    heapq.heappush(heap, (d[0], d[1], v))
        for j in range(inst.n):
            q = row[j]
            if j == i or not q:
                continue
            c, t = min((best[x] for x in at[j]), default=(math.inf, math.inf))
            if c == math.inf:
                return None
            total += q
            att += q * c
            changes[min(t, 3)] += q
    share = [100 * x / total for x in changes]
    return {"att": att / total, "d0": share[0], "d1": share[1], "d2": share[2], "dun": share[3],
            "route_time": route_time(inst, routes)}


def problems(inst, routes):
    """The rules a route set breaks, in words; an empty list if it keeps them all."""
    out = []
    if len(routes) != inst.routes:
        out.append(f"{len(routes)} routes instead of {inst.routes}")
    for k, r in enumerate(routes, 1):
        if not inst.min_nodes <= len(r) <= inst.max_nodes:
            out.append(f"route {k} has {len(r)} nodes")
        if len(set(r)) != len(r):
            out.append(f"route {k} visits a node twice")
        if any(inst.time[a][b] == math.inf for a, b in zip(r, r[1:])):
            out.append(f"route {k} leaves the links")
    missing = inst.n - len({v for r in routes for v in r})
    if missing:
        out.append(f"{missing} nodes on no route")
    if not _connected(routes):
        out.append("the routes fall apart into separate networks")
    return out


def _connected(routes):
    """True when every route can be reached from every other by changing at shared nodes."""
    parent = list(range(len(routes)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    first = {}
    for k, r in enumerate(routes):
        for v in r:
            if v in first:
                parent[find(k)] = find(first[v])
            else:
                first[v] = k
    return len({find(k) for k in range(len(routes))}) <= 1


# ---------------------------------------------------------------- straightening

def quickest_paths(inst):
    """(minutes, predecessor) between every pair of nodes along the links, from Dijkstra."""
    adj = [[(j, w) for j, w in enumerate(row) if j != i and w < math.inf] for i, row in enumerate(inst.time)]
    dist, prev = [], []
    for s in range(inst.n):
        d, p, heap = [math.inf] * inst.n, [-1] * inst.n, [(0.0, s)]
        d[s] = 0.0
        while heap:
            c, u = heapq.heappop(heap)
            if c > d[u]:
                continue
            for v, w in adj[u]:
                if c + w < d[v]:
                    d[v], p[v] = c + w, u
                    heapq.heappush(heap, (c + w, v))
        dist.append(d)
        prev.append(p)
    return dist, prev


def _path(prev, a, b):
    out = [b]
    while out[-1] != a:
        out.append(prev[a][out[-1]])
    return out[::-1]


def detours(inst, route, dist):
    """Stretches of a route that take longer than the quickest path between their ends:
    (minutes longer, i, j) for the nodes at positions i and j.

    As in the redesign (metrics.find_detours): at most max(3, min(12, 40% of the route))
    nodes apart, and of overlapping stretches only the one that wastes the most."""
    n = len(route)
    span = max(3, min(12, int(0.4 * n)))
    cands = []
    for i in range(n):
        along = 0.0
        for j in range(i + 1, min(n, i + span + 1)):
            along += inst.time[route[j - 1]][route[j]]
            quick = dist[route[i]][route[j]]
            if j >= i + 2 and quick < along:
                cands.append((along - quick, i, j))
    chosen = []
    for c in sorted(cands, key=lambda c: (-c[0], c[1], c[2])):
        if all(c[2] <= o[1] or c[1] >= o[2] for o in chosen):
            chosen.append(c)
    return sorted(chosen, key=lambda c: c[1])


@dataclass
class Straighten:
    """Replace the nodes of one route between positions i and j by the quickest path."""
    route: int
    i: int
    j: int
    original: list        # the route as it was when the change was found
    new: list             # the route after the change
    saved_min: float      # route time saved

    def apply(self, routes):
        if routes[self.route] != self.original:
            return None                          # the route has changed since: skip, as the redesign does
        return routes[:self.route] + [self.new] + routes[self.route + 1:]


def candidates(inst, routes, dist, prev, max_tries):
    out = []
    for k, r in enumerate(routes):
        for saved, i, j in detours(inst, r, dist):
            out.append(Straighten(k, i, j, r, r[:i] + _path(prev, r[i], r[j]) + r[j + 1:], saved))
    out.sort(key=lambda c: (-c.saved_min, c.route, c.i))
    return out[:max_tries]


def search(inst, routes, max_tries=80, min_gain=0.005, repeat=False):
    """The redesign's straightening on a route set, under the benchmark's rules.

    A pass screens the max_tries detours that save the most route time, each alone, keeps
    those that cut att by more than min_gain without breaking a rule, and applies them in
    order of gain, scoring each again on the routes as they are by then: the screening and
    the order of redesign.py's search. With repeat=True, passes run until one keeps nothing.
    Returns (routes, score before, score after, the changes kept, counts of what was tried)."""
    dist, prev = quickest_paths(inst)
    start = evaluate(inst, routes)
    current, cur = routes, start
    log = []
    tried = {"passes": 0, "candidates": 0, "breaking_a_rule": 0, "better_alone": 0}
    while True:
        tried["passes"] += 1
        screened = []
        for c in candidates(inst, current, dist, prev, max_tries):
            tried["candidates"] += 1
            new = c.apply(current)
            if problems(inst, new):
                tried["breaking_a_rule"] += 1
                continue
            score = evaluate(inst, new)
            if score and cur["att"] - score["att"] > min_gain:
                screened.append((cur["att"] - score["att"], c))
        tried["better_alone"] += len(screened)
        kept = 0
        for _, c in sorted(screened, key=lambda t: (-t[0], t[1].route, t[1].i)):
            new = c.apply(current)
            if new is None or problems(inst, new):
                continue
            score = evaluate(inst, new)
            if score and score["att"] < cur["att"] - min_gain:
                log.append({"pass": tried["passes"], "change": c, "before": cur, "after": score})
                current, cur = new, score
                kept += 1
        if not (repeat and kept):
            return current, start, cur, log, tried


def matlab(routes):
    """A route set in the supplement's own format, nodes numbered from 1."""
    return "\n".join(f"routeset({k}).route = [{' '.join(str(v + 1) for v in r)}];" for k, r in enumerate(routes, 1))
