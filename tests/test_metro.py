"""The metro tables in data/metro/: data/build_metro.py regenerates them byte for byte from
the committed downloads, and they hang together (27 stations, every one on a line and
named in every source, stops in order, intervals naming real stations)."""

import csv
import importlib.util
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("build_metro", ROOT / "data" / "build_metro.py")
build_metro = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_metro)
METRO = ROOT / "data" / "metro"


def rows(name):
    with open(METRO / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class CommittedMetroTables(unittest.TestCase):
    def test_build_regenerates_tables(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(StringIO()):
            build_metro.build(Path(tmp))
            for path in sorted(METRO.iterdir()):
                with self.subTest(file=path.name):
                    self.assertEqual(path.read_bytes(), (Path(tmp) / path.name).read_bytes())

    def test_stations(self):
        stations = rows("stations.csv")
        self.assertEqual(len(stations), 27)
        for st in stations:
            with self.subTest(station=st["station"]):
                self.assertTrue(st["lines"])
                for col in ("name_exits_en", "name_entries_2025", "name_entries_2026", "name_metro_api", "wikidata"):
                    self.assertTrue(st[col], col)
        self.assertEqual(sum(int(st["exits"]) for st in stations), 98)

    def test_stops_in_order(self):
        for r in rows("route_stops.csv"):
            if r["km_from_previous"]:
                self.assertGreater(float(r["km_from_previous"]), 0, r)
        for r in rows("run_times.csv"):
            self.assertGreaterEqual(int(r["s_from_previous"]), 0, r)
            self.assertEqual(r["by"] == "start", r["seq"] == "1", r)

    def test_headways_name_real_stations(self):
        names = {st["station"] for st in rows("stations.csv")}
        with open(ROOT / "data" / "metro_headways.csv", newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                with self.subTest(stretch=r["stretch"]):
                    self.assertTrue(set(r["stretch"].split(" – ")) <= names)
                    self.assertIn(r["line"], {"red", "green", "purple"})
                    self.assertTrue(r["source"])


if __name__ == "__main__":
    unittest.main()
