"""Walking distance along streets and paths, from OpenStreetMap.

Coverage in metrics.py is straight-line distance to a stop. That is a proxy: rail
lines, motorways and the bay break walking routes, so the walk to a stop is longer
than the line. This module measures the walk along OpenStreetMap's ways instead, so
the size of that error can be reported.

A WalkNetwork is built from an Overpass answer holding every highway in the study area
(ways with their tags and node references, then the nodes) and keeps the ways a
pedestrian may use. A point off the network joins it at the nearest point of the
nearest way, walking the gap in a straight line. The distance from many points to the
nearest of a set of stops is one multi-source Dijkstra run from the stops, so the whole
study area takes seconds.

Standard library only."""

import gzip
import heapq
import json
import math
from array import array
from collections import defaultdict

from .geo import PROJ, haversine_m

# Ways a pedestrian may not use, after OSMnx's "walk" network type: motorways and their
# links, busways, raceways, platforms, cycleways (unless foot is allowed) and ways that
# are planned, under construction or gone. Every other highway can be walked unless its
# tags say foot=no, access=private or access=no (without foot allowed), or service=private.
NOT_WALKABLE = frozenset(("abandoned", "bus_guideway", "busway", "construction", "cycleway", "motorway",
                          "motorway_link", "motorway_junction", "planned", "platform", "proposed", "raceway", "razed"))
FOOT_ALLOWED = frozenset(("yes", "designated", "permissive", "official"))


def walkable(tags):
    """True when the tags of a way describe something a pedestrian may walk along."""
    highway = tags.get("highway")
    if not highway or tags.get("area") == "yes":
        return False
    foot = tags.get("foot")
    if foot in FOOT_ALLOWED:
        return highway not in ("motorway", "motorway_link", "motorway_junction")
    if highway in NOT_WALKABLE or foot in ("no", "private", "use_sidepath"):
        return False
    if tags.get("access") in ("no", "private") or tags.get("service") == "private":
        return False
    return True


def load_overpass(path):
    """(nodes, ways, info) from an Overpass JSON answer (gzipped when the name ends in .gz):
    nodes {id: (lat, lon)}, the node lists of the walkable ways, and counts and the data date."""
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        answer = json.load(f)
    nodes, ways, total = {}, [], 0
    for e in answer.get("elements", ()):
        if e["type"] == "node":
            nodes[e["id"]] = (e["lat"], e["lon"])
        elif e["type"] == "way":
            total += 1
            if walkable(e.get("tags", {})):
                ways.append(e["nodes"])
    info = {"osm_date": answer.get("osm3s", {}).get("timestamp_osm_base"), "ways": total, "ways_walkable": len(ways)}
    return nodes, ways, info


class WalkNetwork:
    """Streets and paths as an undirected graph with metre lengths, and a grid index of
    its segments for joining points to it."""

    CELL = 200.0           # metres; segments are registered in every cell their box touches

    def __init__(self, nodes, ways):
        """nodes: {osm id: (lat, lon)}; ways: lists of node ids in order, walkable ones only."""
        index = {}
        xs, ys, lats, lons = array("d"), array("d"), array("d"), array("d")
        eu, ev, length = array("i"), array("i"), array("d")
        seen = set()
        for way in ways:
            prev = None
            for nid in way:
                if nid not in nodes:
                    prev = None                                   # a node outside the answer
                    continue
                k = index.get(nid)
                if k is None:
                    k = index[nid] = len(xs)
                    lat, lon = nodes[nid]
                    x, y = PROJ.to_xy(lat, lon)
                    xs.append(x), ys.append(y), lats.append(lat), lons.append(lon)
                if prev is not None and prev != k and (min(prev, k), max(prev, k)) not in seen:
                    seen.add((min(prev, k), max(prev, k)))
                    eu.append(prev), ev.append(k)
                    length.append(haversine_m(lats[prev], lons[prev], lats[k], lons[k]))
                prev = k
        self.n, self.xs, self.ys, self.lats, self.lons = len(xs), xs, ys, lats, lons
        self.eu, self.ev, self.length = eu, ev, length
        # Adjacency in compressed form: the neighbours of node i are nbr[off[i]:off[i + 1]].
        degree = array("i", bytes(4 * (self.n + 1)))
        for e in range(len(eu)):
            degree[eu[e] + 1] += 1
            degree[ev[e] + 1] += 1
        for i in range(1, self.n + 1):
            degree[i] += degree[i - 1]
        self.off = degree
        fill = array("i", degree)
        self.nbr, self.wgt = array("i", bytes(4 * degree[self.n])), array("d", bytes(8 * degree[self.n]))
        for e in range(len(eu)):
            u, v, d = eu[e], ev[e], length[e]
            self.nbr[fill[u]], self.wgt[fill[u]] = v, d
            fill[u] += 1
            self.nbr[fill[v]], self.wgt[fill[v]] = u, d
            fill[v] += 1
        self.grid = defaultdict(list)
        c = self.CELL
        for e in range(len(eu)):
            x1, y1, x2, y2 = xs[eu[e]], ys[eu[e]], xs[ev[e]], ys[ev[e]]
            for i in range(int(min(x1, x2) // c), int(max(x1, x2) // c) + 1):
                for j in range(int(min(y1, y2) // c), int(max(y1, y2) // c) + 1):
                    self.grid[(i, j)].append(e)

    @property
    def edges(self):
        return len(self.eu)

    def snap(self, lat, lon, max_m=3000.0):
        """(edge, position along it from 0 to 1, straight-line gap in metres) of the nearest
        point of the network, or None when nothing is within max_m."""
        x, y = PROJ.to_xy(lat, lon)
        c = self.CELL
        reach = c
        while reach <= max_m * 2:
            best = None
            for i in range(int((x - reach) // c), int((x + reach) // c) + 1):
                for j in range(int((y - reach) // c), int((y + reach) // c) + 1):
                    for e in self.grid.get((i, j), ()):
                        u, v = self.eu[e], self.ev[e]
                        ax, ay, bx, by = self.xs[u], self.ys[u], self.xs[v], self.ys[v]
                        dx, dy = bx - ax, by - ay
                        den = dx * dx + dy * dy
                        t = min(1.0, max(0.0, ((x - ax) * dx + (y - ay) * dy) / den)) if den else 0.0
                        d = math.hypot(x - ax - t * dx, y - ay - t * dy)
                        if best is None or d < best[2]:
                            best = (e, t, d)
            # A segment passing within d of the point touches the square of half-side
            # reach when d <= reach, so the best found is then the nearest there is.
            if best is not None and best[2] <= reach:
                return best if best[2] <= max_m else None
            reach *= 2
        return None

    def distances_from(self, sources, cutoff):
        """Walking distance from the nearest of the snapped sources to every node, up to cutoff
        (math.inf beyond it). sources: [(edge, position, gap)] as snap() returns."""
        inf = math.inf
        dist = [inf] * self.n
        heap = []
        for e, t, gap in sources:
            u, v, length = self.eu[e], self.ev[e], self.length[e]
            for node, d in ((u, gap + t * length), (v, gap + (1.0 - t) * length)):
                if d < dist[node]:
                    dist[node] = d
                    heapq.heappush(heap, (d, node))
        nbr, wgt, off = self.nbr, self.wgt, self.off
        while heap:
            d, i = heapq.heappop(heap)
            if d > dist[i]:
                continue
            if d > cutoff:
                break
            for k in range(off[i], off[i + 1]):
                j = nbr[k]
                nd = d + wgt[k]
                if nd < dist[j]:
                    dist[j] = nd
                    heapq.heappush(heap, (nd, j))
        return dist

    def walk_distances(self, points, stops, cutoff=2000.0):
        """Walking distance from each (lat, lon) point to the nearest (lat, lon) stop along
        the network, including the straight-line gaps that join each to it. math.inf when
        it is beyond cutoff or when the point or every stop is off the network."""
        sources = [s for s in (self.snap(lat, lon) for lat, lon in stops) if s is not None]
        on_edge = defaultdict(list)
        for e, t, gap in sources:
            on_edge[e].append((t, gap))
        dist = self.distances_from(sources, cutoff)
        out = []
        for lat, lon in points:
            hit = self.snap(lat, lon)
            if hit is None:
                out.append(math.inf)
                continue
            e, t, gap = hit
            length = self.length[e]
            d = min(dist[self.eu[e]] + t * length, dist[self.ev[e]] + (1.0 - t) * length)
            for ts, gs in on_edge.get(e, ()):                 # a stop on the same segment
                d = min(d, gs + abs(t - ts) * length)
            out.append(gap + d if gap + d <= cutoff else math.inf)
        return out


def load_walk_network(path):
    """A WalkNetwork from an Overpass answer, with the counts and data date it was built from."""
    nodes, ways, info = load_overpass(path)
    net = WalkNetwork(nodes, ways)
    info.update({"nodes": net.n, "edges": net.edges})
    return net, info
