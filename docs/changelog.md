# Changelog

All the work below was done on 23 October 2026. It was made on the branch
`network-efficiency-metrics` and merged into `main` through pull requests. Each commit
does one thing, so `git show <hash>` explains a single step.

## Before this work

`a7a1ea5` to `c892452`: the AYNA scraper (`ayna_scraper.py`) and the network database
(`ayna.db`) were uploaded to the repository root.

## Pull request #4, merged as `18052a7`

| Commit | Change |
|---|---|
| `1169b6f` | Move the AYNA database and scraper into `data/` |
| `a31b2f6` | Add `.gitignore`. At this point it excluded `output/` and `data/external/`; pull request #5 reversed that |
| `38559af` | Add the `busnet` package: load and repair the network, measure directness, detours, overlap, stop spacing and coverage |
| `f0d1b03` | Add `measure.py`, which writes the measures to `output/` |

## Pull request #5, merged as `9dea7fe`

| Commit | Change |
|---|---|
| `a35fffb` | Track all data and results in git: `.gitignore` now excludes only caches and `.DS_Store` |
| `1982414` | Add the public datasets: population, ridership, metro, statistics, OpenStreetMap |
| `a90bb5b` | Add `data/fetch_external.py` to download the public datasets again |
| `95e56d2` | Split each population hexagon into seven points |
| `00fba2c` | Load observed BakuBus boardings |
| `d59b8fc` | Add trip destinations from OpenStreetMap and metro stations |
| `5e59c87` | Model route headways, daily service and destination demand |
| `f90dcc2` | Read settings and data paths from `busnet.toml` |
| `23958a6` | Add the results from the default settings |

## Pull request #6, merged as `f8e7701`

| Commit | Change |
|---|---|
| `97e2108` | Move input loading into `busnet/inputs.py`, shared by both scripts |
| `ebba8f5` | Let stop balancing keep a given set of stops |
| `9660ca1` | Count every headway source in the daily service totals |
| `afea1d5` | Add GTFS export |
| `2d7d22c` | Add the redesign search (`busnet/optimize.py`) |
| `881d75d` | Add `redesign.py` to run the search and report the result |
| `fe1a6f1` | Regenerate results and add the first redesign |
| `90cedb9` | In `network.geojson`, mark a direction as straightened only if its path changed. Before, both directions of a route were marked when one was straightened |
| `32a78ca`, `42822d9`, `88fad72` | Add this documentation under `docs/` |
| `1c98e51` | Link the documentation from the README |
| `8f9b3c2` | Use the new repository name in the download script's user agent. The GitHub repository was renamed from `router_algorithm` to `route_efficiency`; GitHub redirects the old address |
| `1c974c0` | Rank redesign changes by counted boardings where they exist and by the waiting one more bus saves; never drop a route with 1,000 or more counted boardings; leave protected routes (180) alone |
| `5636bec` | Regenerate results with the updated redesign: 595, 149 and 140E are no longer dropped |
| `38e067a` | Update the docs for the updated redesign |
