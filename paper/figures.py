#!/usr/bin/env python3
"""Draw the manuscript's figures as SVG from the committed data and outputs.

  python3 paper/figures.py              # writes paper/figures/figure-1.svg ... figure-4.svg

Figure 1  today's network, every route direction coloured by the route's shape class
Figure 2  the trunk corridors where eight or more routes share every link, width by routes per link
Figure 3  the redesign: kept, straightened, and dropped or merged route directions
Figure 4  the gain of the redesign on ten trip samples and under the alternative settings

Standard library only, like the rest of the repository. The maps use the same flat
projection as the measurements (busnet.geo.PROJ) and the repaired geometry the
measurements use, so they show exactly what was measured. Convert to PDF or EPS for a
journal with any SVG-capable tool (a browser's print dialog, Inkscape, rsvg-convert).
"""
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from busnet.geo import PROJ, haversine_m        # noqa: E402
from busnet.inputs import load_inputs           # noqa: E402

OUT = ROOT / "paper" / "figures"
FONT = "Helvetica, Arial, sans-serif"
INK, INK2, MUTED, HAIR = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
GREY_LINE = "#c3c2b7"                            # recessive context lines
BLUE, ORANGE = "#2a78d6", "#eb6834"              # the two categorical colours
SHAPE_STEPS = [("direct", "#86b6ef"), ("indirect", "#3987e5"),      # one hue, light to dark:
               ("very indirect", "#1c5cab"), ("loop", "#0d366b")]    # the classes are ordered


# ---------------------------------------------------------------- SVG helpers

def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=14, fill=INK, anchor="start", weight="normal", baseline="auto"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" dominant-baseline="{baseline}">{esc(s)}</text>')


def svg(width, height, parts, pad=0):
    body = "\n".join(parts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="{-pad} {-pad} {width} {height}" font-family="{FONT}">\n'
            f'<rect x="{-pad}" y="{-pad}" width="{width}" height="{height}" fill="#ffffff"/>\n{body}\n</svg>\n')


# The maps show the city and the Absheron peninsula; the few intercity routes that leave
# this box (to the south-west and the far east) run off its edge.
CROP = (40.27, 40.62, 49.58, 50.36)                  # lat0, lat1, lon0, lon1


class Map:
    """A map in the measurements' flat projection; drawing coordinates in SVG pixels."""

    def __init__(self, bbox=CROP, width=1000, margin=24):
        lat0, lat1, lon0, lon1 = bbox
        self.x0, self.y0 = PROJ.to_xy(lat0, lon0)
        self.x1, self.y1 = PROJ.to_xy(lat1, lon1)
        self.margin = margin
        self.scale = (width - 2 * margin) / (self.x1 - self.x0)      # pixels per metre
        self.width = width
        self.height = round((self.y1 - self.y0) * self.scale + 2 * margin)
        self.parts = [f'<clipPath id="map"><rect x="{margin}" y="{margin}" width="{width - 2 * margin}" '
                      f'height="{self.height - 2 * margin}"/></clipPath>', '<g clip-path="url(#map)">']
        self.clipped = True

    def end_clip(self):
        if self.clipped:
            self.parts.append('</g>')
            self.clipped = False

    def px(self, lat, lon):
        x, y = PROJ.to_xy(lat, lon)
        return self.margin + (x - self.x0) * self.scale, self.margin + (self.y1 - y) * self.scale

    def polyline(self, latlons, stroke, width, opacity=1.0):
        pts, last = [], None
        for lat, lon in latlons:
            p = self.px(lat, lon)
            if last is None or abs(p[0] - last[0]) + abs(p[1] - last[1]) >= 0.7:   # drop sub-pixel steps
                pts.append(f"{p[0]:.1f},{p[1]:.1f}")
                last = p
        if len(pts) < 2:
            return
        self.parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{stroke}" '
                          f'stroke-width="{width}" stroke-opacity="{opacity}" stroke-linejoin="round" stroke-linecap="round"/>')

    def circle(self, lat, lon, r_m, fill, opacity):
        x, y = self.px(lat, lon)
        self.parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r_m * self.scale:.1f}" fill="{fill}" fill-opacity="{opacity:.3f}"/>')

    def legend(self, entries, x=None, y=None, title=None, line_height=22):
        """entries: (label, colour, stroke width) — a line swatch beside each label."""
        self.end_clip()
        rows = len(entries) + (1 if title else 0)
        w = 12 + 36 + 8 + max(len(e[0]) for e in entries + [(title or "",)]) * 7.2 + 12
        h = rows * line_height + 10
        x = self.width - self.margin - 6 - w if x is None else x          # bottom-right corner
        y = self.height - self.margin - 6 - h if y is None else y
        self.parts.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h}" '
                          f'fill="#ffffff" fill-opacity="0.92" stroke="{HAIR}"/>')
        cy = y + 8
        if title:
            self.parts.append(text(x + 12, cy + 12, title, 14, INK, weight="bold"))
            cy += line_height
        for label, colour, width in entries:
            self.parts.append(f'<line x1="{x + 12}" y1="{cy + 10}" x2="{x + 48}" y2="{cy + 10}" stroke="{colour}" '
                              f'stroke-width="{width}" stroke-linecap="round"/>')
            self.parts.append(text(x + 56, cy + 15, label, 14, INK))
            cy += line_height

    def scale_bar(self, km=10):
        self.end_clip()
        length = km * 1000 * self.scale
        x0, y = self.margin + 12, self.height - self.margin - 12                   # bottom-left corner
        x1 = x0 + length
        self.parts.append(f'<line x1="{x0:.1f}" y1="{y}" x2="{x1:.1f}" y2="{y}" stroke="{INK}" stroke-width="2"/>')
        for x in (x0, x1):
            self.parts.append(f'<line x1="{x:.1f}" y1="{y - 5}" x2="{x:.1f}" y2="{y + 5}" stroke="{INK}" stroke-width="2"/>')
        self.parts.append(text((x0 + x1) / 2, y - 8, f"{km} km", 13, INK2, anchor="middle"))

    def label(self, lat, lon, s, dx=12, dy=-12, anchor="start"):
        """A direct label with a short leader line."""
        x, y = self.px(lat, lon)
        self.parts.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + dx:.1f}" y2="{y + dy:.1f}" stroke="{INK2}" stroke-width="1"/>')
        self.parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{INK}"/>')
        self.parts.append(text(x + dx + (4 if anchor == "start" else -4), y + dy + 4, s, 13, INK, anchor=anchor))

    def render(self):
        self.end_clip()
        self.parts.append(f'<rect x="{self.margin}" y="{self.margin}" width="{self.width - 2 * self.margin}" '
                          f'height="{self.height - 2 * self.margin}" fill="none" stroke="{HAIR}"/>')
        return svg(self.width, self.height, self.parts)


# ---------------------------------------------------------------- data

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def population_layer(m, zones, radius_m=480):
    """Hexagon centroids as grey discs, darker where more people live."""
    top = max(p for _, _, p in zones)
    for lat, lon, people in sorted(zones, key=lambda z: z[2]):
        if people <= 0:
            continue
        m.circle(lat, lon, radius_m, INK, 0.03 + 0.22 * math.sqrt(people / top))


def cumulative(path):
    out = [0.0]
    for (a1, b1), (a2, b2) in zip(path, path[1:]):
        out.append(out[-1] + haversine_m(a1, b1, a2, b2))
    return out


def slice_path(pattern, c0, c1):
    """The part of a pattern's path between two distances along it."""
    path, cum = pattern.path, cumulative(pattern.path)
    out = []
    for i, c in enumerate(cum):
        if c0 <= c <= c1:
            out.append(path[i])
    for c in (c0, c1):                                 # interpolate the exact ends
        for i in range(1, len(cum)):
            if cum[i - 1] <= c <= cum[i] and cum[i] > cum[i - 1]:
                t = (c - cum[i - 1]) / (cum[i] - cum[i - 1])
                pt = (path[i - 1][0] + t * (path[i][0] - path[i - 1][0]),
                      path[i - 1][1] + t * (path[i][1] - path[i - 1][1]))
                out.insert(0, pt) if c == c0 else out.append(pt)
                break
    return out


def corridor_path(net, numbers, stop_ids):
    """The street path of one member route between the corridor's first and last stop."""
    by_number = {r.number: rid for rid, r in net.routes.items()}
    for number in numbers:
        rid = by_number.get(number)
        if rid is None:
            continue
        for p in net.patterns_of(rid):
            ids = p.stop_ids
            if stop_ids[0] in ids and stop_ids[-1] in ids:
                i, j = ids.index(stop_ids[0]), ids.index(stop_ids[-1])
                if i < j and ids[i:j + 1] == stop_ids:
                    return slice_path(p, p.chainage_m[i], p.chainage_m[j])
    return [(net.stops[s].lat, net.stops[s].lon) for s in stop_ids]      # straight lines as a fallback


# ---------------------------------------------------------------- figures

def figure_1(net, zones, routes_csv):
    shape_of = {r["route"]: r["shape"] for r in routes_csv}
    counts = {k: sum(1 for v in shape_of.values() if v == k) for k, _ in SHAPE_STEPS}
    m = Map()
    population_layer(m, zones)
    for cls, colour in SHAPE_STEPS:                    # least direct drawn last, on top
        for (rid, _), p in sorted(net.patterns.items()):
            if shape_of.get(net.number(rid)) == cls:
                m.polyline(p.path, colour, 1.3)
    m.legend([(f"{cls.capitalize()} ({counts[cls]} routes)", colour, 3) for cls, colour in SHAPE_STEPS]
             + [("Residents per hexagon (darker: more)", "#9a9a98", 8)],
             title="Shape class of the route")
    m.scale_bar()
    return m.render()


def figure_2(net, corridors):
    m = Map()
    for p in net.patterns.values():
        m.polyline(p.path, GREY_LINE, 0.8)
    def width(mean):
        return 1.5 + 0.35 * (float(mean) - 8)          # 8 routes per link: 1.5 px; 16: 4.3 px
    rows = sorted(corridors, key=lambda r: float(r["mean_routes_per_link"]))
    for r in rows:
        path = corridor_path(net, r["routes"].split(), [int(s) for s in r["stop_ids"].split()])
        m.polyline(path, BLUE, width(r["mean_routes_per_link"]))
    m.end_clip()
    longest = max(corridors, key=lambda r: float(r["km"]))
    busiest = max(corridors, key=lambda r: int(r["max_routes_on_a_link"]))
    for r, tag, dx, dy in ((longest, "Longest", 60, -40), (busiest, "Busiest", 60, 70)):
        ids = [int(s) for s in r["stop_ids"].split()]
        mid = net.stops[ids[len(ids) // 2]]
        m.label(mid.lat, mid.lon, f"{tag} corridor: {float(r['km']):.1f} km, {len(r['routes'].split())} routes", dx, dy)
    m.legend([("8 routes per link", BLUE, width(8)), ("12 routes per link", BLUE, width(12)),
              ("16 routes per link", BLUE, width(16)), ("Other links", GREY_LINE, 1)],
             title=f"{len(corridors)} trunk corridors, {sum(float(r['km']) for r in corridors):.0f} km")
    m.scale_bar()
    return m.render()


def figure_3(net, geojson):
    m = Map()
    feats = geojson["features"]
    order = {"kept": 0, "straightened": 1, "dropped": 2}
    style = {"kept": (GREY_LINE, 0.9), "straightened": (BLUE, 2.4), "dropped": (ORANGE, 2.4)}
    for f in sorted(feats, key=lambda f: order[f["properties"]["status"]]):
        colour, w = style[f["properties"]["status"]]
        m.polyline([(lat, lon) for lon, lat in f["geometry"]["coordinates"]], colour, w)
    n = {k: sum(1 for f in feats if f["properties"]["status"] == k) for k in order}
    m.legend([(f"Kept ({n['kept']} route directions)", GREY_LINE, 2),
              (f"Straightened ({n['straightened']}), new path shown", BLUE, 3),
              (f"Dropped or merged ({n['dropped']})", ORANGE, 3)],
             title="The redesign")
    m.scale_bar()
    return m.render()


SETTING_LABELS = {
    "default": "Default settings",
    "transfer_penalty_2": "Transfer penalty 2 minutes instead of 5",
    "transfer_penalty_8": "Transfer penalty 8 minutes",
    "trip_decay_4": "Distance decay 4 km instead of 6",
    "trip_decay_9": "Distance decay 9 km",
    "homes_only": "Trips end at homes only",
    "boardings_per_trip_45": "45 boardings per trip instead of 60",
    "boardings_per_trip_80": "80 boardings per trip",
    "walk_400": "Access radius 400 m instead of 500",
    "origins_200": "Search sample of 200 origins",
    "seed_23": "Search sample with another seed",
    "nobody_loses_stop": "Nobody may lose a stop",
    "no_shifts": "No bus shifts",
    "zone_headways_0_8": "Service-type headways × 0.8",
    "zone_headways_1_25": "Service-type headways × 1.25",
}


def figure_4(seeds, settings, check_seed=7):
    """Dot plots of the gain in the capped average, one row per run, on one shared axis."""
    width, left, right = 1000, 330, 960
    row_h, top = 22, 36
    gains = [float(r["gain_min"]) for r in seeds] + [float(r["gain_min"]) for r in settings]
    x_max = max(1.0, math.ceil(max(gains) * 5) / 5)
    default_gain = next(float(r["gain_min"]) for r in settings if r["variant"] == "default")

    def X(v):
        return left + (right - left) * v / x_max

    parts, y = [], top
    panels = [("Ten trip samples of 300 origins (seed 7 is the independent check)",
               [(f"Sample {r['seed']}", float(r["gain_min"]), int(r["seed"]) == check_seed) for r in seeds]),
              ("The search under other assumptions, scored on the independent check",
               [(SETTING_LABELS.get(r["variant"], r["what"]), float(r["gain_min"]), r["variant"] == "default")
                for r in settings])]
    height = top + sum(len(rows) * row_h + 56 for _, rows in panels) + 10
    # gridlines and the default run's line span both panels
    for v in [i / 5 for i in range(int(x_max * 5) + 1)]:
        parts.append(f'<line x1="{X(v):.1f}" y1="{top - 4}" x2="{X(v):.1f}" y2="{height - 30}" stroke="{HAIR}" stroke-width="1"/>')
    parts.append(f'<line x1="{X(default_gain):.1f}" y1="{top - 4}" x2="{X(default_gain):.1f}" y2="{height - 30}" '
                 f'stroke="{ORANGE}" stroke-width="1.5" stroke-dasharray="4 3"/>')
    for title, rows in panels:
        parts.append(text(left - 300, y, title, 14, INK, weight="bold"))
        y += 20
        lo, hi = min(r[1] for r in rows), max(r[1] for r in rows)
        for label, gain, marked in rows:
            cy = y + row_h / 2
            parts.append(text(left - 12, cy + 5, label, 13, INK2, anchor="end"))
            parts.append(f'<line x1="{left}" y1="{cy:.1f}" x2="{right}" y2="{cy:.1f}" stroke="{HAIR}" stroke-width="1"/>')
            x = X(gain)
            if marked:
                parts.append(f'<polygon points="{x:.1f},{cy - 7:.1f} {x + 7:.1f},{cy:.1f} {x:.1f},{cy + 7:.1f} {x - 7:.1f},{cy:.1f}" '
                             f'fill="{ORANGE}" stroke="#ffffff" stroke-width="2"/>')
            else:
                parts.append(f'<circle cx="{x:.1f}" cy="{cy:.1f}" r="5" fill="{BLUE}" stroke="#ffffff" stroke-width="2"/>')
            if gain in (lo, hi) or marked:
                parts.append(text(x + 11, cy + 4, f"{gain:.2f}", 12, INK2))
            y += row_h
        y += 36
    # axis
    ay = height - 30
    parts.append(f'<line x1="{left}" y1="{ay}" x2="{right}" y2="{ay}" stroke="{GREY_LINE}" stroke-width="1"/>')
    for v in [i / 5 for i in range(int(x_max * 5) + 1)]:
        parts.append(text(X(v), ay + 16, f"{v:.1f}", 12, MUTED, anchor="middle"))
    parts.append(text((left + right) / 2, ay + 32, "Gain in the capped average door-to-door time (minutes)", 13, INK2, anchor="middle"))
    parts.append(text(X(default_gain) + 6, top + 6, f"default run {default_gain:.2f}", 12, INK2))
    return svg(width, height + 10, parts)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inp = load_inputs(ROOT, ROOT / "busnet.toml", (), repair=True, split=False, say=lambda *a, **k: None)
    net = inp.network
    routes_csv = read_csv(ROOT / "output" / "routes.csv")
    corridors = read_csv(ROOT / "output" / "corridors.csv")
    geojson = json.loads((ROOT / "output" / "redesign" / "network.geojson").read_text(encoding="utf-8"))
    seeds = read_csv(ROOT / "output" / "robustness" / "redesign_seeds.csv")
    settings = read_csv(ROOT / "output" / "robustness" / "redesign_settings.csv")
    figures = {
        "figure-1.svg": figure_1(net, inp.zones, routes_csv),
        "figure-2.svg": figure_2(net, corridors),
        "figure-3.svg": figure_3(net, geojson),
        "figure-4.svg": figure_4(seeds, settings),
    }
    for name, body in figures.items():
        (OUT / name).write_text(body, encoding="utf-8")
        print(f"{OUT / name}  {len(body) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
