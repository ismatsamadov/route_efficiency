"""The animations in animations/: the GIF writer's output decodes, with an independent
decoder, to the frames it was given; the drawing helpers agree with each other; the buses
keep the GTFS feed's times; and the committed GIFs are valid and as long as what they show.

Drawing the animations takes minutes and is not repeated here. animations/build.py checks
its own words as it draws them: a character the font lacks, or a line that would run off
the picture, stops the build."""

import csv
import importlib.util
import math
import random
import statistics
import struct
import tempfile
import unittest
from pathlib import Path

from busnet.assumptions import Assumptions
from busnet.ridership import load_daily_boardings
from tests.helpers import two_route_network

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("animations_build", ROOT / "animations" / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)
draw = build.draw


def lzw_decode(data, min_size, count):
    """GIF's LZW, decoded the way a reader does it, independently of draw.lzw."""
    clear, end = 1 << min_size, (1 << min_size) + 1
    size, table, prev, out, pos = min_size + 1, [[i] for i in range(clear)] + [None, None], None, [], 0
    while pos + size <= len(data) * 8:
        k = pos // 8
        code = (int.from_bytes(bytes(data[k:k + 3]).ljust(3, b"\0"), "little") >> (pos % 8)) & ((1 << size) - 1)
        pos += size
        if code == clear:
            size, table, prev = min_size + 1, [[i] for i in range(clear)] + [None, None], None
            continue
        if code == end:
            break
        if prev is None:
            out += table[code]
        else:
            entry = table[code] if code < len(table) else table[prev] + [table[prev][0]]
            table.append(table[prev] + [entry[0]])
            out += entry
            if len(table) == 1 << size and size < 12:
                size += 1
        prev = code
    return out[:count]


def read_gif(data, pixels=True):
    """(width, height, loops, frames). Each frame is (x, y, w, h, delay) and, with pixels, the
    whole picture after it as (r, g, b) tuples, transparent pixels keeping what was there."""
    assert data[:6] == b"GIF89a"
    w, h, flags, _, _ = struct.unpack("<HHBBB", data[6:13])
    pos, size = 13, 2 << (flags & 7)
    palette = [tuple(data[pos + 3 * i:pos + 3 * i + 3]) for i in range(size)]
    pos += 3 * size
    screen, frames, gce, loops = [0] * (w * h), [], None, None

    def blocks():
        nonlocal pos
        out = []
        while data[pos]:
            out.append(data[pos + 1:pos + 1 + data[pos]])
            pos += 1 + data[pos]
        pos += 1
        return out

    while data[pos] != 0x3B:
        kind = data[pos]
        pos += 1
        if kind == 0x21:
            label = data[pos]
            pos += 1
            parts = blocks()
            if label == 0xF9:
                gce = struct.unpack("<BHB", parts[0][:4])
            elif label == 0xFF and parts[0] == b"NETSCAPE2.0":
                loops = struct.unpack("<H", parts[1][1:3])[0]
            continue
        assert kind == 0x2C, hex(kind)
        x, y, fw, fh, _ = struct.unpack("<HHHHB", data[pos:pos + 9])
        min_size = data[pos + 9]
        pos += 10
        code = b"".join(blocks())
        frame = (x, y, fw, fh, gce[1] if gce else 0)
        if pixels:
            idx = lzw_decode(code, min_size, fw * fh)
            transparent = gce is not None and gce[0] & 1
            for j in range(fh):
                for i in range(fw):
                    v = idx[j * fw + i]
                    if not (transparent and v == gce[2]):
                        screen[(y + j) * w + x + i] = v
            frame += ([palette[v] for v in screen],)
        frames.append(frame)
        gce = None
    return w, h, loops, frames


class Lzw(unittest.TestCase):
    def test_round_trip(self):
        rng = random.Random(3)
        cases = [bytes([5]), bytes(rng.randrange(256) for _ in range(20000)),      # many table resets
                 bytes(rng.randrange(3) for _ in range(30000)), bytes([7] * 50000 + [1] * 3 + [7] * 49999)]
        for data in cases:
            self.assertEqual(lzw_decode(draw.lzw(data), 8, len(data)), list(data))


class GifFile(unittest.TestCase):
    def test_frames_round_trip(self):
        rng = random.Random(5)
        w, h = 31, 17
        gif = draw.Gif(w, h, pinned=["#f7f8f5", "#2a78d6"])
        shown = []
        c = draw.Canvas(w, h, "#f7f8f5")
        for k in range(5):
            c = c.copy()
            c.disc(4 + 5 * k, 8, 3, "#2a78d6")
            for _ in range(10):
                i = rng.randrange(w * h)
                c.r[i], c.g[i], c.b[i] = rng.randrange(256), rng.randrange(256), rng.randrange(256)
            gif.add(c, 10 + k)
            if k == 2:
                gif.add(c.copy(), 7)                 # the same picture again: shown longer, not stored twice
            shown.append(c)
        with tempfile.TemporaryDirectory() as tmp:
            gif.write(Path(tmp) / "t.gif")
            width, height, loops, frames = read_gif((Path(tmp) / "t.gif").read_bytes())
        self.assertEqual((width, height, loops), (w, h, 0))
        self.assertEqual([f[4] for f in frames], [10, 11, 19, 13, 14])
        palette = gif.palette()
        for frame, canvas in zip(frames, shown):
            for i in range(w * h):
                want = (canvas.r[i], canvas.g[i], canvas.b[i])
                if want in palette:                  # pinned and frequent colours come back exactly
                    self.assertEqual(frame[5][i], want)
                else:                                # any other comes back as its nearest palette colour
                    self.assertEqual(frame[5][i], min(palette, key=lambda p: (2 * (p[0] - want[0]) ** 2 + 4 * (p[1] - want[1]) ** 2
                                                                              + 3 * (p[2] - want[2]) ** 2)))


class Drawing(unittest.TestCase):
    def test_field_draws_what_line_draws(self):
        pts = [(3.2, 4.1), (40.7, 9.9), (41.0, 30.5), (12.3, 28.0)]
        field = draw.Field(60, 40, [pts], 4.0)
        for width in (0.6, 1.0, 2.5, 7.9):
            line = draw.Mask(60, 40).line(pts, width)
            mask = field.mask(width)
            self.assertEqual(set(line), set(mask))
            for k in line:
                self.assertAlmostEqual(line[k], mask[k], places=9)

    def test_polygons_tile_without_seams(self):
        left = draw.Mask(20, 20).polygon([(2.3, 2.7), (9.6, 2.7), (9.6, 15.2), (2.3, 15.2)])
        right = draw.Mask(20, 20).polygon([(9.6, 2.7), (17.1, 2.7), (17.1, 15.2), (9.6, 15.2)])
        whole = draw.Mask(20, 20).polygon([(2.3, 2.7), (17.1, 2.7), (17.1, 15.2), (2.3, 15.2)])
        self.assertFalse(set(left) & set(right))
        self.assertEqual(set(left) | set(right), set(whole))

    def test_font(self):
        self.assertEqual(len({draw.FONT[d][0] for d in "0123456789"}), 1)       # counters do not jitter
        self.assertEqual(draw.unknown("Step 4 of 27 · 79.66 → 78.31 min (−0.061)"), [])
        c = draw.Canvas(200, 30)
        with self.assertRaises(ValueError):
            c.text(5, 20, "Bakı", 11, "#000000")                                 # no dotless i
        with self.assertRaises(ValueError):
            c.text(5, 20, "far too long a line for so small a picture", 11, "#000000")


class Buses(unittest.TestCase):
    def test_buses_keep_the_feeds_times(self):
        net, a = two_route_network(), Assumptions()
        runs = build.bus_runs(net, a, {1: (5.0, "zone"), 2: (12.0, "ridership")})
        self.assertEqual([r["counted"] for r in runs], [False, False, True, True])
        for r in runs:
            cycle, h = r["times"][-1], r["h"]
            on_road = [len(build.bus_positions(r, t)) for t in range(0, 7200, 7)]
            self.assertLessEqual(set(on_road), {math.floor(cycle / h), math.floor(cycle / h) + 1})
            self.assertAlmostEqual(statistics.mean(on_road), cycle / h, delta=0.03)
        r, p = runs[0], net.patterns[(1, 1)]
        for i, s in enumerate(p.stop_ids):                    # a bus is at each stop when the feed says
            positions = build.bus_positions(r, r["phase"] + 4 * r["h"] + r["times"][i])
            self.assertTrue(any(abs(lat - net.stops[s].lat) < 1e-9 and abs(lon - net.stops[s].lon) < 1e-9
                                for lat, lon in positions))


class Committed(unittest.TestCase):
    def test_gifs_are_whole_and_as_long_as_their_data(self):
        days = {d for v in load_daily_boardings(ROOT / "data" / "external" / "opendata" / "bakubus_passenger-2026.csv").values()
                for d in v}
        with open(ROOT / "output" / "redesign" / "changes.csv", newline="", encoding="utf-8-sig") as f:
            changes = len(list(csv.DictReader(f)))
        expected = {"buses.gif": 80, "riders.gif": len(days), "redesign.gif": 2 * changes + 2, "travel-time.gif": 121}
        m = build.Map()
        for name, frames in expected.items():
            data = (ROOT / "animations" / name).read_bytes()
            self.assertLess(len(data), 5e6, name)            # light enough for the top of the README
            w, h, loops, parts = read_gif(data, pixels=False)
            self.assertEqual((w, h, loops, len(parts)), (m.w, m.h, 0, frames), name)


if __name__ == "__main__":
    unittest.main()
