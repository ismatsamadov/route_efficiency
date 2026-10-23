"""Observed boardings per route, from the BakuBus daily counts published on opendata.az.

The CSV has three columns: date (e.g. "2026-01-01 00:00:00,000"), route number and
daily boardings. It covers BakuBus routes only, so routes run by other carriers
have no observed figure."""

import csv
import datetime
import statistics
from collections import defaultdict


def load_daily_boardings(path):
    """{route number: {date: boardings}}."""
    out = defaultdict(dict)
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 3 or not row[2].strip():
                continue
            day = datetime.date.fromisoformat(row[0].strip()[:10])
            route = row[1].strip()
            out[route][day] = out[route].get(day, 0) + int(float(row[2]))
    return dict(out)


def latest_month(daily):
    """(year, month) of the most recent month with data."""
    last = max(d for days in daily.values() for d in days)
    return last.year, last.month


def weekday_mean(daily, year=None, month=None):
    """Mean boardings per Monday-to-Friday day, for one month if given."""
    out = {}
    for route, days in daily.items():
        vals = [n for d, n in days.items()
                if d.weekday() < 5 and (month is None or (d.year, d.month) == (year, month))]
        if vals:
            out[route] = statistics.mean(vals)
    return out
