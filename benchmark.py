#!/usr/bin/env python3
"""
Test the redesign's search on the benchmark networks of the transit routing literature.

Mandl's network and Mumford's four (Mumford0 to Mumford3) come with published route sets
and scores: Mumford (2013), whose supplement is data/external/utrp/CEC2013Supp.zip. The
script first scores each published route set with busnet/utrp.py and sets the result
beside the published one, to show that the scoring is the literature's. Then it starts
from each published set and applies the one kind of change of the redesign that the
benchmark's rules allow, straightening detours, keeping a change only if the average
travel time falls: once as redesign.py does (one pass), and again with passes repeated
until one keeps nothing. Removing stops would make another network, and there are no
frequencies to shift.

Writes to ./output/benchmark/ (or --out):
  published.csv   each published route set scored here, beside its published scores
  search.csv      each search from a published set: what it tried and kept, the scores before and after
  changes.csv     every change kept, in order
  route_sets/     the route sets the searches end with, in the supplement's own format

Standard library only, about two minutes. Usage:
  python3 benchmark.py
"""

import argparse
import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from busnet.utrp import (RULES, evaluate, load_instance, matlab, problems,     # noqa: E402
                         published_route_sets, published_scores, search)

SUPPLEMENT = ROOT / "data" / "external" / "utrp" / "CEC2013Supp.zip"
SEARCHES = {"one_pass": False, "repeated": True}                  # name: repeat passes?
MEASURES = ("att", "d0", "d1", "d2", "dun", "route_time")


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})


def nodes(seq):
    return " ".join(str(v + 1) for v in seq)


def main():
    ap = argparse.ArgumentParser(description="Test the redesign's search on the UTRP benchmark networks.")
    ap.add_argument("--out", default=str(ROOT / "output" / "benchmark"), help="output folder")
    out = Path(ap.parse_args().out)
    (out / "route_sets").mkdir(parents=True, exist_ok=True)
    sets = published_route_sets(SUPPLEMENT)
    table = published_scores(SUPPLEMENT)
    published, searches, changes = [], [], []
    for name in RULES:
        inst = load_instance(SUPPLEMENT, name)
        for who in ("passenger", "operator"):
            routes = sets[(name, who)]
            score = evaluate(inst, routes)
            published.append({"network": name, "route_set": who, "routes": len(routes),
                              "nodes_min": min(map(len, routes)), "nodes_max": max(map(len, routes)),
                              "rules_broken": "; ".join(problems(inst, routes)),
                              **score, **{f"{k}_published": table[(name, who)][k] for k in MEASURES}})
            for kind, repeat in SEARCHES.items():
                t0 = time.time()
                final, before, after, log, tried = search(inst, routes, repeat=repeat)
                assert not problems(inst, final), problems(inst, final)
                searches.append({"network": name, "route_set": who, "search": kind, **tried, "changes": len(log),
                                 "att_before": before["att"], "att_after": after["att"],
                                 "att_change_pct": 100 * (after["att"] / before["att"] - 1),
                                 "route_time_before": before["route_time"], "route_time_after": after["route_time"],
                                 "route_time_change_pct": 100 * (after["route_time"] / before["route_time"] - 1),
                                 **{f"{k}_after": after[k] for k in ("d0", "d1", "d2", "dun")}})
                for step, entry in enumerate(log, 1):
                    c = entry["change"]
                    changes.append({"network": name, "route_set": who, "search": kind, "step": step,
                                    "pass": entry["pass"], "route": c.route + 1,
                                    "from_node": c.original[c.i] + 1, "to_node": c.original[c.j] + 1,
                                    "nodes_before": nodes(c.original[c.i:c.j + 1]),
                                    "nodes_after": nodes(c.new[c.i:len(c.new) - (len(c.original) - c.j - 1)]),
                                    "route_minutes_saved": c.saved_min,
                                    "att_before": entry["before"]["att"], "att_after": entry["after"]["att"],
                                    "route_time_before": entry["before"]["route_time"],
                                    "route_time_after": entry["after"]["route_time"]})
                if log:
                    head = (f"% {name}: Mumford (2013)'s route set best for {who}s after benchmark.py's "
                            f"{kind.replace('_', ' ')} straightening search\n"
                            f"% ATT {after['att']:.4f} (published set {before['att']:.4f}), "
                            f"route time {after['route_time']:.0f} ({before['route_time']:.0f})\n")
                    (out / "route_sets" / f"{name}_{who}_{kind}.txt").write_text(head + matlab(final) + "\n",
                                                                               encoding="utf-8")
                print(f"{name:9s} {who:9s} {kind:8s}  ATT {before['att']:6.2f} -> {after['att']:6.2f}   "
                      f"route time {before['route_time']:5.0f} -> {after['route_time']:5.0f}   "
                      f"{len(log):2d} changes kept of {tried['candidates']:4d} tried  ({time.time() - t0:.0f} s)")
    write_csv(out / "published.csv", published)
    write_csv(out / "search.csv", searches)
    write_csv(out / "changes.csv", changes)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
