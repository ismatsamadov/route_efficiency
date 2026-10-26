"""The GTFS writer (busnet/gtfs.py) on the two-route test network, with route 1's outbound
line cut short after stop 3 and a repeated point, as AYNA's lines sometimes are."""

import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from busnet.assumptions import Assumptions
from busnet.gtfs import shape_points, write_gtfs
from busnet.model import Pattern

from .helpers import two_route_network


def short_line_network():
    net = two_route_network()
    p = net.patterns[(1, 1)]
    pts = [(net.stops[s].lat, net.stops[s].lon) for s in p.stop_ids]
    net.patterns[(1, 1)] = Pattern(1, 1, p.stop_ids, p.chainage_m, [pts[0], pts[0], pts[1], pts[2]], "shape")
    return net


def read(feed):
    with zipfile.ZipFile(feed) as z:
        return {name: list(csv.DictReader(io.StringIO(z.read(name).decode("utf-8")))) for name in z.namelist()}


class GtfsTest(unittest.TestCase):
    def setUp(self):
        self.net = short_line_network()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.feed = Path(tmp.name) / "feed.zip"
        write_gtfs(self.feed, self.net, Assumptions(), {1: (10, "test"), 2: (15, "test")}, "today")
        self.tables = read(self.feed)

    def test_files_and_feed_info(self):
        for name in ("agency.txt", "feed_info.txt", "stops.txt", "routes.txt", "calendar.txt", "trips.txt",
                     "stop_times.txt", "shapes.txt", "frequencies.txt"):
            self.assertIn(name, self.tables)
        info = self.tables["feed_info.txt"][0]
        self.assertEqual(info["feed_version"], "today")
        self.assertEqual(info["feed_lang"], "az")

    def test_stop_times_resolve_and_increase(self):
        stops = {r["stop_id"] for r in self.tables["stops.txt"]}
        trips = {r["trip_id"] for r in self.tables["trips.txt"]}
        last = {}
        for r in self.tables["stop_times.txt"]:
            self.assertIn(r["stop_id"], stops)
            self.assertIn(r["trip_id"], trips)
            self.assertGreater(r["arrival_time"], last.get(r["trip_id"], ""))
            last[r["trip_id"]] = r["arrival_time"]

    def test_repeated_points_are_written_once(self):
        for shape in {r["shape_id"] for r in self.tables["shapes.txt"]}:
            dist = [float(r["shape_dist_traveled"]) for r in self.tables["shapes.txt"] if r["shape_id"] == shape]
            self.assertTrue(all(b > a for a, b in zip(dist, dist[1:])), shape)

    def test_short_line_is_carried_on_to_the_last_stops(self):
        pts = shape_points(self.net.patterns[(1, 1)], self.net)
        stops = [(self.net.stops[s].lat, self.net.stops[s].lon) for s in (4, 5)]
        self.assertEqual(pts[-2:], stops)
        rows = [r for r in self.tables["shapes.txt"] if r["shape_id"] == "shape_1_1"]
        self.assertEqual(len(rows), 5)                # stops 1, 2 and 3 on the line, then 4 and 5
        self.assertAlmostEqual(float(rows[-1]["shape_dist_traveled"]), self.net.patterns[(1, 1)].length_m, delta=1)

    def test_full_lines_are_left_alone(self):
        p = self.net.patterns[(1, 2)]
        self.assertEqual(shape_points(p, self.net), p.path)


if __name__ == "__main__":
    unittest.main()
