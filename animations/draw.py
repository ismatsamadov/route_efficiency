"""Pictures and animated GIFs with the standard library only.

A Canvas is an RGB raster. Everything drawn on it is anti-aliased: polylines of any width
with round ends and joins, discs, rectangles, and text in the small stroke font defined
below. A shape is first turned into a mask (pixel -> coverage from 0 to 1) and then painted
in one colour, so a line never darkens where its own pieces overlap, but two lines do.

Gif collects frames and writes them as an animated GIF: one palette of at most 255 colours
for the whole animation (median cut over the colours used, with the colours that must stay
exact pinned), and each frame stored as the rectangle of pixels that changed since the one
before, the unchanged ones transparent, so a still background costs almost nothing."""

import bisect
import math
import struct
import zlib
from collections import Counter


def rgb(colour):
    """(r, g, b) from "#rrggbb" or an (r, g, b) tuple."""
    if isinstance(colour, str):
        h = colour.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return tuple(colour)


def mix(a, b, t):
    """The colour t of the way from a to b, as "#rrggbb"."""
    a, b = rgb(a), rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


# ---------------------------------------------------------------- canvas and masks

class Canvas:
    def __init__(self, width, height, background="#ffffff"):
        self.w, self.h = width, height
        r, g, b = rgb(background)
        n = width * height
        self.r, self.g, self.b = bytearray([r]) * n, bytearray([g]) * n, bytearray([b]) * n

    def copy(self):
        c = Canvas.__new__(Canvas)
        c.w, c.h = self.w, self.h
        c.r, c.g, c.b = bytearray(self.r), bytearray(self.g), bytearray(self.b)
        return c

    def mask(self):
        return Mask(self.w, self.h)

    def paint(self, mask, colour, opacity=1.0):
        """Cover the canvas with colour as far as the mask says, times opacity."""
        cr, cg, cb = rgb(colour)
        R, G, B = self.r, self.g, self.b
        for i, c in mask.items():
            a = c * opacity
            if a >= 0.998:
                R[i], G[i], B[i] = cr, cg, cb
            elif a > 0.002:
                R[i] = int(R[i] + (cr - R[i]) * a + 0.5)
                G[i] = int(G[i] + (cg - G[i]) * a + 0.5)
                B[i] = int(B[i] + (cb - B[i]) * a + 0.5)

    def line(self, points, width, colour, opacity=1.0):
        self.paint(self.mask().line(points, width), colour, opacity)

    def disc(self, x, y, radius, colour, opacity=1.0):
        self.paint(self.mask().disc(x, y, radius), colour, opacity)

    def rect(self, x0, y0, x1, y1, colour, opacity=1.0):
        self.paint(self.mask().rect(x0, y0, x1, y1), colour, opacity)

    def text(self, x, y, s, size, colour, weight=1.3, halo=None, halo_width=2.5, align="left"):
        """Text with its baseline at y, starting at x (or ending at x, or centred on it).
        size is the height of a capital in pixels; weight is the stroke in tenths of it.
        halo paints a wider stroke of that colour underneath, to keep text legible on a map."""
        width = text_width(s, size)
        if align != "left":
            x -= width * (1.0 if align == "right" else 0.5)
        if x < 0 or x + width > self.w:
            raise ValueError(f"{s!r} runs off the canvas")
        if halo:
            self.paint(self.mask().text(x, y, s, size, weight, extra=halo_width), halo)
        self.paint(self.mask().text(x, y, s, size, weight), colour)

    def pixels(self):
        """The three channels joined, R then G then B."""
        return bytes(self.r) + bytes(self.g) + bytes(self.b)


class Mask(dict):
    """Pixel index -> coverage from 0 to 1. Shapes added to a mask keep the larger coverage."""

    def __init__(self, width, height):
        super().__init__()
        self.w, self.h = width, height

    def _put(self, k, c):
        if c > 1.0:
            c = 1.0
        if c > self.get(k, 0.0):
            self[k] = c

    def segment(self, ax, ay, bx, by, r):
        """A segment of half-width r with round ends. Coverage is r + 0.5 minus the
        distance from the pixel's centre to the segment, kept between 0 and 1."""
        R = r + 0.5
        get = self.get
        for k, d in _near_segment(self.w, self.h, ax, ay, bx, by, R):
            c = R - d
            if c > 1.0:
                c = 1.0
            if c > get(k, 0.0):
                self[k] = c
        return self

    def line(self, points, width):
        """A polyline of the given width; a single point makes a dot."""
        r = width / 2
        if len(points) == 1:
            return self.disc(points[0][0], points[0][1], r)
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            self.segment(ax, ay, bx, by, r)
        return self

    def disc(self, cx, cy, r):
        W, H = self.w, self.h
        R = r + 0.5
        for y in range(max(0, int(math.floor(cy - R))), min(H - 1, int(math.ceil(cy + R))) + 1):
            dy = y + 0.5 - cy
            t = R * R - dy * dy
            if t < 0:
                continue
            s = math.sqrt(t)
            base = y * W
            for x in range(max(0, int(math.floor(cx - s))), min(W - 1, int(math.ceil(cx + s))) + 1):
                dx = x + 0.5 - cx
                c = R - math.sqrt(dx * dx + dy * dy)
                if c > 0.0:
                    self._put(base + x, c)
        return self

    def rect(self, x0, y0, x1, y1):
        """Whole pixels from (x0, y0) up to, not including, (x1, y1)."""
        for y in range(max(0, int(y0)), min(self.h, int(y1))):
            base = y * self.w
            for x in range(max(0, int(x0)), min(self.w, int(x1))):
                self[base + x] = 1.0
        return self

    def polygon(self, points):
        """The pixels whose centres lie inside a polygon (even-odd rule), without smoothing:
        polygons that share edges, like a hexagon grid, then tile without seams."""
        ys = [y for _, y in points]
        n = len(points)
        for y in range(max(0, int(math.floor(min(ys)))), min(self.h - 1, int(math.ceil(max(ys)))) + 1):
            yc = y + 0.5
            xs = []
            for k in range(n):
                (ax, ay), (bx, by) = points[k], points[(k + 1) % n]
                if (ay <= yc < by) or (by <= yc < ay):
                    xs.append(ax + (yc - ay) * (bx - ax) / (by - ay))
            xs.sort()
            base = y * self.w
            for x0, x1 in zip(xs[0::2], xs[1::2]):
                for x in range(max(0, int(math.ceil(x0 - 0.5))), min(self.w, int(math.ceil(x1 - 0.5)))):
                    self[base + x] = 1.0
        return self

    def text(self, x, y, s, size, weight=1.3, extra=0.0):
        _drawable(s)
        unit = size / 10
        stroke = max(1.0, weight * unit) + extra
        pen = x
        for ch in s:
            adv, strokes = FONT[ch]
            for st in strokes:
                self.line([(pen + gx * unit, y - gy * unit) for gx, gy in st], stroke)
            pen += (adv + TRACKING) * unit
        return self


def _near_segment(W, H, ax, ay, bx, by, R):
    """(pixel, distance) for every pixel whose centre lies within R of the segment from
    (ax, ay) to (bx, by). Each row is searched only across the hull of the segment's two end
    discs and the band between them, so long diagonal segments cost no more than their area."""
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    L = math.sqrt(L2)
    sqrt = math.sqrt
    for y in range(max(0, int(math.floor(min(ay, by) - R))), min(H - 1, int(math.ceil(max(ay, by) + R))) + 1):
        yc = y + 0.5
        lo, hi = math.inf, -math.inf
        for px, py in ((ax, ay), (bx, by)):              # the two round ends
            t = R * R - (yc - py) * (yc - py)
            if t >= 0:
                s = sqrt(t)
                lo, hi = min(lo, px - s), max(hi, px + s)
        if L2 > 0:                                       # the band along the segment
            if dy != 0:
                xc = ax + (yc - ay) * dx / dy
                half = R * L / abs(dy)
                blo, bhi = xc - half, xc + half
                if dx != 0:                              # between the two ends
                    e0 = ax - (yc - ay) * dy / dx
                    e1 = ax + (L2 - (yc - ay) * dy) / dx
                    blo, bhi = max(blo, min(e0, e1)), min(bhi, max(e0, e1))
                elif not 0 <= (yc - ay) / dy <= 1:
                    blo, bhi = math.inf, -math.inf
            elif abs(yc - ay) <= R:
                blo, bhi = min(ax, bx), max(ax, bx)
            else:
                blo, bhi = math.inf, -math.inf
            if blo <= bhi:
                lo, hi = min(lo, blo), max(hi, bhi)
        if lo > hi:
            continue
        base = y * W
        py = yc - ay
        for x in range(max(0, int(math.floor(lo))), min(W - 1, int(math.ceil(hi))) + 1):
            px = x + 0.5 - ax
            if L2:
                t = (px * dx + py * dy) / L2
                t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
                ex, ey = px - t * dx, py - t * dy
            else:
                ex, ey = px, py
            d = sqrt(ex * ex + ey * ey)
            if d < R:
                yield base + x, d


class Field:
    """The pixels near some polylines with their distance to the nearest, for drawing the
    same lines at many widths: mask(width) is what Mask.line gives, up to a width of
    2 x radius, at the cost of the pixels covered."""

    def __init__(self, width, height, lines, radius):
        self.w, self.h = width, height
        R = radius + 0.5
        near = {}
        for pts in lines:
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                for k, d in _near_segment(width, height, ax, ay, bx, by, R):
                    if d < near.get(k, R):
                        near[k] = d
        self.items = sorted((d, k) for k, d in near.items())
        self.dist = [d for d, _ in self.items]

    def mask(self, width):
        R = width / 2 + 0.5
        m = Mask(self.w, self.h)
        for d, k in self.items[:bisect.bisect_left(self.dist, R)]:
            m[k] = 1.0 if R - d > 1.0 else R - d
        return m


# ---------------------------------------------------------------- the stroke font

def _arc(cx, cy, rx, ry, a0, a1, step=12):
    """Points on an ellipse from angle a0 to a1 in degrees (0 = east, 90 = up)."""
    n = max(2, int(abs(a1 - a0) / step) + 1)
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * k / (n - 1))),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * k / (n - 1)))) for k in range(n)]


def _font():
    """{character: (width, strokes)} in units where a capital is 10 high and the baseline is
    at 0; each stroke is a list of points, and a stroke of one point is a dot. Digits share
    one width, so counters do not jitter."""
    o = _arc(3.5, 3.5, 3, 3.5, 0, 360)                     # the round lowercase bowl
    P = [[(0.7, 0), (0.7, 10), (4.2, 10)] + _arc(4.2, 7.3, 2.7, 2.7, 90, -90) + [(0.7, 4.6)]]
    f = {
        " ": (3.2, []),
        "a": (7, [o, [(6.5, 7), (6.5, 0)]]),
        "b": (7, [[(0.5, 10), (0.5, 0)], o]),
        "c": (6.2, [_arc(3.5, 3.5, 3, 3.5, 45, 315)]),
        "d": (7, [o, [(6.5, 10), (6.5, 0)]]),
        "e": (7, [[(0.5, 3.5)] + _arc(3.5, 3.5, 3, 3.5, 0, 318)]),
        "f": (5, [_arc(4.4, 8.3, 1.7, 1.7, 30, 180) + [(2.7, 0)], [(0.7, 7), (4.8, 7)]]),
        "g": (7, [o, [(6.5, 7), (6.5, -0.5)] + _arc(3.5, -0.5, 3, 2.5, 0, -150)]),
        "h": (7, [[(0.5, 10), (0.5, 0)], [(0.5, 4)] + _arc(3.5, 4, 3, 3, 180, 0) + [(6.5, 0)]]),
        "i": (2, [[(1, 7), (1, 0)], [(1, 9.3)]]),
        "j": (3, [[(2.1, 7), (2.1, -1.2)] + _arc(0.6, -1.2, 1.5, 1.8, 0, -140), [(2.1, 9.3)]]),
        "k": (6.3, [[(0.5, 10), (0.5, 0)], [(5.8, 7), (0.5, 2.4)], [(2.4, 4.1), (6.2, 0)]]),
        "l": (2, [[(1, 10), (1, 0)]]),
        "m": (9.4, [[(0.5, 7), (0.5, 0)], [(0.5, 4.5)] + _arc(2.6, 4.5, 2.1, 2.5, 180, 0) + [(4.7, 0)],
                    [(4.7, 4.5)] + _arc(6.8, 4.5, 2.1, 2.5, 180, 0) + [(8.9, 0)]]),
        "n": (7, [[(0.5, 7), (0.5, 0)], [(0.5, 4)] + _arc(3.5, 4, 3, 3, 180, 0) + [(6.5, 0)]]),
        "o": (7, [o]),
        "p": (7, [[(0.5, 7), (0.5, -3)], o]),
        "q": (7, [o, [(6.5, 7), (6.5, -3)]]),
        "r": (4.5, [[(0.5, 7), (0.5, 0)], [(0.5, 4)] + _arc(3.2, 4, 2.7, 3, 180, 70)]),
        "s": (6, [_arc(3, 5.25, 2.5, 1.75, 20, 270) + _arc(3, 1.75, 2.7, 1.75, 90, -160)]),
        "t": (4.6, [[(1.8, 9.3), (1.8, 1.6)] + _arc(3.4, 1.6, 1.6, 1.6, 180, 290), [(0.3, 7), (4.2, 7)]]),
        "u": (7, [[(0.5, 7), (0.5, 3)] + _arc(3.5, 3, 3, 3, 180, 360) + [(6.5, 7)], [(6.5, 7), (6.5, 0)]]),
        "v": (6, [[(0, 7), (3, 0), (6, 7)]]),
        "w": (9, [[(0, 7), (2.2, 0), (4.5, 7), (6.8, 0), (9, 7)]]),
        "x": (6.2, [[(0.3, 7), (5.9, 0)], [(5.9, 7), (0.3, 0)]]),
        "y": (6.2, [[(0, 7), (3.1, 0)], [(6.2, 7), (2, -3)]]),
        "z": (6.3, [[(0.5, 7), (5.8, 7), (0.5, 0), (5.8, 0)]]),
        "A": (7.2, [[(0, 0), (3.6, 10), (7.2, 0)], [(1.3, 3.4), (5.9, 3.4)]]),
        "B": (7.6, [[(0.7, 0), (0.7, 10), (4.2, 10)] + _arc(4.2, 7.6, 2.4, 2.4, 90, -90) + [(0.7, 5.2)],
                    [(4.2, 5.2)] + _arc(4.4, 2.6, 2.6, 2.6, 90, -90) + [(0.7, 0)]]),
        "C": (7.6, [_arc(4.4, 5, 4, 5, 40, 320)]),
        "D": (8, [[(0.7, 0), (0.7, 10), (3.2, 10)] + _arc(3.2, 5, 4.2, 5, 90, -90) + [(0.7, 0)]]),
        "E": (6.6, [[(6.2, 10), (0.7, 10), (0.7, 0), (6.2, 0)], [(0.7, 5.1), (5.4, 5.1)]]),
        "F": (6.4, [[(6.2, 10), (0.7, 10), (0.7, 0)], [(0.7, 5.1), (5.4, 5.1)]]),
        "G": (8.6, [_arc(4.4, 5, 4, 5, 40, 355) + [(8.4, 4.4), (5.2, 4.4)]]),
        "H": (8, [[(0.7, 0), (0.7, 10)], [(7.3, 0), (7.3, 10)], [(0.7, 5.1), (7.3, 5.1)]]),
        "I": (2, [[(1, 0), (1, 10)]]),
        "J": (5.6, [[(5, 10), (5, 3)] + _arc(2.75, 3, 2.25, 3, 0, -180)]),
        "K": (7.2, [[(0.7, 0), (0.7, 10)], [(6.8, 10), (0.7, 3.6)], [(2.7, 5.7), (7, 0)]]),
        "L": (6.2, [[(0.7, 10), (0.7, 0), (6, 0)]]),
        "M": (9.2, [[(0.7, 0), (0.7, 10), (4.6, 0.6), (8.5, 10), (8.5, 0)]]),
        "N": (8, [[(0.7, 0), (0.7, 10), (7.3, 0), (7.3, 10)]]),
        "O": (9, [_arc(4.5, 5, 4, 5, 0, 360)]),
        "P": (7.2, P),
        "Q": (9, [_arc(4.5, 5, 4, 5, 0, 360), [(5.6, 2.4), (8.6, -0.6)]]),
        "R": (7.4, P + [[(3.8, 4.6), (7, 0)]]),
        "S": (7.2, [_arc(3.7, 7.5, 3, 2.5, 25, 270) + _arc(3.7, 2.5, 3.2, 2.5, 90, -155)]),
        "T": (7, [[(0, 10), (7, 10)], [(3.5, 10), (3.5, 0)]]),
        "U": (8, [[(0.7, 10), (0.7, 3.6)] + _arc(4, 3.6, 3.3, 3.6, 180, 360) + [(7.3, 10)]]),
        "V": (7.4, [[(0, 10), (3.7, 0), (7.4, 10)]]),
        "W": (10.4, [[(0, 10), (2.6, 0), (5.2, 10), (7.8, 0), (10.4, 10)]]),
        "X": (7.3, [[(0.3, 10), (7, 0)], [(7, 10), (0.3, 0)]]),
        "Y": (7.2, [[(0, 10), (3.6, 5), (7.2, 10)], [(3.6, 5), (3.6, 0)]]),
        "Z": (7.6, [[(0.6, 10), (7, 10), (0.6, 0), (7, 0)]]),
        "0": (7.2, [_arc(3.6, 5, 3, 5, 0, 360)]),
        "1": (7.2, [[(1.6, 8), (4.2, 10), (4.2, 0)]]),
        "2": (7.2, [_arc(3.6, 7, 2.9, 3, 160, -25) + [(0.7, 0), (6.6, 0)]]),
        "3": (7.2, [_arc(3.5, 7.65, 2.7, 2.35, 150, -90) + _arc(3.5, 2.65, 3, 2.65, 90, -150)]),
        "4": (7.2, [[(5.2, 0), (5.2, 10), (0.4, 3), (6.9, 3)]]),
        "5": (7.2, [[(6.2, 10), (1.2, 10), (0.9, 5.4)] + _arc(3.6, 3.3, 2.9, 3.3, 145, -155)]),
        "6": (7.2, [_arc(3.6, 3.2, 3, 3.2, 0, 360), [(0.6, 3.2)] + _arc(4, 5, 3.4, 5, 180, 62)]),
        "7": (7.2, [[(0.5, 10), (6.7, 10), (2.4, 0)]]),
        "8": (7.2, [_arc(3.6, 7.6, 2.6, 2.4, 0, 360), _arc(3.6, 2.65, 3, 2.65, 0, 360)]),
        "9": (7.2, [_arc(3.6, 6.8, 3, 3.2, 0, 360), [(6.6, 6.8)] + _arc(3.2, 5, 3.4, 5, 0, -118)]),
        ".": (1.8, [[(0.9, 0.6)]]),
        ",": (1.8, [[(0.9, 0.6)], [(1.1, 0.6), (0.3, -1.6)]]),
        ":": (1.8, [[(0.9, 0.6)], [(0.9, 6.2)]]),
        ";": (1.8, [[(0.9, 6.2)], [(0.9, 0.6)], [(1.1, 0.6), (0.3, -1.6)]]),
        "-": (4.4, [[(0.5, 3.8), (3.9, 3.8)]]),
        "–": (7, [[(0.3, 3.8), (6.7, 3.8)]]),
        "−": (7.2, [[(0.6, 5), (6.6, 5)]]),
        "+": (7.2, [[(0.6, 5), (6.6, 5)], [(3.6, 2), (3.6, 8)]]),
        "/": (4.2, [[(0, -0.5), (4.2, 10.5)]]),
        "(": (3.2, [_arc(4.6, 4, 3.6, 7, 120, 240)]),
        ")": (3.2, [_arc(-1.4, 4, 3.6, 7, 60, -60)]),
        "%": (9, [_arc(2, 8, 1.6, 1.9, 0, 360), _arc(7, 2, 1.6, 1.9, 0, 360), [(7.4, 10), (1.6, 0)]]),
        "'": (1.8, [[(0.9, 10), (0.9, 7.2)]]),
        "’": (1.8, [[(1.1, 10), (0.6, 7.2)]]),
        "·": (2.2, [[(1.1, 4.6)]]),
        "→": (9.4, [[(0.5, 4.6), (8.5, 4.6)], [(5.6, 7.2), (8.5, 4.6), (5.6, 2)]]),
        "×": (6.6, [[(1, 2.2), (5.6, 6.8)], [(5.6, 2.2), (1, 6.8)]]),
        "!": (2, [[(1, 10), (1, 3)], [(1, 0.6)]]),
        "?": (6, [_arc(3.2, 7.4, 2.6, 2.6, 160, -60) + [(3.2, 3)], [(3.2, 0.6)]]),
    }
    return f


FONT = _font()
TRACKING = 1.7                                             # space between letters, in font units


def unknown(s):
    """The characters of s that the font has no glyph for."""
    return sorted(set(s) - set(FONT))


def _drawable(s):
    missing = unknown(s)
    if missing:
        raise ValueError(f"the font cannot draw {''.join(missing)!r} in {s!r}")


def text_width(s, size):
    _drawable(s)
    unit = size / 10
    return sum(FONT[ch][0] + TRACKING for ch in s) * unit - TRACKING * unit


# ---------------------------------------------------------------- GIF

def lzw(indices, min_size=8):
    """GIF's variable-length LZW code for a sequence of palette indices, as bytes."""
    clear, end = 1 << min_size, (1 << min_size) + 1
    size, nxt, table = min_size + 1, end + 1, {}
    out = bytearray()
    acc, nacc = clear, size                              # start with a clear code
    it = iter(indices)
    prefix = next(it)
    for px in it:
        key = (prefix << 8) | px
        code = table.get(key)
        if code is not None:
            prefix = code
            continue
        acc |= prefix << nacc
        nacc += size
        while nacc >= 8:
            out.append(acc & 255)
            acc >>= 8
            nacc -= 8
        if nxt == 4096:                                  # table full: start again
            acc |= clear << nacc
            nacc += size
            while nacc >= 8:
                out.append(acc & 255)
                acc >>= 8
                nacc -= 8
            size, nxt, table = min_size + 1, end + 1, {}
        else:
            if nxt >= 1 << size:
                size += 1
            table[key] = nxt
            nxt += 1
        prefix = px
    for code in (prefix, end):
        acc |= code << nacc
        nacc += size
        while nacc >= 8:
            out.append(acc & 255)
            acc >>= 8
            nacc -= 8
    if nacc:
        out.append(acc & 255)
    return bytes(out)


def _median_cut(counts, n):
    """Up to n colours standing for {packed 0xrrggbb: pixels}: the box of colours with the
    widest spread (weighted by the square root of its pixels) is split at its median until
    there are n boxes; each box gives its pixel-weighted mean."""
    def spread(box):
        best = (-1, 16)
        for shift in (16, 8, 0):
            vals = [(c >> shift) & 255 for c, _ in box]
            best = max(best, (max(vals) - min(vals), shift))
        return best

    boxes = [list(counts.items())]
    while len(boxes) < n:
        scored = []
        for i, box in enumerate(boxes):
            if len(box) > 1:
                rng, shift = spread(box)
                if rng > 0:
                    scored.append((rng * math.sqrt(sum(w for _, w in box)), i, shift))
        if not scored:
            break
        _, i, shift = max(scored)
        box = sorted(boxes.pop(i), key=lambda cw: (cw[0] >> shift) & 255)
        half, acc, cut = sum(w for _, w in box) / 2, 0, 1
        for k, (_, w) in enumerate(box):
            acc += w
            if acc >= half:
                cut = min(max(k + 1, 1), len(box) - 1)
                break
        boxes += [box[:cut], box[cut:]]
    out = []
    for box in boxes:
        total = sum(w for _, w in box)
        out.append(tuple(round(sum(((c >> s) & 255) * w for c, w in box) / total) for s in (16, 8, 0)))
    return out


class _Nearest(dict):
    """Packed colour -> index of the nearest palette colour, computed once per colour."""

    def __init__(self, palette):
        super().__init__()
        self.palette = palette

    def __missing__(self, key):
        r, g, b = key >> 16, (key >> 8) & 255, key & 255
        best, index = None, 0
        for i, (pr, pg, pb) in enumerate(self.palette):
            d = 2 * (r - pr) ** 2 + 4 * (g - pg) ** 2 + 3 * (b - pb) ** 2
            if best is None or d < best:
                best, index = d, i
        self[key] = index
        return index


def _first_diff(a, b):
    """Index of the first position where two equal-length byte strings differ."""
    lo, hi = 0, len(a)
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if a[lo:mid] != b[lo:mid]:
            hi = mid
        else:
            lo = mid
    return lo


class Gif:
    """An animation. add() each frame with its delay; write() makes the palette and the file."""

    TRANSPARENT = 255

    def __init__(self, width, height, pinned=(), colours=255):
        self.w, self.h = width, height
        self.pinned = [rgb(c) for c in pinned]
        self.colours = min(255, colours)
        self.frames = []                                 # [compressed channels, delay in 1/100 s]
        self.counts = Counter()
        self.last = None

    def add(self, canvas, delay_cs):
        raw = canvas.pixels()
        if raw == self.last:                             # the same picture: show the last one longer
            self.frames[-1][1] += delay_cs
            return
        stride = 1 if not self.frames else 3             # the first frame fully, then a sample
        self.counts.update([(r << 16) | (g << 8) | b
                            for r, g, b in zip(canvas.r[::stride], canvas.g[::stride], canvas.b[::stride])])
        self.frames.append([zlib.compress(raw, 1), delay_cs])
        self.last = raw

    def palette(self):
        pinned = list(dict.fromkeys(self.pinned))
        counts = Counter({c: n for c, n in self.counts.items()
                          if (c >> 16, (c >> 8) & 255, c & 255) not in pinned})
        return pinned + _median_cut(counts, self.colours - len(pinned)) if counts else pinned

    def write(self, path):
        w, h, n = self.w, self.h, self.w * self.h
        pal = self.palette()
        nearest = _Nearest(pal)
        table = b"".join(bytes(c) for c in pal) + b"\0\0\0" * (256 - len(pal))
        out = bytearray(b"GIF89a" + struct.pack("<HHBBB", w, h, 0xF7, 0, 0) + table)
        out += b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"           # loop for ever
        T = self.TRANSPARENT
        records, prev = [], None
        for blob, delay in self.frames:
            raw = zlib.decompress(blob)
            idx = bytes([nearest[(r << 16) | (g << 8) | b]
                         for r, g, b in zip(raw[:n], raw[n:2 * n], raw[2 * n:])])
            if prev is None:
                records.append([0, 0, w, h, idx, delay, False])
                prev = idx
                continue
            rows = [y for y in range(h) if idx[y * w:(y + 1) * w] != prev[y * w:(y + 1) * w]]
            if not rows:
                records[-1][5] += delay
                continue
            x0, x1 = w, 0
            for y in rows:
                a, b = idx[y * w:(y + 1) * w], prev[y * w:(y + 1) * w]
                x0 = min(x0, _first_diff(a, b))
                x1 = max(x1, w - _first_diff(a[::-1], b[::-1]))
            y0, y1 = rows[0], rows[-1] + 1
            data = bytearray()
            for y in range(y0, y1):
                cur, old = idx[y * w + x0:y * w + x1], prev[y * w + x0:y * w + x1]
                data += bytes([c if c != o else T for c, o in zip(cur, old)])
            records.append([x0, y0, x1 - x0, y1 - y0, bytes(data), delay, True])
            prev = idx
        for x, y, fw, fh, data, delay, transparent in records:
            out += struct.pack("<BBBBHBB", 0x21, 0xF9, 4, (1 << 2) | int(transparent), delay, T, 0)
            out += b"\x2c" + struct.pack("<HHHHB", x, y, fw, fh, 0) + b"\x08"
            code = lzw(data)
            for k in range(0, len(code), 255):
                chunk = code[k:k + 255]
                out += bytes([len(chunk)]) + chunk
            out += b"\x00"
        out += b"\x3b"
        with open(path, "wb") as f:
            f.write(out)
        return len(out)
