import unittest

from busnet.geo import PROJ, Polyline, fit_score, haversine_m, match_stops

LAT, LON = 40.40, 49.80


def east_line(km, points=6):
    """A straight line running east from (LAT, LON), about km long."""
    dlon = km / 111.195 / 0.7615 / (points - 1)          # cos(40.4 degrees) is about 0.7615
    return Polyline([(LAT, LON + dlon * i) for i in range(points)])


class Distances(unittest.TestCase):
    def test_haversine_one_degree_of_longitude_at_the_equator(self):
        self.assertAlmostEqual(haversine_m(0, 0, 0, 1), 111_194.9, delta=1)

    def test_haversine_is_symmetric_and_zero_at_the_same_point(self):
        self.assertEqual(haversine_m(LAT, LON, LAT, LON), 0.0)
        self.assertAlmostEqual(haversine_m(LAT, LON, LAT + 0.01, LON + 0.01), haversine_m(LAT + 0.01, LON + 0.01, LAT, LON))

    def test_projection_round_trip(self):
        x, y = PROJ.to_xy(LAT + 0.1, LON - 0.2)
        lat, lon = PROJ.to_latlon(x, y)
        self.assertAlmostEqual(lat, LAT + 0.1, places=9)
        self.assertAlmostEqual(lon, LON - 0.2, places=9)

    def test_projection_matches_great_circle_locally(self):
        (x1, y1), (x2, y2) = PROJ.to_xy(LAT, LON), PROJ.to_xy(LAT + 0.02, LON + 0.03)
        flat = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        self.assertAlmostEqual(flat / haversine_m(LAT, LON, LAT + 0.02, LON + 0.03), 1.0, delta=0.01)


class Polylines(unittest.TestCase):
    def test_length_point_at_and_slice(self):
        line = east_line(5.0)
        self.assertAlmostEqual(line.length_m, 5000, delta=5)
        lat, lon = line.point_at(2500)
        self.assertAlmostEqual(lat, LAT, places=9)
        self.assertAlmostEqual(haversine_m(LAT, LON, lat, lon), 2500, delta=3)
        part = line.slice_latlon(1000, 3000)
        self.assertAlmostEqual(haversine_m(*part[0], *part[-1]), 2000, delta=3)
        self.assertEqual(line.reversed().latlon, line.latlon[::-1])

    def test_max_jump(self):
        self.assertAlmostEqual(east_line(5.0).max_jump_m(), 1000, delta=1)


class StopMatching(unittest.TestCase):
    def setUp(self):
        self.line = east_line(5.0)
        # five stops along the line, 11 m north of it
        self.stops = [self.line.point_at(k * 1000) for k in range(5)]
        self.stops = [(lat + 0.0001, lon) for lat, lon in self.stops]

    def test_stops_in_order_have_no_breaks_and_rising_chainage(self):
        m = match_stops(self.line, self.stops)
        self.assertFalse(any(x["order_break"] for x in m))
        chain = [x["chainage_m"] for x in m]
        self.assertEqual(chain, sorted(chain))
        for x, k in zip(m, range(5)):
            self.assertAlmostEqual(x["chainage_m"], k * 1000, delta=3)
            self.assertAlmostEqual(x["offset_m"], 11.1, delta=0.5)

    def test_stops_in_reverse_order_break_the_order_at_every_stop_but_the_first(self):
        breaks, median, m = fit_score(self.line, self.stops[::-1])
        self.assertEqual(breaks, 4)
        self.assertAlmostEqual(median, 11.1, delta=0.5)
        self.assertEqual(fit_score(self.line.reversed(), self.stops[::-1])[0], 0)

    def listed_out_of_order(self, step_deg):
        """The third stop moved to just before the fourth, and listed after it."""
        stops = list(self.stops)
        stops[2] = (stops[2][0], stops[3][1] - step_deg)
        stops[2], stops[3] = stops[3], stops[2]
        return stops

    def test_a_small_backward_step_within_the_tolerance_is_not_a_break(self):
        m = match_stops(self.line, self.listed_out_of_order(0.0002))             # about 17 m back
        self.assertFalse(any(x["order_break"] for x in m))

    def test_a_backward_step_beyond_the_tolerance_is_one_break(self):
        m = match_stops(self.line, self.listed_out_of_order(0.0006))             # about 51 m back
        self.assertEqual([x["order_break"] for x in m], [False, False, False, True, False])
