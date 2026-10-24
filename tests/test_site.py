"""The page in index.html: site/build.py regenerates the committed site/ files, its helpers
do what the page expects, and every local file the page links to exists.

The build takes about three seconds and always runs. Its data must match the committed
data.js to within rounding (see test_regression.py), and the workbooks part for part."""

import importlib.util
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from tests.test_regression import _same

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("site_build", ROOT / "site" / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


def page_data(path):
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(text[text.index("=") + 1:].strip().rstrip(";"))


def parts(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


class CommittedSite(unittest.TestCase):
    def test_build_regenerates_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            build.build(Path(tmp))
            self.assertTrue(_same(page_data(ROOT / "site" / "data.js"), page_data(Path(tmp) / "data.js"), 1e-9))
            for lang in ("az", "en"):
                name = f"checklist-{lang}.xlsx"
                self.assertEqual(parts(ROOT / "site" / name), parts(Path(tmp) / name), name)

    def test_page_links_to_files_that_exist(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        refs = re.findall(r'(?:href|src)="([^"#:]+)"', html)
        self.assertIn("site/data.js", refs)
        for ref in refs:
            self.assertTrue((ROOT / ref).is_file(), ref)


class Helpers(unittest.TestCase):
    def test_encode_matches_the_published_example(self):
        self.assertEqual(build.encode([(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]),
                         "_p~iF~ps|U_ulLnnqC_mqNvxq`@")

    def test_simplify_keeps_the_ends_and_the_bends(self):
        straight = [(40.4, 49.8 + 0.001 * i) for i in range(11)]
        self.assertEqual(build.simplify(straight, 6.0), [straight[0], straight[-1]])
        bent = straight[:5] + [(40.401, 49.805)] + straight[6:]           # 111 m off the line
        self.assertIn((40.401, 49.805), build.simplify(bent, 6.0))

    def test_repairs_are_sorted_into_kinds(self):
        rows = build.parse_repairs([
            "120A d1: stop list was repeated twice; kept one copy",
            "4: shapes were filed under the wrong direction (stored d2 -> d1, stored d1 -> d2)",
            "550 d1: shape cannot explain its stops (straight jump of 17.7 km); using straight lines between stops",
            "9 d2: a defect nobody has seen yet",
        ])
        self.assertEqual([(r["route"], r["direction"], r["kind"]) for r in rows],
                         [("120A", 1, "repeated_stops"), ("4", None, "wrong_direction"),
                          ("550", 1, "scrambled"), ("9", 2, "other")])
        self.assertEqual(rows[2]["jump_km"], 17.7)

    def test_workbook_is_a_well_formed_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.xlsx"
            build.write_xlsx(path, [("Sheet & one", [10, 20], [["Route", "Name"], ["120A", "Ə < ş"], [1, 2.5]],
                                     ["text", "1"], True)])
            files = parts(path)
        self.assertLessEqual({"[Content_Types].xml", "xl/workbook.xml", "xl/worksheets/sheet1.xml", "xl/styles.xml"},
                             set(files))
        for content in files.values():
            ElementTree.fromstring(content)
        sheet = files["xl/worksheets/sheet1.xml"].decode("utf-8")
        self.assertIn("Ə &lt; ş", sheet)
        self.assertIn('<autoFilter ref="A1:B3"/>', sheet)
        self.assertIn("'Sheet &amp; one'!$A$1:$B$3", files["xl/workbook.xml"].decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
