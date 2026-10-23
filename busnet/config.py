"""Settings from a TOML file, so assumptions and data paths change without editing code.

A config file has a [data] table of file paths and any number of other tables whose
keys are Assumptions fields; the table names only group them for readers. Tables such
as headway_by_zone are merged with the defaults, so one entry can be changed alone.
Unknown keys are an error, so a typo cannot be silently ignored."""

import tomllib
from dataclasses import fields, replace
from pathlib import Path

from .assumptions import Assumptions

DATA_KEYS = ("db", "population", "ridership", "headways", "destinations", "metro_passengers", "metro_exits")


def parse_value(text):
    """A TOML value from the command line: 12, 0.5, true, "text" or {a = 1}; bare words stay text."""
    try:
        return tomllib.loads(f"v = {text}")["v"]
    except tomllib.TOMLDecodeError:
        return text.strip()


def load_config(path=None, overrides=()):
    """(Assumptions, {data key: path}) from an optional TOML file and "name=value" overrides.

    Relative data paths in the file are read relative to the file's own folder."""
    raw, base = {}, Path(".")
    if path:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
        base = Path(path).resolve().parent
    settings, data = {}, {}
    for section, values in raw.items():
        if section == "data":
            data.update({k: _resolve(base, v) for k, v in values.items()})
        elif isinstance(values, dict) and section not in _DICT_FIELDS:
            settings.update(values)
        else:
            settings[section] = values
    for item in overrides:
        key, sep, value = item.partition("=")
        if not sep:
            raise ValueError(f"--set needs name=value, got {item!r}")
        key = key.strip()
        if key in DATA_KEYS:
            data[key] = _resolve(Path("."), parse_value(value))
        else:
            settings[key] = parse_value(value)

    unknown = sorted(set(data) - set(DATA_KEYS)) + sorted(set(settings) - _FIELDS)
    if unknown:
        raise ValueError(f"unknown setting(s): {', '.join(unknown)}. "
                         f"Data keys: {', '.join(DATA_KEYS)}. Assumptions: {', '.join(sorted(_FIELDS))}")
    defaults = Assumptions()
    for key in _DICT_FIELDS & set(settings):
        settings[key] = {**getattr(defaults, key), **settings[key]}
    return replace(defaults, **settings), data


def _resolve(base, value):
    if isinstance(value, list):
        return [_resolve(base, v) for v in value]
    p = Path(value)
    return str(p if p.is_absolute() else base / p)


_FIELDS = {f.name for f in fields(Assumptions)}
_DICT_FIELDS = {f.name for f in fields(Assumptions) if isinstance(getattr(Assumptions(), f.name), dict)}
