import unittest

from busnet.assumptions import Assumptions
from busnet.optimize import Plan, allocate
from tests.helpers import straight, two_route_network


class Plans(unittest.TestCase):
    def setUp(self):
        self.net = two_route_network()
        self.a = Assumptions()
        self.headways = {1: (10, "zone"), 2: (15, "zone")}
        self.plan = Plan.from_headways(self.net, self.a, self.headways)

    def test_buses_and_headways_are_inverses(self):
        for rid, (h, _) in self.headways.items():
            self.assertAlmostEqual(self.plan.fleet[rid], self.plan.cycle_min(rid, self.a) / h)
            self.assertAlmostEqual(self.plan.headways(self.a)[rid][0], h)
        self.assertAlmostEqual(self.plan.total_fleet(), sum(self.plan.fleet.values()))

    def test_cycle_time_includes_layover(self):
        from busnet.service import run_time_s
        round_trip = sum(run_time_s(p, self.net, self.a) for p in self.net.patterns_of(1)) / 60
        self.assertAlmostEqual(self.plan.cycle_min(1, self.a), round_trip * 1.15)

    def test_headways_never_go_below_the_minimum(self):
        crowded = Plan(self.net, {1: 1000.0, 2: 1000.0})
        self.assertEqual(crowded.headways(self.a)[1][0], self.a.min_headway_min)

    def test_dropping_a_route_leaves_the_original_untouched(self):
        new = self.plan.changed(drop=[2])
        self.assertNotIn(2, new.fleet)
        self.assertEqual({k for k in new.network.patterns}, {(1, 1), (1, 2)})
        self.assertIn(2, self.plan.fleet)
        self.assertIn((2, 1), self.plan.network.patterns)
        self.assertEqual(new.stops_of(1), {1, 2, 3, 4, 5})

    def test_replacing_a_pattern_leaves_the_original_untouched(self):
        self.net.repairs.append("a repair")
        new = self.plan.changed(patterns={(1, 1): straight(1, 1, self.net.stops, [1, 3, 5])})
        self.assertEqual(new.network.patterns[(1, 1)].stop_ids, [1, 3, 5])
        self.assertEqual(self.plan.network.patterns[(1, 1)].stop_ids, [1, 2, 3, 4, 5])
        self.assertEqual(new.network.repairs, ["a repair"])
        self.assertEqual(new.fleet, self.plan.fleet)

    def test_a_route_with_no_patterns_gets_no_buses(self):
        self.assertNotIn(9, Plan(self.net, {1: 2.0, 9: 5.0}).fleet)


class Allocation(unittest.TestCase):
    def setUp(self):
        self.net = two_route_network()
        self.a = Assumptions()
        self.plan = Plan.from_headways(self.net, self.a, {1: (10, "zone"), 2: (15, "zone")})

    def test_buses_are_shared_in_proportion_to_weights(self):
        fleet = dict(self.plan.fleet)
        left = allocate(self.plan, fleet, 0.3, {1: 2, 2: 1}, self.a)
        self.assertAlmostEqual(left, 0.0)
        self.assertAlmostEqual(fleet[1] - self.plan.fleet[1], 0.2)
        self.assertAlmostEqual(fleet[2] - self.plan.fleet[2], 0.1)

    def test_no_route_gets_more_buses_than_the_minimum_headway_allows(self):
        fleet = dict(self.plan.fleet)
        room = sum(self.plan.cycle_min(r, self.a) / self.a.min_headway_min - f for r, f in fleet.items())
        left = allocate(self.plan, fleet, 1000.0, {1: 1, 2: 1}, self.a)
        self.assertAlmostEqual(left, 1000.0 - room)
        for rid in fleet:
            self.assertAlmostEqual(self.plan.changed(fleet=fleet).headways(self.a)[rid][0], self.a.min_headway_min)

    def test_a_full_routes_share_goes_to_the_routes_with_room(self):
        fleet = dict(self.plan.fleet)
        room2 = self.plan.cycle_min(2, self.a) / self.a.min_headway_min - fleet[2]     # the short route fills first
        left = allocate(self.plan, fleet, 6.0, {1: 1, 2: 1}, self.a)
        self.assertAlmostEqual(left, 0.0)
        self.assertAlmostEqual(fleet[2], self.plan.cycle_min(2, self.a) / self.a.min_headway_min)
        self.assertAlmostEqual(fleet[1] - self.plan.fleet[1], 6.0 - room2)
