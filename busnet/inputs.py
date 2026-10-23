"""Load everything busnet.toml points to, falling back to assumptions for missing files.

Shared by measure.py and redesign.py so both read the same data the same way."""

from dataclasses import dataclass, field
from pathlib import Path

from .config import load_config
from .destinations import metro_points, osm_points, zone_attraction
from .model import load_network
from .population import load_population, stops_bbox
from .ridership import latest_month, load_daily_boardings, weekday_mean
from .service import load_headways, route_headways


@dataclass
class Inputs:
    a: object                       # Assumptions
    network: object                 # Network
    zones: list = None              # [(lat, lon, people)]
    attraction: list = None         # pull of each zone on trip ends, or None
    observed: dict = None           # route number -> observed weekday boardings
    observed_month: str = None
    supplied: dict = None           # route number -> real headway (minutes)
    headways: dict = None           # route id -> (minutes, source)
    points: list = field(default_factory=list)   # destination points
    found: dict = field(default_factory=dict)    # input name -> path used, or None if missing
    data: dict = field(default_factory=dict)     # data paths from the config


def load_inputs(root, config=None, overrides=(), repair=True, split=True, say=print):
    """Read settings and every input. split=False keeps one zone per population hexagon."""
    root = Path(root)
    a, data = load_config(config, overrides)
    found = {}

    def available(path, what):
        ok = bool(path) and Path(path).exists()
        found[what] = (str(Path(path).relative_to(root)) if Path(path).is_relative_to(root) else str(path)) if ok else None
        if path and not ok:
            say(f"  missing {what}: {path} (using assumptions instead)")
        return ok

    db = data.get("db", str(root / "data" / "ayna.db"))
    available(db, "db")
    inp = Inputs(a=a, network=load_network(db, repair=repair), data=data, found=found)
    net = inp.network
    if available(data.get("population"), "population"):
        inp.zones = load_population(data["population"], stops_bbox(net), split=split)
    if available(data.get("ridership"), "ridership"):
        daily = load_daily_boardings(data["ridership"])
        year, month = latest_month(daily)
        inp.observed, inp.observed_month = weekday_mean(daily, year, month), f"{year}-{month:02d}"
    if available(data.get("headways"), "headways"):
        inp.supplied = load_headways(data["headways"])
    inp.headways = route_headways(net, a, inp.observed, inp.supplied)

    files = [p for p in data.get("destinations", []) if available(p, f"destinations:{Path(p).name}")]
    if files:
        inp.points += osm_points(files, a.destination_weights)
    if available(data.get("metro_passengers"), "metro_passengers") and available(data.get("metro_exits"), "metro_exits"):
        metro, unmatched = metro_points(data["metro_passengers"], data["metro_exits"], a.metro_weight_per_1000_entries)
        inp.points += metro
        if unmatched:
            say(f"  metro stations without exit coordinates: {', '.join(unmatched)}")
    if inp.zones:
        inp.attraction = zone_attraction(inp.zones, inp.points, a.destination_share)
    return inp
