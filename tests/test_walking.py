"""Walking distances along streets (busnet/walking.py), on a made-up pair of streets
joined only at one end, so that the walk is far longer than the straight line."""

import gzip
import json
import math
import tempfile
import unittest
from pathlib import Path

from busnet.geo import PROJ, haversine_m
from busnet.walking import WalkNetwork, load_overpass, load_walk_network, walkable


def ll(x, y):
    """(lat, lon) of a point x metres east and y metres north of the projection's centre."""
    return PROJ.to_latlon(x, y)


# Two east-west streets 1,000 m long and 300 m apart, joined by a north-south street at
# their east ends only. Node ids: 1 to 3 on the south street, 4 to 6 on the north one.
NODES = {1: ll(0, 0), 2: ll(500, 0), 3: ll(1000, 0), 4: ll(0, 300), 5: ll(500, 300), 6: ll(1000, 300),
         7: ll(0, -50)}
STREETS = {"south": ([1, 2, 3], {"highway": "residential"}),
           "north": ([4, 5, 6], {"highway": "residential"}),
           "east link": ([3, 6], {"highway": "footway"}),
           "motorway at the west end": ([1, 4], {"highway": "motorway"}),
           "private lane at the west end": ([1, 4], {"highway": "service", "service": "private"})}


def network(*extra):
    """The streets above plus extra (node ids, tags) ways, filtered as the loader filters."""
    ways = [nodes for nodes, tags in list(STREETS.values()) + list(extra) if walkable(tags)]
    return WalkNetwork(NODES, ways)


def overpass_json(extra=()):
    elements = [{"type": "way", "id": i, "nodes": nodes, "tags": tags}
                for i, (nodes, tags) in enumerate(list(STREETS.values()) + list(extra), start=1)]
    elements += [{"type": "node", "id": i, "lat": lat, "lon": lon} for i, (lat, lon) in NODES.items()]
    return {"osm3s": {"timestamp_osm_base": "2026-10-25T14:00:00Z"}, "elements": elements}


class Walkable(unittest.TestCase):
    def test_streets_paths_and_steps_can_be_walked(self):
        for highway in ("residential", "footway", "path", "steps", "pedestrian", "living_street", "service",
                        "tertiary", "primary", "trunk", "track", "unclassified"):
            self.assertTrue(walkable({"highway": highway}), highway)

    def test_motorways_cycleways_and_unbuilt_ways_cannot(self):
        for highway in ("motorway", "motorway_link", "cycleway", "construction", "proposed", "raceway", "platform", "busway"):
            self.assertFalse(walkable({"highway": highway}), highway)

    def test_tags_that_forbid_or_allow_walking(self):
        self.assertFalse(walkable({"highway": "primary", "foot": "no"}))
        self.assertFalse(walkable({"highway": "service", "service": "private"}))
        self.assertFalse(walkable({"highway": "service", "access": "private"}))
        self.assertFalse(walkable({"highway": "residential", "access": "no"}))
        self.assertTrue(walkable({"highway": "residential", "access": "no", "foot": "yes"}))
        self.assertTrue(walkable({"highway": "cycleway", "foot": "designated"}))
        self.assertFalse(walkable({"highway": "motorway", "foot": "yes"}))
        self.assertFalse(walkable({"highway": "pedestrian", "area": "yes"}))
        self.assertFalse(walkable({"building": "yes"}))


class Distances(unittest.TestCase):
    def test_the_graph_keeps_only_walkable_ways(self):
        net = network()
        self.assertEqual(net.n, 6)                       # node 7 is on no way
        self.assertEqual(net.edges, 5)                   # 2 + 2 segments and the east link; no motorway, no private lane

    def test_the_walk_goes_round_by_the_east_link(self):
        net = network()
        point, stop = ll(0, 0), ll(0, 300)
        self.assertAlmostEqual(haversine_m(*point, *stop), 300, delta=1)
        (d,) = net.walk_distances([point], [stop], cutoff=5000)
        self.assertAlmostEqual(d, 2300, delta=5)

    def test_a_cycleway_counts_only_when_feet_are_allowed(self):
        link = ([2, 5], {"highway": "cycleway"})
        (d,) = network(link).walk_distances([ll(0, 0)], [ll(0, 300)], cutoff=5000)
        self.assertAlmostEqual(d, 2300, delta=5)
        link = ([2, 5], {"highway": "cycleway", "foot": "yes"})
        (d,) = network(link).walk_distances([ll(0, 0)], [ll(0, 300)], cutoff=5000)
        self.assertAlmostEqual(d, 1300, delta=5)

    def test_a_point_off_the_street_walks_the_gap_in_a_straight_line(self):
        net = network()
        (d,) = net.walk_distances([ll(0, -50)], [ll(0, 300)], cutoff=5000)
        self.assertAlmostEqual(d, 2350, delta=5)
        (d,) = net.walk_distances([ll(250, -40)], [ll(250, 340)], cutoff=5000)   # stop off the street too
        self.assertAlmostEqual(d, 40 + 750 + 300 + 750 + 40, delta=5)

    def test_a_stop_on_the_same_segment_is_reached_along_it(self):
        net = network()
        (d,) = net.walk_distances([ll(100, 0)], [ll(400, 0)], cutoff=5000)
        self.assertAlmostEqual(d, 300, delta=3)
        (d,) = net.walk_distances([ll(100, 0)], [ll(400, 0), ll(0, 300)], cutoff=5000)
        self.assertAlmostEqual(d, 300, delta=3)

    def test_beyond_the_cutoff_or_off_the_network_is_infinite(self):
        net = network()
        self.assertEqual(net.walk_distances([ll(0, 0)], [ll(0, 300)], cutoff=1000), [math.inf])
        self.assertEqual(net.walk_distances([ll(20000, 0)], [ll(0, 300)], cutoff=5000), [math.inf])
        self.assertEqual(net.walk_distances([ll(0, 0)], [ll(20000, 0)], cutoff=5000), [math.inf])

    def test_snap_finds_the_nearest_segment_at_any_distance(self):
        net = network()
        e, t, gap = net.snap(*ll(700, 1500))
        self.assertAlmostEqual(gap, 1200, delta=2)
        self.assertEqual({net.eu[e], net.ev[e]}, {net_index(net, 5), net_index(net, 6)})
        self.assertAlmostEqual(t, 0.4, delta=0.01)
        self.assertIsNone(net.snap(*ll(700, 1500), max_m=1000))


def net_index(net, osm_id):
    lat, lon = NODES[osm_id]
    return min(range(net.n), key=lambda i: haversine_m(net.lats[i], net.lons[i], lat, lon))


class Loading(unittest.TestCase):
    def test_overpass_answers_load_plain_or_gzipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            plain, zipped = Path(tmp) / "walk.json", Path(tmp) / "walk.json.gz"
            text = json.dumps(overpass_json())
            plain.write_text(text, encoding="utf-8")
            zipped.write_bytes(gzip.compress(text.encode()))
            for path in (plain, zipped):
                nodes, ways, info = load_overpass(path)
                self.assertEqual(len(nodes), 7)
                self.assertEqual(len(ways), 3)
                self.assertEqual(info, {"osm_date": "2026-10-25T14:00:00Z", "ways": 5, "ways_walkable": 3})
            net, info = load_walk_network(zipped)
            self.assertEqual((info["nodes"], info["edges"]), (6, 5))
            self.assertAlmostEqual(net.walk_distances([ll(0, 0)], [ll(0, 300)], cutoff=5000)[0], 2300, delta=5)
