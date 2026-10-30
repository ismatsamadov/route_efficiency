"""The benchmark scoring and rules (busnet/utrp.py): the published route sets must score as
their authors published them, Mumford (2013), Hüsselmann et al. (2024) and Jiao (2026),
and the straightening search must keep every rule, shown on a made-up five-node network
where one route makes an obvious detour."""

import math
import tempfile
import unittest
from pathlib import Path

from busnet import utrp

EXTERNAL = Path(__file__).resolve().parents[1] / "data" / "external" / "utrp"
SUPPLEMENT = EXTERNAL / "CEC2013Supp.zip"
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


class LaterSets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.instances = {name: utrp.load_instance(SUPPLEMENT, name) for name in utrp.RULES}

    def test_husselmann_sets_score_as_their_files_say(self):
        """Their Mandl demand matrix has 10 trips between nodes 3 and 4 where Mumford's file
        has 40, so on Mandl only the route times must agree and ATT within 0.05 minutes."""
        seen = set()
        for source, method, name, file, kinds in utrp.LATER_SETS:
            data = utrp.husselmann_route_sets(EXTERNAL / file)
            for who in kinds:
                self.assertNotIn((method, name, who), seen)
                seen.add((method, name, who))
                routes, theirs = data[who], data["scores"][who]
                self.assertEqual(len(routes), utrp.RULES[name][0], (file, who))
                self.assertEqual(utrp.problems(self.instances[name], routes), [], (file, who))
                score = utrp.evaluate(self.instances[name], routes)
                self.assertEqual(score["route_time"], theirs["route_time"], (file, who))
                if name == "Mandl":
                    self.assertLess(abs(score["att"] - theirs["att"]), 0.05, (file, who))
                else:
                    for measure, value in theirs.items():
                        self.assertAlmostEqual(score[measure], value, places=3, msg=(file, who, measure))
        self.assertEqual(len(seen), 20)

    def test_jiao_sets_score_as_published(self):
        sets = utrp.jiao_route_sets(EXTERNAL / utrp.JIAO_FILE)
        self.assertEqual(sorted(sets), sorted(utrp.RULES))
        for name, (routes, att) in sets.items():
            self.assertEqual(len(routes), utrp.RULES[name][0])
            self.assertEqual(utrp.problems(self.instances[name], routes), [])
            score = utrp.evaluate(self.instances[name], routes)
            self.assertAlmostEqual(score["att"], att, places=4, msg=name)
            for measure, value in utrp.JIAO_SCORES[name].items():
                self.assertAlmostEqual(round(score[measure], 2), value, places=6, msg=(name, measure))

    def test_husselmann_file_format(self):
        text = ("x RESULTS EVALUATION:\n\\\nHV:0.5 | BM:0.5\n\n\\\n\tOperator\tPassenger\n\\\nf1_ATT\t13.5\t\t10.25\n\\\n"
                "f2_TRT\t63\t\t179\n\\\nd_0\t70\t\t95\n\\\nd_1\t24\t\t4\n\\\nd_2\t5\t\t1\n\\\nd_un\t1\t\t0\n\n\\\n"
                "Best Operator Route set:\n\\\n[[9, 6],\n[3, 4]]\n\n\\\nBest Passenger Route set:\n\\\n[[0, 1, 2],\n[5, 14, 6]]\n\n\\\n"
                "Best Operator Route set string:\n\\\n9-6*3-4*\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Extreme solutions.txt"
            path.write_text(text, encoding="utf-8")
            data = utrp.husselmann_route_sets(path)
        self.assertEqual(data["operator"], [[9, 6], [3, 4]])
        self.assertEqual(data["passenger"], [[0, 1, 2], [5, 14, 6]])
        self.assertEqual(data["scores"]["passenger"], {"att": 10.25, "route_time": 179, "d0": 95, "d1": 4, "d2": 1, "dun": 0})
        self.assertEqual(data["scores"]["operator"]["att"], 13.5)


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
