"""The benchmark scoring and rules (busnet/utrp.py): the published route sets must score as
Mumford (2013) published them, and the straightening search must keep every rule, shown
on a made-up five-node network where one route makes an obvious detour."""

import math
import unittest
from pathlib import Path

from busnet import utrp

SUPPLEMENT = Path(__file__).resolve().parents[1] / "data" / "external" / "utrp" / "CEC2013Supp.zip"
INF = math.inf


def small_network():
    """Nodes 0 to 4. Route [0, 1, 2, 3, 4] goes round by 1 and 2 although 0 and 3 are linked;
    route [0, 1, 2] also serves 1 and 2. Most trips go between 0 and 4."""
    links = {(0, 1): 1, (1, 2): 1, (2, 3): 1, (0, 3): 1, (3, 4): 1}
    time = [[0 if i == j else INF for j in range(5)] for i in range(5)]
    for (a, b), w in links.items():
        time[a][b] = time[b][a] = w
    demand = [[0] * 5 for _ in range(5)]
    for (a, b), q in {(0, 4): 100, (1, 3): 1}.items():
        demand[a][b] = demand[b][a] = q
    return utrp.Instance("small", time, demand, 2, 2, 5), [[0, 1, 2, 3, 4], [0, 1, 2]]


class PublishedSets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sets = utrp.published_route_sets(SUPPLEMENT)
        cls.scores = utrp.published_scores(SUPPLEMENT)
        cls.instances = {name: utrp.load_instance(SUPPLEMENT, name) for name in utrp.RULES}

    def test_all_ten_sets_are_read(self):
        self.assertEqual(sorted(self.sets), sorted((n, w) for n in utrp.RULES for w in ("passenger", "operator")))
        self.assertEqual(sorted(self.scores), sorted(self.sets))

    def test_scores_match_table_iv(self):
        for key, routes in self.sets.items():
            score = utrp.evaluate(self.instances[key[0]], routes)
            for measure, published in self.scores[key].items():
                self.assertAlmostEqual(round(score[measure], 2), published, places=6, msg=(key, measure))

    def test_published_sets_keep_the_rules(self):
        for (name, _), routes in self.sets.items():
            self.assertEqual(utrp.problems(self.instances[name], routes), [])


class Rules(unittest.TestCase):
    def setUp(self):
        self.inst, self.routes = small_network()

    def test_each_rule(self):
        cases = {
            "1 routes instead of 2": [[0, 1, 2, 3, 4]],
            "route 2 has 1 nodes": [[0, 1, 2, 3, 4], [0]],
            "route 2 visits a node twice": [[0, 1, 2, 3, 4], [0, 1, 0]],
            "route 2 leaves the links": [[0, 1, 2, 3, 4], [0, 2]],
            "2 nodes on no route": [[0, 3, 4], [3, 4]],
            "the routes fall apart into separate networks": [[0, 1], [2, 3, 4]],
        }
        for expected, routes in cases.items():
            self.assertIn(expected, utrp.problems(self.inst, routes))
        self.assertEqual(utrp.problems(self.inst, self.routes), [])

    def test_a_trip_without_a_path_scores_none(self):
        self.assertIsNone(utrp.evaluate(self.inst, [[0, 1], [2, 3, 4]]))


class Straightening(unittest.TestCase):
    def test_detour_is_found(self):
        inst, routes = small_network()
        dist, _ = utrp.quickest_paths(inst)
        self.assertEqual(utrp.detours(inst, routes[0], dist), [(2.0, 0, 3)])
        self.assertEqual(utrp.detours(inst, routes[1], dist), [])

    def test_search_straightens_and_keeps_the_rules(self):
        inst, routes = small_network()
        final, before, after, log, tried = utrp.search(inst, routes)
        self.assertEqual(final, [[0, 3, 4], [0, 1, 2]])
        self.assertEqual(utrp.problems(inst, final), [])
        self.assertLess(after["att"], before["att"])
        self.assertEqual((before["route_time"], after["route_time"]), (6, 4))
        self.assertEqual(len(log), 1)

    def test_a_change_to_a_route_that_has_changed_is_skipped(self):
        inst, routes = small_network()
        dist, prev = utrp.quickest_paths(inst)
        (change,) = utrp.candidates(inst, routes, dist, prev, 80)
        self.assertIsNone(change.apply([[0, 1, 2, 3], routes[1]]))

    def test_matlab_format_numbers_nodes_from_one(self):
        self.assertEqual(utrp.matlab([[0, 3, 4], [0, 1, 2]]), "routeset(1).route = [1 4 5];\nrouteset(2).route = [1 2 3];")


if __name__ == "__main__":
    unittest.main()
