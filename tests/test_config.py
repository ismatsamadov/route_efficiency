import tempfile
import unittest
from pathlib import Path

from busnet.assumptions import Assumptions
from busnet.config import DATA_KEYS, load_config, parse_value

ROOT = Path(__file__).resolve().parents[1]


class Settings(unittest.TestCase):
    def test_no_file_gives_the_defaults(self):
        self.assertEqual(load_config(None), (Assumptions(), {}))

    def test_the_repository_settings_file_repeats_the_defaults(self):
        a, data = load_config(ROOT / "busnet.toml")
        self.assertEqual(a, Assumptions())
        self.assertEqual(set(data), set(DATA_KEYS))
        for key, path in data.items():
            for p in (path if isinstance(path, list) else [path]):
                self.assertTrue(Path(p).exists(), f"{key}: {p} is missing")

    def test_unknown_setting_is_an_error(self):
        with self.assertRaises(ValueError) as cm:
            load_config(None, ["walk_speed=1"])
        self.assertIn("unknown setting", str(cm.exception))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.toml"
            path.write_text("[walking]\nwalk_speed = 1\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(path)

    def test_set_needs_name_equals_value(self):
        with self.assertRaises(ValueError):
            load_config(None, ["transfer_penalty_min"])

    def test_set_overrides_and_merges_tables(self):
        a, data = load_config(None, ["transfer_penalty_min=8", 'headway_by_zone={"Şəhərdaxili" = 8}', "db=data/x.db"])
        self.assertEqual(a.transfer_penalty_min, 8)
        self.assertEqual(a.headway_by_zone["Şəhərdaxili"], 8)
        self.assertEqual(a.headway_by_zone["Şəhərətrafı"], Assumptions().headway_by_zone["Şəhərətrafı"])
        self.assertTrue(data["db"].endswith("data/x.db"))

    def test_values_are_read_as_toml(self):
        self.assertEqual(parse_value("12"), 12)
        self.assertEqual(parse_value("0.5"), 0.5)
        self.assertIs(parse_value("false"), False)
        self.assertEqual(parse_value('"text"'), "text")
        self.assertEqual(parse_value("bare word"), "bare word")
        self.assertEqual(parse_value('["180", "519"]'), ["180", "519"])
