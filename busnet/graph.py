"""Spatial index for stops, and door-to-door journey search over the bus network.

The search graph has, for every served stop, an arrival node and a departure node,
and for every route direction a chain of on-board nodes:

    departure(stop) --board: wait + transfer penalty--> on-board(pattern, i)
    on-board(pattern, i) --ride: hop time--> on-board(pattern, i + 1)
    on-board(pattern, i) --alight--> arrival(stop)
    arrival(stop) --stay--> departure(stop)
    arrival(stop) --walk up to max_transfer_walk_m--> departure(other stop)

Walking happens once between rides, never chained. Every boarding pays the
transfer penalty; callers subtract one penalty because the first boarding of a
journey is not a transfer."""

import heapq
import math
from collections import defaultdict

from .geo import PROJ, haversine_m


class StopIndex:
    """Find stops near a point quickly, using a square grid."""

    def __init__(self, stops, cell_m=250.0):
        self.cell = cell_m
        self.grid = defaultdict(list)
        for s in stops:
            x, y = PROJ.to_xy(s.lat, s.lon)
            self.grid[(int(x // cell_m), int(y // cell_m))].append(s)

    def within(self, lat, lon, radius_m):
        """[(distance_m, stop)] for every stop within radius_m, nearest first."""
        x, y = PROJ.to_xy(lat, lon)
        k = int(math.ceil(radius_m / self.cell))
        cx, cy = int(x // self.cell), int(y // self.cell)
        out = []
        for i in range(cx - k, cx + k + 1):
            for j in range(cy - k, cy + k + 1):
                for s in self.grid.get((i, j), ()):
                    d = haversine_m(lat, lon, s.lat, s.lon)
                    if d <= radius_m:
                        out.append((d, s))
        out.sort(key=lambda t: t[0])
        return out

    def nearest(self, lat, lon, max_m=5000.0):
        r = self.cell
        while r <= max_m:
            hits = self.within(lat, lon, r)
            if hits:
                return hits[0]
            r *= 2
        return None


class TransitGraph:
    def __init__(self, network, assumptions):
        self.a = assumptions
        served = sorted(network.served_stop_ids())
        self.stop_index = {s: i for i, s in enumerate(served)}
        self.stop_ids = served
        n = len(served)
        self.n_stops = n
        self.pattern_base = {}
        nxt = 2 * n
        for key in sorted(network.patterns):
            self.pattern_base[key] = nxt
            nxt += len(network.patterns[key].stop_ids)
        self.n_nodes = nxt
        adj = [[] for _ in range(nxt)]            # node -> [(to, seconds, boards)]

        for i in range(n):
            adj[i].append((n + i, 0.0, 0))         # arrival -> departure at the same stop
        index = StopIndex([network.stops[s] for s in served])
        board_s = assumptions.wait_s + assumptions.transfer_penalty_s
        for s in served:
            st = network.stops[s]
            for d, t in index.within(st.lat, st.lon, assumptions.max_transfer_walk_m):
                if t.id != s:
                    walk = d * assumptions.walk_detour / assumptions.walk_speed_mps
                    adj[self.stop_index[s]].append((n + self.stop_index[t.id], walk, 0))

        for key, p in network.patterns.items():
            base = self.pattern_base[key]
            speed = assumptions.cruise_mps(network.routes[p.route_id].zone)
            last = len(p.stop_ids) - 1
            for i, s in enumerate(p.stop_ids):
                si = self.stop_index[s]
                if i < last:
                    adj[n + si].append((base + i, board_s, 1))
                    hop = p.chainage_m[i + 1] - p.chainage_m[i]
                    adj[base + i].append((base + i + 1, hop / speed + assumptions.stop_loss_s, 0))
                if i > 0:
                    adj[base + i].append((si, 0.0, 0))
        self.adj = adj

    def arrival(self, stop_id):
        return self.stop_index[stop_id]

    def departure(self, stop_id):
        return self.n_stops + self.stop_index[stop_id]

    def search(self, sources, cutoff_s=math.inf):
        """Dijkstra from {node: start cost}. Returns (cost, boardings) per node."""
        dist = [math.inf] * self.n_nodes
        boards = [0] * self.n_nodes
        heap = []
        for node, c in sources.items():
            if c < dist[node]:
                dist[node] = c
                heap.append((c, node))
        heapq.heapify(heap)
        adj = self.adj
        while heap:
            c, u = heapq.heappop(heap)
            if c > dist[u] or c > cutoff_s:
                continue
            bu = boards[u]
            for v, w, b in adj[u]:
                nc = c + w
                if nc < dist[v]:
                    dist[v] = nc
                    boards[v] = bu + b
                    heapq.heappush(heap, (nc, v))
        return dist, boards
