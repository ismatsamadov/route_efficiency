"""The bicycle readers and measures: a small KMZ in the shape of AYNA's files reads back
(lanes by folder, parking points by name, Google Earth's sample places dropped), the line
index agrees with brute force, the measures come out right on the test network, and
bicycle.py regenerates the committed output/bicycle/ (about four seconds)."""

import math
import random
import tempfile
import unittest
import zipfile
from pathlib import Path

from busnet.assumptions import Assumptions
from busnet.bicycle import LANES_2025_FOLDER, LineIndex, along, load_lanes, load_parking, measure, placemarks
from busnet.geo import PROJ, Polyline, haversine_m
from tests.helpers import two_route_network
from tests.test_regression import ROOT, differences, regenerate

KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>test.kmz</name>
<Folder><name>Temporary Places</name>
  <Folder><name>Velosiped yolları 2025 yanvar</name>
    <Placemark><name>Old st.</name><LineString><coordinates>49.80,40.40,0 49.81,40.40,0</coordinates></LineString></Placemark>
  </Folder>
  <Folder><name>Mövcud zolaqlar</name>
    <Placemark><name>Main st.</name><LineString><coordinates>49.80,40.40,0 49.82,40.40,0 49.84,40.40,0</coordinates></LineString></Placemark>
    <Placemark><name>Side st.</name><LineString><coordinates>49.82,40.40,0 49.82,40.41,0</coordinates></LineString></Placemark>
    <Placemark><name>8 Noyabr pr.</name><LineString><coordinates></coordinates></LineString></Placemark>
  </Folder>
  <Folder><name>My Places</name>
    <Placemark><name>MPS-1</name><Point><coordinates>49.804,40.4002,0</coordinates></Point></Placemark>
    <Placemark><name>MPS-2</name><Point><coordinates>49.83,40.405,0</coordinates></Point></Placemark>
    <Folder><name>Sightseeing Tour</name>
      <Placemark><name>The Eiffel Tower</name><description>Located in Paris, France</description>
        <Point><coordinates>2.2945,48.8583,0</coordinates></Point></Placemark>
    </Folder>
  </Folder>
  <Folder><name>velosiped məntəqələri yeni</name>
    <Placemark><name>MPV-1-2</name><Point><coordinates>49.804,40.4002,0</coordinates></Point></Placemark>
    <Placemark><name>MPV-2-3</name><Point><coordinates>49.86,40.42,0</coordinates></Point></Placemark>
  </Folder>
</Folder></Document></kml>
"""


def write_kmz(folder):
    path = Path(folder) / "test.kmz"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("doc.kml", KML)
    return path


def brute_nearest(lines, lat, lon):
    x, y = PROJ.to_xy(lat, lon)
    best = math.inf
    for _, line in lines:
        for (ax, ay), (bx, by) in zip(line.xy, line.xy[1:]):
            dx, dy = bx - ax, by - ay
            seg2 = dx * dx + dy * dy
            t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / seg2))
            best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


class Readers(unittest.TestCase):
    def test_lanes_come_from_their_folder_and_empty_lines_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            lanes, skipped = load_lanes(write_kmz(tmp))
            self.assertEqual([lane.name for lane in lanes], ["Main st.", "Side st."])
            self.assertEqual(skipped, ["8 Noyabr pr."])
            self.assertAlmostEqual(lanes[0].length_m, haversine_m(40.40, 49.80, 40.40, 49.82) + haversine_m(40.40, 49.82, 40.40, 49.84), places=6)
            old, skipped_old = load_lanes(write_kmz(tmp), LANES_2025_FOLDER)
            self.assertEqual(([lane.name for lane in old], skipped_old), (["Old st."], []))

    def test_parking_points_are_read_by_name_and_sample_places_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            parking = load_parking(write_kmz(tmp))
            self.assertEqual([p.name for p in parking], ["MPS-1", "MPS-2", "MPV-1-2", "MPV-2-3"])
            self.assertEqual([p.kind for p in parking], ["MPS", "MPS", "MPV", "MPV"])
            self.assertEqual([p.suffix for p in parking], [None, None, 2, 3])
            self.assertEqual((parking[0].lat, parking[0].lon), (40.4002, 49.804))

    def test_placemarks_carry_their_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            marks = {name: folders for folders, name, _, _ in placemarks(write_kmz(tmp))}
            self.assertEqual(marks["MPS-1"], ("test.kmz", "Temporary Places", "My Places"))
            self.assertEqual(marks["The Eiffel Tower"], ("test.kmz", "Temporary Places", "My Places", "Sightseeing Tour"))
            self.assertEqual(marks["8 Noyabr pr."], ("test.kmz", "Temporary Places", "Mövcud zolaqlar"))


class Geometry(unittest.TestCase):
    def test_line_index_agrees_with_brute_force(self):
        rng = random.Random(3)
        lines = []
        for k in range(12):
            pts = [(40.35 + rng.random() * 0.1, 49.80 + rng.random() * 0.15)]
            for _ in range(rng.randint(1, 6)):
                pts.append((pts[-1][0] + rng.uniform(-0.004, 0.004), pts[-1][1] + rng.uniform(-0.005, 0.005)))
            lines.append((f"line {k}", Polyline(pts)))
        index = LineIndex(lines, cell_m=150.0)
        for _ in range(300):
            lat, lon = 40.34 + rng.random() * 0.12, 49.79 + rng.random() * 0.17
            truth = brute_nearest(lines, lat, lon)
            for radius in (60.0, 400.0, 1500.0):
                hit = index.nearest(lat, lon, radius)
                if truth <= radius:
                    self.assertIsNotNone(hit)
                    self.assertAlmostEqual(hit[0], truth, places=6)
                else:
                    self.assertIsNone(hit)
            self.assertAlmostEqual(index.nearest_any(lat, lon)[0], truth, places=6)

    def test_along_adds_up_to_the_path_length(self):
        lane = Polyline([(40.40, 49.80), (40.40, 49.84)])
        index = LineIndex([("Main st.", lane)])
        beside = [(40.4001, 49.805), (40.4001, 49.835)]
        metres = along(beside, index, 40.0)
        self.assertAlmostEqual(sum(metres.values()), Polyline(beside).length_m, places=6)
        self.assertEqual(list(metres), ["Main st."])
        self.assertEqual(along([(40.45, 49.805), (40.45, 49.835)], index, 40.0), {})
        # Along the lane, then 1.1 km north and on: only the first leg and the first metres of the turn count.
        turn = [(40.4001, 49.81), (40.4001, 49.82), (40.4101, 49.82), (40.4101, 49.83)]
        near = sum(along(turn, index, 40.0).values())
        first_leg = haversine_m(40.4001, 49.81, 40.4001, 49.82)
        self.assertGreaterEqual(near, first_leg - 20)
        self.assertLessEqual(near, first_leg + 80)


class Measures(unittest.TestCase):
    def test_measures_on_the_test_network(self):
        net = two_route_network()        # stops 1 to 5 on the 40.40 parallel, 49.80 to 49.84
        with tempfile.TemporaryDirectory() as tmp:
            path = write_kmz(tmp)
            lanes, skipped = load_lanes(path)
            lanes_2025, _ = load_lanes(path, LANES_2025_FOLDER)
            parking = load_parking(path)
        zones = [(40.4002, 49.804, 100.0), (40.5, 49.9, 50.0)]
        exits = [("S", 40.40, 49.84)]
        r = measure(net, Assumptions(), zones, {"1": 1000}, lanes, lanes_2025, parking, exits, skipped)
        s = r["summary"]
        self.assertEqual(s["lanes"]["segments"], 2)
        self.assertEqual(s["lanes"]["skipped_placemarks"], ["8 Noyabr pr."])
        self.assertAlmostEqual(s["lanes"]["january_2025"]["km"], lanes_2025[0].length_m / 1000)
        self.assertEqual(s["bus"]["stops_within_m_of_lane"], {"50": 5, "100": 5, "200": 5})
        self.assertEqual(s["bus"]["routes_along_lanes"], 2)
        main = r["lanes"][0]
        self.assertEqual((main["street"], main["bus_routes"], main["stops_within_100m"]), ("Main st.", "1 2A", 5))
        self.assertAlmostEqual(main["km_beside_bus_route"], main["km"], places=6)
        self.assertEqual(r["lanes"][1]["bus_routes"], "")
        route1 = r["routes"][0]
        self.assertEqual((route1["route"], route1["weekday_boardings"], route1["streets"]), ("1", 1000, "Main st."))
        self.assertAlmostEqual(route1["km_along_lanes"], route1["one_way_km"], places=6)
        # The first zone is 22 m from the lane, on the MPV point and 340 m from stop 1; the second is far from everything.
        self.assertEqual(s["people"], {"study_area": 150.0, "within_radius_of_lane": 100.0, "within_radius_of_stop": 100.0,
                                       "within_radius_of_both": 100.0, "within_radius_of_mpv_parking": 100.0})
        p = {row["name"]: row for row in r["parking"]}
        self.assertEqual(p["MPV-1-2"]["mps_within_5m"], "MPS-1")
        self.assertEqual(p["MPS-1"]["mps_within_5m"], "")
        self.assertEqual(p["MPV-1-2"]["nearest_lane"], "Main st.")
        self.assertAlmostEqual(p["MPV-1-2"]["m_to_lane"], haversine_m(40.4002, 49.804, 40.40, 49.804), delta=0.1)
        self.assertEqual(p["MPV-1-2"]["nearest_stop"], "stop 1")
        self.assertEqual(p["MPV-1-2"]["nearest_metro_exit"], "S")
        self.assertEqual(s["parking"]["MPV"]["within_50m_of_lane"], 1)
        self.assertEqual(s["parking"]["MPS"]["within_100m_of_stop"], 0)
        self.assertEqual(len(r["geojson"]["features"]), 2 + 4)


class CommittedResults(unittest.TestCase):
    def test_bicycle_regenerates_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            regenerate("bicycle.py", tmp)
            self.assertEqual(differences(ROOT / "output" / "bicycle", Path(tmp)), [])
