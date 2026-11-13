#!/usr/bin/env python3
"""
Draw the animations at the top of the README as GIFs, from the committed data and outputs.

  buses.gif        a modelled hour: every route of today's network run at its estimated
                   headway and modelled speed, as the GTFS feed describes them
  riders.gif       every day from 1 January to 30 September 2026 as counted: boardings on
                   each BakuBus route and entries at each metro station (opendata.az)
  redesign.gif     the redesign search replayed: the 27 changes redesign.py keeps, one at
                   a time, with the average door-to-door time on its sample of trips
  travel-time.gif  how far the buses take you, minute by minute, from the stop where the
                   page's travel-time view starts, by the same travel model

Only riders.gif shows counts. AYNA publishes no timetables and no bus positions, so the
buses run as the model runs them, and each picture says what it rests on.

redesign.gif runs the search again (about two minutes) and stops if it keeps other changes
than output/redesign/changes.csv lists, so run redesign.py first after any change to the
data or the settings.

Standard library only, like the rest of the repository; draw.py holds the drawing and the
GIF writer. The maps use the flat projection of the measurements (busnet.geo.PROJ), the
crop of the manuscript's figures and the repaired network the measurements use. Usage:
  python3 animations/build.py                    # all four, about four minutes
  python3 animations/build.py --only riders      # one of them; repeatable
"""

import argparse
import bisect
import csv
import datetime
import json
import math
import random
import sqlite3
import struct
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import draw                                                                     # noqa: E402
from busnet.destinations import _match, read_exits                             # noqa: E402
from busnet.geo import PROJ, Polyline                                           # noqa: E402
from busnet.graph import TransitGraph                                           # noqa: E402
from busnet.inputs import load_inputs                                           # noqa: E402
from busnet.optimize import Context, Evaluator, Plan, search                    # noqa: E402
from busnet.population import _mercator_to_latlon, load_population, stops_bbox  # noqa: E402
from busnet.ridership import load_daily_boardings                              # noqa: E402

# The page's colours (site/app.js and site/style.css).
PAGE, INK, INK2, MUTED = "#f7f8f5", "#192d3b", "#56646a", "#65726c"
BLUE, ORANGE, GREEN, RED = "#2a78d6", "#eb6834", "#1baf7a", "#d03b3b"
ROUTE_GREY, FAINT = "#a9a89e", "#a9b1bf"
TIME_RAMP = ["#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]      # up to 15, 30, 45, 60 min, more
# People per population hexagon (Kontur, about 0.74 km² each): 100, 1,000, 5,000, 10,000 and more.
PEOPLE_STEPS = [(10000, "#d2dbca"), (5000, "#dde4d6"), (1000, "#e7ece2"), (100, "#eff2eb")]

CROP = (40.27, 40.62, 49.58, 50.36)      # the crop of the manuscript's figures (paper/figures.py)
WIDTH = 960
TX, TY = 340, 466                        # where the text starts: the sea south of the city
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


class Map:
    """The crop in the measurements' flat projection, in pixels from the top left."""

    def __init__(self, bbox=CROP, width=WIDTH):
        lat0, lat1, lon0, lon1 = bbox
        self.x0, y0 = PROJ.to_xy(lat0, lon0)
        x1, self.y1 = PROJ.to_xy(lat1, lon1)
        self.scale = width / (x1 - self.x0)
        self.w, self.h = width, round((self.y1 - y0) * self.scale)

    def px(self, lat, lon):
        x, y = PROJ.to_xy(lat, lon)
        return (x - self.x0) * self.scale, (self.y1 - y) * self.scale

    def line(self, latlon, tol=0.6):
        """A path in pixels, leaving out points within tol pixels of the last one kept."""
        pts = [self.px(a, b) for a, b in latlon]
        out = pts[:1]
        for p in pts[1:-1]:
            if abs(p[0] - out[-1][0]) + abs(p[1] - out[-1][1]) > tol:
                out.append(p)
        return out + pts[-1:] if len(pts) > 1 else out


def _ring(blob):
    """Outer ring of a GeoPackage polygon, in the layer's own coordinates (as site/build.py)."""
    flags = blob[3]
    env_len = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(flags >> 1) & 7]
    wkb = blob[8 + env_len:]
    order = "<" if wkb[0] == 1 else ">"
    if struct.unpack(order + "I", wkb[1:5])[0] % 1000 == 6:          # multipolygon: the first polygon
        wkb = wkb[9:]
        order = "<" if wkb[0] == 1 else ">"
    npts = struct.unpack(order + "I", wkb[9:13])[0]
    coords = struct.unpack(order + f"{2 * npts}d", wkb[13:13 + 16 * npts])
    return list(zip(coords[0::2], coords[1::2]))


def hexagons(path, bbox=CROP):
    """[(ring as (lat, lon), people)] for the population hexagons with a corner in bbox."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    table, geom_col, srs = con.execute(
        "SELECT c.table_name, g.column_name, g.srs_id FROM gpkg_contents c "
        "JOIN gpkg_geometry_columns g ON g.table_name = c.table_name "
        "WHERE c.data_type = 'features' LIMIT 1").fetchone()
    cols = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
    pop_col = next(c for c in cols if c.lower() in ("population", "pop", "people"))
    out = []
    for blob, pop in con.execute(f'SELECT "{geom_col}", "{pop_col}" FROM "{table}"'):
        if not blob or not pop:
            continue
        ring = [_mercator_to_latlon(x, y) if srs == 3857 else (y, x) for x, y in _ring(blob)]
        if any(bbox[0] <= a <= bbox[1] and bbox[2] <= b <= bbox[3] for a, b in ring):
            out.append((ring, float(pop)))
    con.close()
    return out


def base_map(m, hexes):
    """The page colour with the population hexagons in four light steps."""
    c = draw.Canvas(m.w, m.h, PAGE)
    for ring, people in hexes:
        colour = next((col for least, col in PEOPLE_STEPS if people >= least), None)
        if colour:
            c.paint(c.mask().polygon([m.px(a, b) for a, b in ring]), colour)
    return c


def network_lines(c, m, patterns, colour=ROUTE_GREY, width=0.9, opacity=0.5):
    """Each route direction as its own line, so that where routes share a street it darkens."""
    for p in patterns:
        c.paint(c.mask().line(m.line(p.path), width), colour, opacity)


def legend(c, x, y, items, size=11):
    """Coloured dots with labels on one line; returns where the line ends."""
    for colour, label in items:
        c.disc(x + 4, y - size * 0.42, 4.2, "#ffffff")
        c.disc(x + 4, y - size * 0.42, 3.2, colour)
        c.text(x + 12, y, label, size, INK2, halo=PAGE)
        x += 12 + draw.text_width(label, size) + 14
    return x


def wrap(text, size, width):
    """Lines of at most width pixels, broken between words."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and draw.text_width(trial, size) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur] if cur else lines


def note(c, text, y=TY + 77, size=10, most=2):
    """Small print under the legend, wrapped to the text column, in at most `most` lines."""
    rows = wrap(text, size, WIDTH - 24 - TX)
    if len(rows) > most:
        raise ValueError(f"{text!r} needs {len(rows)} lines")
    for k, row in enumerate(rows):
        c.text(TX, y + 13 * k, row, size, MUTED, halo=PAGE)


def chart(c, values, box, vmin, vmax, colour, upto=None, width=1.3):
    """A line of values across box = (x0, y0, x1, y1), up to index upto; returns its points."""
    x0, y0, x1, y1 = box
    n = len(values)
    pts = [(x0 + (x1 - x0) * k / max(1, n - 1), y1 - (y1 - y0) * (v - vmin) / (vmax - vmin))
           for k, v in enumerate(values)]
    shown = pts if upto is None else pts[:upto + 1]
    if len(shown) > 1:
        c.line(shown, width, colour)
    return pts


def thousands(n):
    return f"{n:,.0f}"


def day_text(d):
    return f"{WEEKDAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]} {d.year}"


# ---------------------------------------------------------------- 1. a modelled hour

def bus_runs(net, a, headways):
    """One run per route direction: its line, the time from its first stop to each stop, its
    headway and a start between 0 and the headway that is random but fixed. The times are
    the GTFS feed's: each hop at the zone's moving speed plus the fixed loss at a stop."""
    runs = []
    for key in sorted(net.patterns):
        p, rid = net.patterns[key], key[0]
        headway, source = headways[rid]
        speed = a.cruise_mps(net.routes[rid].zone)
        times = [0.0]
        for i in range(1, len(p.stop_ids)):
            times.append(times[-1] + (p.chainage_m[i] - p.chainage_m[i - 1]) / speed + a.stop_loss_s)
        h = headway * 60
        runs.append({"line": Polyline(p.path), "times": times, "chain": p.chainage_m, "h": h,
                     "phase": random.Random(f"{rid}/{key[1]}").random() * h,
                     "counted": source in ("supplied", "ridership")})
    return runs


def bus_positions(run, t):
    """(lat, lon) of every bus of a run that is on the road t seconds after the start:
    the buses that left at phase + k x headway, for every whole k, and have not arrived."""
    times, chain, h = run["times"], run["chain"], run["h"]
    out = []
    k = -int((run["phase"] + times[-1] - t) // h)              # the earliest bus still on the road
    while run["phase"] + k * h <= t:
        e = t - run["phase"] - k * h
        k += 1
        i = min(bisect.bisect_right(times, e) - 1, len(times) - 2)
        frac = (e - times[i]) / (times[i + 1] - times[i])
        out.append(run["line"].point_at(chain[i] + frac * (chain[i + 1] - chain[i])))
    return out


def buses(inp, m, base, out, minutes=60, step_s=45, delay_cs=9):
    """Every route direction runs at its route's headway (bus_runs, bus_positions). Buses on
    routes whose headway rests on counted boardings or a published headway are blue; the
    rest, whose headway is assumed from the type of service, orange."""
    net, a = inp.network, inp.a
    runs = bus_runs(net, a, inp.headways)
    blue_routes = sum(1 for _, s in inp.headways.values() if s in ("supplied", "ridership"))
    on_road = sum(r["times"][-1] / r["h"] for r in runs)

    still = base.copy()
    network_lines(still, m, net.patterns.values())
    still.text(TX, TY, "A modelled hour on Baku's buses", 16, INK, 1.75, halo=PAGE)
    still.text(TX, TY + 20, f"Today's {len(inp.headways)} routes on AYNA's map, about "
               f"{thousands(round(on_road, -1))} buses on the road at once", 11, INK2, halo=PAGE)
    legend(still, TX, TY + 40, [(BLUE, f"frequency based on counts or a published headway ({blue_routes} routes)")])
    legend(still, TX, TY + 57, [(ORANGE, f"frequency assumed by type of service ({len(inp.headways) - blue_routes} routes)")])
    note(still, f"Not tracked: AYNA publishes no timetables or bus positions. One frequency per route all day; "
                f"speeds by type of service average 22 km/h, with {a.stop_loss_s:.0f} s lost per stop.")

    gif = draw.Gif(m.w, m.h, pinned=[PAGE, INK, INK2, MUTED, BLUE, ORANGE, "#ffffff"], colours=64)
    frames = minutes * 60 // step_s
    for f in range(frames):
        t = f * step_s
        c = still.copy()
        casing, dots = c.mask(), {True: c.mask(), False: c.mask()}
        for r in runs:
            for lat, lon in bus_positions(r, t):
                bx, by = m.px(lat, lon)
                if -4 < bx < m.w + 4 and -4 < by < m.h + 4:
                    casing.disc(bx, by, 2.7)
                    dots[r["counted"]].disc(bx, by, 1.8)
        c.paint(casing, "#ffffff", 0.9)
        c.paint(dots[False], ORANGE)
        c.paint(dots[True], BLUE)
        c.text(m.w - 24, 38, f"minute {t // 60}", 16, INK, 1.75, halo=PAGE, align="right")
        c.rect(m.w - 144, 48, m.w - 24, 50, "#d4d8cf")
        c.rect(m.w - 144, 48, m.w - 144 + 120 * (f + 1) / frames, 50, INK)
        gif.add(c, delay_cs)
    return gif.write(out / "buses.gif")


# ---------------------------------------------------------------- 2. counted riders

BOARDINGS_PER_PX = 4000      # a route's line is one pixel wide for every 4,000 boardings a day
ENTRIES_PER_PX2 = 230        # a station's circle has one square pixel for every 230 entries


def route_width(boardings):
    """Line width in whole pixels: a day like the one before then mostly leaves the picture
    alone, which keeps the GIF small (it stores only the pixels that change)."""
    return max(0.5, math.floor(boardings / BOARDINGS_PER_PX + 0.5))


def station_radius(entries):
    """Circle radius in half pixels, for the same reason."""
    return math.floor(math.sqrt(entries / ENTRIES_PER_PX2 / math.pi) * 2 + 0.5) / 2


def metro_entries(path):
    """{station: {date: entries}} from the opendata.az file of daily entries per station."""
    daily = defaultdict(dict)
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f, delimiter=";" if ";" in f.readline() else ","))
    for row in rows:
        if len(row) >= 3 and row[2].strip().isdigit():
            daily[row[1].strip()][datetime.date.fromisoformat(row[0].strip()[:10])] = int(row[2])
    return dict(daily)


def riders(inp, m, base, out, delay_cs=6):
    """Each counted bus route that AYNA's map carries, drawn as wide as its boardings that day,
    and each metro station as a circle whose area is its entries that day."""
    net = inp.network
    daily = load_daily_boardings(inp.data["ridership"])
    ids = {r.number: rid for rid, r in net.routes.items() if net.patterns_of(rid)}
    drawn = sorted(n for n in daily if n in ids)
    hidden = sorted(n for n in daily if n not in ids)
    entries = metro_entries(inp.data["metro_passengers"])
    exits = defaultdict(list)
    for name, lat, lon in read_exits(inp.data["metro_exits"]):
        exits[name].append((lat, lon))
    stations = {}
    for name in sorted(entries):
        match = _match(name, list(exits))
        if not match:
            sys.exit(f"riders.gif: no exits for the metro station {name}")
        pts = exits[match]
        stations[name] = m.px(sum(a for a, _ in pts) / len(pts), sum(b for _, b in pts) / len(pts))
    days = sorted({d for v in daily.values() for d in v} | {d for v in entries.values() for d in v})
    bus_total = [sum(v.get(d, 0) for v in daily.values()) for d in days]
    metro_total = [sum(v.get(d, 0) for v in entries.values()) for d in days]
    fields = {n: draw.Field(m.w, m.h, [m.line(p.path) for p in net.patterns_of(ids[n])],
                            route_width(max(daily[n].values())) / 2 + 1) for n in drawn}

    still = base.copy()
    network_lines(still, m, net.patterns.values(), opacity=0.3)
    still.text(TX, TY, "Counted riders, day by day", 16, INK, 1.75, halo=PAGE)
    still.text(TX, TY + 20, f"Every day from {days[0].day} {MONTHS[days[0].month - 1]} to {days[-1].day} "
               f"{MONTHS[days[-1].month - 1]} {days[-1].year}, as counted", 11, INK2, halo=PAGE)
    still.line([(TX, TY + 35.5), (TX + 18, TY + 35.5)], route_width(10000), BLUE, 0.5)
    still.text(TX + 26, TY + 40, "10,000 boardings a day on a BakuBus route", 11, INK2, halo=PAGE)
    r20 = station_radius(20000)
    still.disc(TX + 9, TY + 53, r20 + 1, "#ffffff")
    still.disc(TX + 9, TY + 53, r20, ORANGE, 0.85)
    still.text(TX + 26, TY + 57, "20,000 entries a day at a metro station", 11, INK2, halo=PAGE)
    note(still, f"Both counts are published by Baku Metro on opendata.az. The {len(hidden)} counted routes not on "
                f"AYNA's map are not drawn, and the other bus carriers publish no counts.")
    box = (662, 80, 936, 124)
    vmax = math.ceil(max(bus_total + metro_total) / 100000) * 100000
    still.rect(box[0], box[3], box[2] + 1, box[3] + 1, "#c9cec4")
    for k, d in enumerate(days):
        if d.day == 1:
            x = box[0] + (box[2] - box[0]) * k / (len(days) - 1)
            still.rect(x, box[3] + 1, x + 1, box[3] + 4, "#c9cec4")
            still.text(x + 2, box[3] + 13, MONTHS[d.month - 1][:3], 9, MUTED, 1.2, halo=PAGE)
    works = days.index(datetime.date(2026, 8, 15))         # trains stop between 28 May and Nizami
    xw = box[0] + (box[2] - box[0]) * works / (len(days) - 1)
    for yy in range(box[1] - 2, box[3], 4):
        still.rect(xw, yy, xw + 1, yy + 2, MUTED)
    still.text(xw - 3, box[1] - 5, "metro works", 9, MUTED, 1.2, halo=PAGE, align="right")
    bus_pts = chart(still, bus_total, box, 0, vmax, BLUE)
    metro_pts = chart(still, metro_total, box, 0, vmax, ORANGE)

    gif = draw.Gif(m.w, m.h, pinned=[PAGE, INK, INK2, MUTED, BLUE, ORANGE, "#ffffff"], colours=64)
    for k, d in enumerate(days):
        c = still.copy()
        for n in sorted(drawn, key=lambda n: (-daily[n].get(d, 0), n)):     # wide first, narrow on top
            v = daily[n].get(d, 0)
            if v > 0:
                c.paint(fields[n].mask(route_width(v)), BLUE, 0.5)
        casing, dots = c.mask(), c.mask()
        for name, (x, y) in stations.items():
            v = entries[name].get(d, 0)
            if v > 0:
                r = station_radius(v)
                casing.disc(x, y, r + 1)
                dots.disc(x, y, r)
        c.paint(casing, "#ffffff", 0.9)
        c.paint(dots, ORANGE, 0.85)
        c.text(m.w - 24, 38, day_text(d), 16, INK, 1.75, halo=PAGE, align="right")
        c.text(m.w - 24, 56, f"BakuBus {thousands(bus_total[k])} boardings · metro {thousands(metro_total[k])} entries",
               11, INK2, halo=PAGE, align="right")
        x = bus_pts[k][0]
        c.rect(x, box[1] - 2, x + 1, box[3], INK, 0.6)
        c.disc(*bus_pts[k], 2.4, BLUE)
        c.disc(*metro_pts[k], 2.4, ORANGE)
        gif.add(c, delay_cs)
    return gif.write(out / "riders.gif")


# ---------------------------------------------------------------- 3. the redesign search

KIND_NAMES = {"merge": "merge two routes", "drop": "drop a route", "straighten": "straighten a detour",
              "stops": "balance stops", "shift": "move buses"}


def describe(row):
    """The change as changes.csv words it, without stop names (the font has Latin letters
    only) and without the lists of routes that the map shows in colour."""
    text = row["change"]
    if row["kind"] == "straighten":
        return text.split(" between ")[0] + ": " + text.rsplit(": ", 1)[1]
    if row["kind"] == "shift":
        return text.split(" (")[0] + " to the " + text.split(" to the ")[1].split(" (")[0]
    return text.split("; its buses go to ")[0]


def replay_search(inp):
    """Today's plan; [(change, plan after it)] for each change redesign.py's search keeps; the
    changes as output/redesign/changes.csv records them; and the search's context."""
    net, a = inp.network, inp.a
    fine = load_population(inp.data["population"], stops_bbox(net), split=True)
    today = Plan.from_headways(net, a, inp.headways)
    evaluator = Evaluator(net, a, inp.zones, inp.attraction, coverage_zones=fine,
                          n_origins=a.redesign_origins, seed=a.redesign_seed)
    ctx = Context(net, a, evaluator, observed=inp.observed)
    steps = []
    _, log, _, _ = search(today, evaluator, ctx, say=lambda *_: None, kept=lambda ch, p: steps.append((ch, p)))
    with open(ROOT / "output" / "redesign" / "changes.csv", newline="", encoding="utf-8-sig") as f:
        recorded = list(csv.DictReader(f))
    same = len(recorded) == len(log) and all(
        r["kind"] == g["kind"] and r["routes"] == g["routes"] and abs(float(r["minutes_after"]) - g["minutes_after"]) < 1e-3
        for r, g in zip(recorded, log))
    if not same:
        sys.exit("redesign.gif: the search kept other changes than output/redesign/changes.csv; run redesign.py first")
    return today, steps, recorded, ctx


def redesign(inp, m, base, out):
    """Today's network, then each change the search keeps: what it touches in colour, the
    network after it, and the average door-to-door time on the search's sample of trips."""
    today, steps, rows, ctx = replay_search(inp)
    summary = json.loads((ROOT / "output" / "redesign" / "summary.json").read_text(encoding="utf-8"))
    minutes = [float(rows[0]["minutes_before"])] + [float(r["minutes_after"]) for r in rows]
    lo, hi = math.floor(min(minutes) * 5) / 5 - 0.1, math.ceil(max(minutes) * 5) / 5 + 0.1
    box = (712, 70, 936, 118)
    n = len(steps)
    ghosts, greens, gone = [], [], []          # dropped routes, new stretches, removed stops (pixels)

    def frame(plan, step, value, highlight=None, lines=(), items=(), people=0.0, title_2=None,
              note_text="A change is kept only if the average trip on the search's sample gets shorter."):
        c = base.copy()
        network_lines(c, m, plan.network.patterns.values())
        for pts in ghosts:
            c.line(pts, 1.0, RED, 0.35)
        for x, y in gone:
            c.disc(x, y, 1.1, RED, 0.45)
        for pts in greens:
            c.line(pts, 1.8, GREEN)
        if highlight:
            highlight(c)
        c.text(TX, TY, "The redesign search, one change at a time", 16, INK, 1.75, halo=PAGE)
        c.text(TX, TY + 21, title_2 or "Today's network: the search starts here", 12.5, INK, 1.6, halo=PAGE)
        if len(lines) + (people >= 1) > 2:
            raise ValueError(f"step {step}: too much text for the space above the legend")
        y = TY + 38
        for text in lines:
            c.text(TX, y, text, 11, INK2, halo=PAGE)
            y += 15
        if people >= 1:
            c.text(TX, y, f"{thousands(people)} people are left with no stop within 500 m", 11, RED, halo=PAGE)
        if items:
            legend(c, TX, TY + 74, items)
        note(c, note_text, TY + 92, most=1)
        c.text(m.w - 24, 38, f"{value:.2f} min", 16, INK, 1.75, halo=PAGE, align="right")
        c.text(m.w - 24, 56, "average door to door, search sample", 10, MUTED, halo=PAGE, align="right")
        c.rect(box[0], box[3], box[2] + 1, box[3] + 1, "#c9cec4")
        pts = chart(c, minutes, box, lo, hi, INK, upto=step)
        c.disc(*pts[step], 2.6, INK)
        c.text(box[0], box[3] + 13, "today", 9, MUTED, 1.2, halo=PAGE)
        c.text(box[2], box[3] + 13, f"step {n}", 9, MUTED, 1.2, halo=PAGE, align="right")
        return c

    def lines_of(pats, colour, width):
        return lambda c: [c.line(m.line(p.path), width, colour) for p in pats]

    gif = draw.Gif(m.w, m.h, pinned=[PAGE, INK, INK2, MUTED, BLUE, ORANGE, GREEN, RED, "#ffffff"], colours=96)
    gif.add(frame(today, 0, minutes[0], lines=[f"{summary['routes_before']} routes and "
                                                f"{thousands(summary['independent_check']['before']['served_stops'])} stops, "
                                                f"{thousands(summary['fleet_buses'])} buses (estimated)"]), 180)
    prev = today
    for k, ((change, after), row) in enumerate(zip(steps, rows), 1):
        net = prev.network
        kind = row["kind"]
        text = wrap(describe(row), 11, m.w - 24 - TX)
        people = float(row["people_losing_stop"])
        if kind in ("merge", "drop"):
            dropped = net.patterns_of(change.rid)
            others = [change.target] if kind == "merge" else change.receivers
            items = [(RED, f"{net.number(change.rid)}: {'merged' if kind == 'merge' else 'dropped'}"),
                     (BLUE, f"{net.number(change.target)}: takes its riders" if kind == "merge" else "get its buses")]

            def light(c, dropped=dropped, others=others, net=net):
                for r in others:
                    lines_of(net.patterns_of(r), BLUE, 1.8)(c)
                lines_of(dropped, RED, 2.4)(c)
        elif kind == "straighten":
            old = net.patterns[change.key]
            old_stretch = m.line(Polyline(old.path).slice_latlon(old.chainage_m[change.i], old.chainage_m[change.j]))
            new_stretch = m.line(ctx.streets.geometry(change.path))
            items = [(RED, "the detour"), (GREEN, "the shorter path, on streets buses use")]

            xs = [x for x, _ in old_stretch + new_stretch]
            ys = [y for _, y in old_stretch + new_stretch]
            cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
            ring = max(14.0, math.hypot(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 8)

            def light(c, old_stretch=old_stretch, new_stretch=new_stretch, cx=cx, cy=cy, ring=ring):
                c.line(old_stretch, 2.6, RED)
                c.line(new_stretch, 2.6, GREEN)
                c.line([(cx + ring * math.cos(k / 36 * 2 * math.pi), cy + ring * math.sin(k / 36 * 2 * math.pi))
                        for k in range(37)], 1.5, INK)
        elif kind == "stops":
            removed = sorted(net.served_stop_ids() - after.network.served_stop_ids())
            dots = [m.px(net.stops[s].lat, net.stops[s].lon) for s in removed]
            items = [(RED, f"{len(removed)} stops removed")]

            def light(c, dots=dots):
                mask = c.mask()
                for x, y in dots:
                    mask.disc(x, y, 1.9)
                c.paint(mask, RED)
        else:
            items = [(ORANGE, f"{len(change.donors)} routes give buses"), (BLUE, f"{len(change.takers)} routes get them")]

            def light(c, change=change, net=net):
                for r in change.donors:
                    lines_of(net.patterns_of(r), ORANGE, 2.2)(c)
                for r in change.takers:
                    lines_of(net.patterns_of(r), BLUE, 2.2)(c)
        hold = 170 if kind in ("stops", "shift") else 120
        gif.add(frame(prev, k - 1, minutes[k - 1], light, text, items, people,
                      f"Step {k} of {n} · {KIND_NAMES[kind]}"), hold)
        if kind in ("merge", "drop"):
            ghosts.extend(m.line(p.path) for p in net.patterns_of(change.rid))
        elif kind == "straighten":
            greens.append(new_stretch)
        elif kind == "stops":
            gone.extend(dots)
        gif.add(frame(after, k, minutes[k], lines=text, items=items, people=people,
                      title_2=f"Step {k} of {n} · {KIND_NAMES[kind]}: {minutes[k - 1] - minutes[k]:.3f} min shorter"), 45)
        prev = after
    ic = summary["independent_check"]
    gif.add(frame(prev, n, minutes[n], lines=wrap(
        f"{summary['routes_before']} → {summary['routes_after']} routes, {thousands(ic['before']['served_stops'])} → "
        f"{thousands(ic['after']['served_stops'])} stops, the same buses. On another sample of trips, the average trip "
        f"falls from {ic['before']['accessibility']['mean_door_to_door_min']:.1f} to "
        f"{ic['after']['accessibility']['mean_door_to_door_min']:.1f} minutes.", 11, m.w - 24 - TX),
        items=[(GREEN, "straightened"), (RED, "dropped or merged routes, removed stops")],
        title_2=f"The redesigned network, after {n} changes",
        note_text="Candidates to review, not a plan: docs/results.md lists what to check first."), 450)
    return gif.write(out / "redesign.gif")


# ---------------------------------------------------------------- 4. travel time

def travel_time(inp, m, base, out, last_min=120, delay_cs=8):
    """Minutes by bus from the stop with the most routes, where the page's travel-time view
    starts, to every stop, by the page's rebuild of the paper's travel model: the journey of
    least cost, with each change of bus costing transfer_penalty_min more, and the minutes
    shown leaving those penalties out."""
    net, a = inp.network, inp.a
    at = net.routes_at_stop()
    origin = min(at, key=lambda s: (-len(at[s]), s))
    graph = TransitGraph(net, a, inp.headways)
    dist, boards, _, _ = graph.search({graph.arrival(origin): 0.0},
                                      a.max_trip_min * 60 + 3 * a.transfer_penalty_s)
    reach = {}
    for s in graph.stop_ids:
        i = graph.arrival(s)
        if dist[i] < math.inf:
            reach[s] = (dist[i] - boards[i] * a.transfer_penalty_s) / 60
    total = len(graph.stop_ids)
    where = {s: m.px(net.stops[s].lat, net.stops[s].lon) for s in graph.stop_ids}
    name = net.stops[origin].name

    still = base.copy()
    network_lines(still, m, net.patterns.values(), opacity=0.35)
    faint = still.mask()
    for s in graph.stop_ids:
        faint.disc(*where[s], 1.0)
    still.paint(faint, FAINT, 0.7)
    still.text(TX, TY, "How far the buses take you", 16, INK, 1.75, halo=PAGE)
    still.text(TX, TY + 20, f"Minutes by bus from {name}, the stop with the most routes ({len(at[origin])})",
               11, INK2, halo=PAGE)
    end = legend(still, TX, TY + 40, [(TIME_RAMP[0], "up to 15 min"), (TIME_RAMP[1], "15–30"), (TIME_RAMP[2], "30–45"),
                                      (TIME_RAMP[3], "45–60"), (TIME_RAMP[4], "over 60")])
    legend(still, end, TY + 40, [(FAINT, f"not reached in {a.max_trip_min // 60:.0f} hours")])
    note(still, f"The paper's travel model, as on the page: a wait of half the headway at each boarding, speeds by "
                f"type of service, {a.stop_loss_s:.0f} s lost per stop, walks of up to {a.max_transfer_walk_m:.0f} m to "
                f"change, and each change avoided as if it cost {a.transfer_penalty_min:.0f} min, which the minutes "
                f"leave out.", TY + 60, most=3)
    ox, oy = where[origin]

    gif = draw.Gif(m.w, m.h, pinned=[PAGE, INK, INK2, MUTED, FAINT, "#ffffff"] + TIME_RAMP, colours=96)
    settled = still.copy()
    order = sorted(reach, key=lambda s: reach[s])
    done = 0
    for t in range(last_min + 1):
        new = []
        while done < len(order) and reach[order[done]] <= t:
            new.append(order[done])
            done += 1
        for s in new:
            settled.disc(*where[s], 2.1, TIME_RAMP[min(4, int(reach[s] // 15))])          # the page's bins
        c = settled.copy()
        front = c.mask()
        for s in new:
            front.disc(*where[s], 3.4)
        c.paint(front, "#ffffff", 0.55)
        c.line([(ox + 6.5 * math.cos(k / 24 * 2 * math.pi), oy + 6.5 * math.sin(k / 24 * 2 * math.pi))
                for k in range(25)], 1.8, INK)
        c.text(m.w - 24, 38, f"minute {t}", 16, INK, 1.75, halo=PAGE, align="right")
        c.text(m.w - 24, 56, f"{thousands(done)} of {thousands(total)} stops reached", 11, INK2, halo=PAGE, align="right")
        c.rect(m.w - 144, 64, m.w - 24, 66, "#d4d8cf")
        c.rect(m.w - 144, 64, m.w - 144 + 120 * done / total, 66, INK)
        gif.add(c, 300 if t == last_min else delay_cs)
    return gif.write(out / "travel-time.gif")


# ---------------------------------------------------------------- main

ANIMATIONS = {"buses": buses, "riders": riders, "redesign": redesign, "travel-time": travel_time}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append", choices=list(ANIMATIONS), help="draw only this one; repeatable")
    ap.add_argument("--out", default=str(HERE))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    inp = load_inputs(ROOT, ROOT / "busnet.toml", split=False, say=lambda *_: None)    # as redesign.py reads them
    m = Map()
    base = base_map(m, hexagons(inp.data["population"]))
    for name in args.only or list(ANIMATIONS):
        t1 = time.time()
        size = ANIMATIONS[name](inp, m, base, out)
        print(f"{name}.gif: {size / 1e6:.1f} MB in {time.time() - t1:.0f}s")
    print(f"Done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
