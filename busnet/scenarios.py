"""Changes to the network that can be measured against the current one.

Each function takes a Network and returns (new_network, details) without touching
the original, so the same metrics can score both and show the difference."""

from collections import defaultdict

from .model import Pattern


def balance_stops(network, min_gap_m=250.0, max_gap_after_m=700.0):
    """Remove closely spaced stops, the way stop-balancing programmes do.

    A stop is removed only when, on every route direction that uses it:
      - it is not the first or last stop, and is not a flagged interchange hub,
      - it sits less than min_gap_m along the path from the previous or next kept stop,
      - removing it leaves no gap longer than max_gap_after_m.
    Stops served by fewer routes go first, so busy transfer stops are kept."""
    uses = defaultdict(list)                     # stop -> [(pattern key, position)]
    for key, p in network.patterns.items():
        for i, s in enumerate(p.stop_ids):
            uses[s].append((key, i))
    protected = {s for p in network.patterns.values() for s in (p.stop_ids[0], p.stop_ids[-1])}
    protected |= {s for s in uses if network.stops[s].is_hub}
    kept = {key: [True] * len(p.stop_ids) for key, p in network.patterns.items()}

    def neighbours(key, i):
        k = kept[key]
        prev = next(j for j in range(i - 1, -1, -1) if k[j])
        nxt = next(j for j in range(i + 1, len(k)) if k[j])
        return prev, nxt

    def removable(s):
        for key, i in uses[s]:
            ch = network.patterns[key].chainage_m
            prev, nxt = neighbours(key, i)
            if min(ch[i] - ch[prev], ch[nxt] - ch[i]) >= min_gap_m or ch[nxt] - ch[prev] > max_gap_after_m:
                return False
        return True

    def tightest(s):
        best = float("inf")
        for key, i in uses[s]:
            ch = network.patterns[key].chainage_m
            if 0 < i < len(ch) - 1:
                best = min(best, ch[i] - ch[i - 1], ch[i + 1] - ch[i])
        return best

    order = sorted((s for s in uses if s not in protected), key=lambda s: (len(uses[s]), tightest(s)))
    removed = []
    for s in order:
        if removable(s):
            for key, i in uses[s]:
                kept[key][i] = False
            removed.append(s)

    new = network.copy()
    for key, p in network.patterns.items():
        k = kept[key]
        new.patterns[key] = Pattern(p.route_id, p.direction,
                                    [s for s, keep in zip(p.stop_ids, k) if keep],
                                    [c for c, keep in zip(p.chainage_m, k) if keep],
                                    p.path, p.path_source)
    occurrences = sum(len(uses[s]) for s in removed)
    return new, {"removed_stops": removed, "removed_stop_visits": occurrences,
                 "min_gap_m": min_gap_m, "max_gap_after_m": max_gap_after_m}
