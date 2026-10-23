#!/usr/bin/env python3
"""
Check how far the results depend on the sample of trips and on the assumptions.

results.md quotes four checks. This script runs them all and writes compact tables to
./output/robustness/ (or --out):
  fit_ladder.csv         how well the model ranks observed boardings as each input is added
  coverage_radius.csv    people within 300, 400, 500, 800 and 1,000 m of a served stop
  redesign_seeds.csv     today's network against the redesign on other samples of trips
  redesign_settings.csv  the redesign search again under other assumptions
  summary.json           the same figures with their averages, and the settings used

Standard library only. The redesign variants run redesign.py in parallel processes into a
temporary folder; only the tables above are kept. With 8 processes the whole run takes
about 10 minutes. Usage:
  python3 robustness.py
  python3 robustness.py --skip-settings    # fit ladder, coverage and seeds only (about 5 minutes)
  python3 robustness.py --jobs 4           # fewer parallel redesign runs
"""

import argparse
import csv
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from busnet.destinations import zone_attraction                                # noqa: E402
from busnet.inputs import load_inputs                                          # noqa: E402
from busnet.metrics import compare_ridership, coverage_by_route, evaluate_od   # noqa: E402
from busnet.optimize import Context, Evaluator, Plan, search                   # noqa: E402
from busnet.population import load_population, stops_bbox                     # noqa: E402
from busnet.service import operations, route_headways                         # noqa: E402

RADII = (300, 400, 500, 800, 1000)
CHECK_ORIGINS = 300                      # origins per trip sample, as in the independent check

# The redesign search under other assumptions: (name, what it changes, --set overrides).
VARIANTS = [
    ("default", "The settings in busnet.toml", []),
    ("transfer_penalty_2", "Riders mind a change less: 2 minutes instead of 5", ["transfer_penalty_min=2"]),
    ("transfer_penalty_8", "Riders mind a change more: 8 minutes instead of 5", ["transfer_penalty_min=8"]),
    ("trip_decay_4", "Shorter trips: distance decay 4 km instead of 6", ["trip_decay_km=4"]),
    ("trip_decay_9", "Longer trips: distance decay 9 km instead of 6", ["trip_decay_km=9"]),
    ("homes_only", "Trips end at homes only, with no destinations", ["destination_share=0"]),
    ("boardings_per_trip_45", "Counted routes run more often: 45 boardings per trip instead of 60", ["boardings_per_trip=45"]),
    ("boardings_per_trip_80", "Counted routes run less often: 80 boardings per trip instead of 60", ["boardings_per_trip=80"]),
    ("walk_400", "People walk at most 400 m to a stop instead of 500", ["max_access_walk_m=400"]),
    ("origins_200", "A search sample twice as large: 200 origins instead of 100", ["redesign_origins=200"]),
    ("seed_23", "Another search sample of the same size: seed 23 instead of 11", ["redesign_seed=23"]),
    ("nobody_loses_stop", "No change may leave anyone without a stop within reach",
     ["redesign_max_people_losing_stop=0", "redesign_max_people_losing_stop_total=0"]),
]


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})


def capped(acc, a):
    """Average door-to-door minutes, counting trips that cannot be made in time at the limit."""
    r = acc["share_reachable"]
    return r * acc["mean_door_to_door_min"] + (1 - r) * a.max_trip_min


# ---------------------------------------------------------------- the four checks

def fit_ladder(inp, fine, fine_pull, say):
    """Spearman of modelled against observed boardings, adding one input at a time.

    The last step is the default run of measure.py; the step before it is the fair
    measure of the model, because it does not use the boardings it is checked against."""
    a, net = inp.a, inp.network
    flat = replace(a, headway_from_ridership=False, default_headway_min=12,
                   headway_by_zone={zone: 12 for zone in a.headway_by_zone})
    fair = replace(a, headway_from_ridership=False)
    steps = [
        ("One headway of 12 minutes for every route; trips to homes only", flat, None, None),
        ("Headways by service type; trips to homes only", fair, inp.supplied, None),
        ("Plus destinations (OpenStreetMap, metro)", fair, inp.supplied, fine_pull),
        ("Plus headways estimated from observed boardings (the default)", a, inp.supplied, fine_pull),
    ]
    rows = []
    for step, (inputs, ai, supplied, attraction) in enumerate(steps, 1):
        headways = route_headways(net, ai, inp.observed, supplied)
        acc = evaluate_od(net, ai, fine, CHECK_ORIGINS, headways=headways, attraction=attraction)
        _, fit = compare_ridership(net, acc["modelled_boardings"], inp.observed)
        ops = operations(net, ai, headways)[1]
        rows.append({"step": step, "inputs": inputs, "routes_compared": fit["routes_compared"],
                     "spearman": fit["spearman"], "pearson_of_log_shares": fit["pearson_of_log_shares"],
                     "fleet": ops["fleet"],
                     "headway_sources": " ".join(f"{k} {v}" for k, v in ops["headway_sources"].items() if v)})
        say(f"  {step}. {inputs}: Spearman {fit['spearman']:.2f}, fleet {ops['fleet']:,}")
    return rows


def coverage_curve(network, fine, say):
    """Share of people with a served stop within each radius."""
    total = sum(z[2] for z in fine)
    rows = []
    for radius in RADII:
        cov = coverage_by_route(network, fine, radius)
        covered = sum(z[2] for z, c in zip(fine, cov) if c)
        rows.append({"radius_m": radius, "population_within": covered, "share_population_covered": covered / total})
        say(f"  within {radius:,} m: {covered / total:.1%}")
    return rows


def redesign_seeds(inp, fine, fine_pull, seeds, say):
    """Today's network against the redesign on other samples of trips.

    The search itself is the one redesign.py runs (same settings, same search sample);
    only the trips it is checked on change. Seed 7 is the independent check in
    output/redesign/summary.json."""
    a, net = inp.a, inp.network
    today = Plan.from_headways(net, a, inp.headways)
    evaluator = Evaluator(net, a, inp.zones, inp.attraction, coverage_zones=fine,
                          n_origins=a.redesign_origins, seed=a.redesign_seed)
    plan, log, _, _ = search(today, evaluator, Context(net, a, evaluator, observed=inp.observed), say=lambda *_: None)
    say(f"  search reproduced: {len(log)} changes, {len(plan.fleet)} routes")
    hw_today, hw_plan = today.headways(a), plan.headways(a)
    rows = []
    for seed in seeds:
        before = evaluate_od(today.network, a, fine, CHECK_ORIGINS, seed=seed, headways=hw_today, attraction=fine_pull)
        after = evaluate_od(plan.network, a, fine, CHECK_ORIGINS, seed=seed, headways=hw_plan, attraction=fine_pull)
        row = {"seed": seed, "minutes_before": capped(before, a), "minutes_after": capped(after, a)}
        row["gain_min"] = row["minutes_before"] - row["minutes_after"]
        row.update({"mean_possible_before": before["mean_door_to_door_min"],
                    "mean_possible_after": after["mean_door_to_door_min"],
                    "reachable_before": before["share_reachable"], "reachable_after": after["share_reachable"]})
        rows.append(row)
        say(f"  seed {seed:>2}: {row['minutes_before']:.2f} -> {row['minutes_after']:.2f} min, gain {row['gain_min']:.3f}")
    return rows


def run_variant(name, overrides, config, tmp):
    """Run redesign.py with overrides into a temporary folder; return its summary and changes."""
    out = Path(tmp) / name
    cmd = [sys.executable, str(ROOT / "redesign.py"), "--out", str(out)]
    if config:
        cmd += ["--config", str(config)]
    for item in overrides:
        cmd += ["--set", item]
    done = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"redesign.py failed for variant {name}:\n{done.stderr.strip()[-2000:]}")
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    changes = []
    if (out / "changes.csv").exists():
        with open(out / "changes.csv", newline="", encoding="utf-8-sig") as f:
            changes = list(csv.DictReader(f))
    return summary, changes


def settings_row(name, what, overrides, summary, changes):
    check = summary["independent_check"]
    minutes = summary["minutes_counting_impossible_trips_at_limit"]
    kinds = summary["changes"]
    ops_before = check["before"]["operations"]
    ops_saving = summary["fleet_saving_option"]["operations"]
    return {
        "variant": name, "what": what, "overrides": " ".join(overrides),
        "changes": sum(kinds.values()), "merges": kinds["merge"], "drops": kinds["drop"],
        "straightened": kinds["straighten"], "stop_balancing": kinds["stops"], "shifts": kinds["shift"],
        "routes_after": summary["routes_after"], "stops_after": check["after"]["served_stops"],
        "people_losing_stop": sum(float(c["people_losing_stop"]) for c in changes),
        "search_before": summary["search_sample"]["minutes_before"],
        "search_after": summary["search_sample"]["minutes_after"],
        "minutes_before": minutes["before"], "minutes_after": minutes["after"],
        "gain_min": minutes["before"] - minutes["after"],
        "mean_possible_before": check["before"]["accessibility"]["mean_door_to_door_min"],
        "mean_possible_after": check["after"]["accessibility"]["mean_door_to_door_min"],
        "share_of_fleet_for_todays_time": summary["share_of_fleet_for_todays_travel_time"]["independent_check"],
        "bus_hours_saving": 1 - ops_saving["bus_hours_per_day"] / ops_before["bus_hours_per_day"],
        "fuel_saving": 1 - ops_saving["fuel_l_per_day"] / ops_before["fuel_l_per_day"],
    }


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(ROOT / "busnet.toml"), help="settings file (TOML); 'none' for defaults only")
    ap.add_argument("--out", default=str(ROOT / "output" / "robustness"))
    ap.add_argument("--seeds", type=int, default=10, help="trip samples to score today's network and the redesign on")
    ap.add_argument("--jobs", type=int, default=max(1, min(8, (os.cpu_count() or 2) - 2)),
                    help="redesign variants to run at the same time")
    ap.add_argument("--skip-settings", action="store_true", help="do not run the redesign under other assumptions")
    args = ap.parse_args()

    config = None if args.config.lower() == "none" or not Path(args.config).exists() else str(Path(args.config).resolve())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        inp = load_inputs(ROOT, config, [], split=False)
    except (ValueError, TypeError) as e:
        sys.exit(f"Settings error: {e}")
    a, net = inp.a, inp.network
    if not inp.zones or not inp.observed:
        sys.exit("The robustness checks need population and ridership data: see data.population and data.ridership in busnet.toml")
    fine = load_population(inp.data["population"], stops_bbox(net), split=True)
    fine_pull = zone_attraction(fine, inp.points, a.destination_share)

    with tempfile.TemporaryDirectory() as tmp, ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {}
        if not args.skip_settings:
            print(f"Starting {len(VARIANTS)} redesign runs under other assumptions ({args.jobs} at a time) ...")
            futures = {name: pool.submit(run_variant, name, overrides, config, tmp) for name, _, overrides in VARIANTS}

        print("How well the model ranks observed boardings as inputs are added:")
        ladder = fit_ladder(inp, fine, fine_pull, print)
        print("People within reach of a stop:")
        coverage = coverage_curve(net, fine, print)
        seeds = list(range(1, args.seeds + 1))
        print(f"The redesign on {len(seeds)} samples of {CHECK_ORIGINS} origins:")
        seed_rows = redesign_seeds(inp, fine, fine_pull, seeds, print)
        write_csv(out / "fit_ladder.csv", ladder)              # on disk before the slow runs are collected
        write_csv(out / "coverage_radius.csv", coverage)
        write_csv(out / "redesign_seeds.csv", seed_rows)

        variants, failed = None, []
        if futures:
            print("Collecting the redesign runs ...")
            variants = []
            for name, what, overrides in VARIANTS:
                try:
                    summary, changes = futures[name].result()
                except Exception as e:                    # one failed run must not lose the others
                    failed.append(f"{name}: {e}")
                    continue
                variants.append(settings_row(name, what, overrides, summary, changes))
                row = variants[-1]
                print(f"  {name:<22} {row['changes']:>2} changes, {row['minutes_before']:.2f} -> {row['minutes_after']:.2f} min, "
                      f"{row['share_of_fleet_for_todays_time']:.0%} of the fleet for today's times")

    gains = [r["gain_min"] for r in seed_rows]
    summary = {
        "fit_ladder": ladder,
        "coverage_radius": coverage,
        "redesign_seeds": {
            "origins_per_sample": CHECK_ORIGINS, "rows": seed_rows,
            "gain_min": {"mean": statistics.mean(gains), "stdev": statistics.stdev(gains) if len(gains) > 1 else 0.0,
                         "min": min(gains), "max": max(gains), "positive": sum(g > 0 for g in gains), "samples": len(gains)},
        },
        "redesign_settings": None if failed else variants,
        "settings": asdict(a), "inputs": inp.found,
    }
    if variants and not failed:
        write_csv(out / "redesign_settings.csv", variants)
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    if failed:
        sys.exit("These redesign runs failed, so redesign_settings.csv was not written:\n  " + "\n  ".join(failed))

    committed = ROOT / "output" / "redesign" / "summary.json"
    if committed.exists():
        ref = json.loads(committed.read_text(encoding="utf-8"))["minutes_counting_impossible_trips_at_limit"]
        seven = next((r for r in seed_rows if r["seed"] == 7), None)
        if seven:
            same = abs(seven["minutes_before"] - ref["before"]) < 1e-6 and abs(seven["minutes_after"] - ref["after"]) < 1e-6
            print(f"\nSeed 7 {'reproduces' if same else 'DIFFERS FROM'} the committed independent check in output/redesign/summary.json")
    g = summary["redesign_seeds"]["gain_min"]
    print(f"Redesign gain over {g['samples']} trip samples: mean {g['mean']:.2f} min, stdev {g['stdev']:.2f}, "
          f"from {g['min']:.2f} to {g['max']:.2f}; positive in {g['positive']} of {g['samples']}")
    if variants:
        lo, hi = min(variants, key=lambda r: r["gain_min"]), max(variants, key=lambda r: r["gain_min"])
        print(f"Under other assumptions the gain runs from {lo['gain_min']:.2f} min ({lo['variant']}) "
              f"to {hi['gain_min']:.2f} min ({hi['variant']})")
    print(f"\nWrote {out.resolve()} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
