"""A small made-up network for the unit tests: two routes on one straight street."""

from busnet.model import Network, Route, Stop, _straight_pattern

LAT, LON, STEP = 40.40, 49.80, 0.01          # stops 0.01 degrees of longitude apart, about 847 m


def route(rid, number, zone="Şəhərdaxili", carrier="Test MMC"):
    return Route(rid, number, carrier, "A", "B", 0.0, zone, "Bakı", 0.5, "Kart", "")


def stop(sid, lat, lon, hub=False):
    return Stop(sid, str(sid), f"stop {sid}", lat, lon, hub)


def straight(rid, direction, stops, stop_ids):
    return _straight_pattern(rid, direction, list(stop_ids), [(stops[s].lat, stops[s].lon) for s in stop_ids])


def two_route_network():
    """Route 1 serves stops 1 to 5 both ways; route 2A serves stops 1 to 3 both ways."""
    stops = {i: stop(i, LAT, LON + STEP * (i - 1)) for i in range(1, 6)}
    routes = {1: route(1, "1"), 2: route(2, "2A", zone="Şəhərətrafı")}
    patterns = {
        (1, 1): straight(1, 1, stops, [1, 2, 3, 4, 5]),
        (1, 2): straight(1, 2, stops, [5, 4, 3, 2, 1]),
        (2, 1): straight(2, 1, stops, [1, 2, 3]),
        (2, 2): straight(2, 2, stops, [3, 2, 1]),
    }
    return Network(routes, stops, patterns)
