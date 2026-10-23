# Changelog

All the work below was done on 23 October 2026. It was made on the branch
`network-efficiency-metrics` and merged into `main` through pull requests. Each commit
does one thing, so `git show <hash>` explains a single step.

## Before this work

`8cdf769` to `5cb3e92`: the AYNA scraper (`ayna_scraper.py`) and the network database
(`ayna.db`) were uploaded to the repository root.

## Pull request #4, merged as `ca18552`

| Commit | Change |
|---|---|
| `07b140a` | Move the AYNA database and scraper into `data/` |
| `b2100b6` | Add `.gitignore`. At this point it excluded `output/` and `data/external/`; pull request #5 reversed that |
| `f683b66` | Add the `busnet` package: load and repair the network, measure directness, detours, overlap, stop spacing and coverage |
| `08efb1b` | Add `measure.py`, which writes the measures to `output/` |

## Pull request #5, merged as `71b0d8f`

| Commit | Change |
|---|---|
| `a4dbdee` | Track all data and results in git: `.gitignore` now excludes only caches and `.DS_Store` |
| `c934cb6` | Add the public datasets: population, ridership, metro, statistics, OpenStreetMap |
| `47bd479` | Add `data/fetch_external.py` to download the public datasets again |
| `976f327` | Split each population hexagon into seven points |
| `e1640e6` | Load observed BakuBus boardings |
| `ffe51ae` | Add trip destinations from OpenStreetMap and metro stations |
| `506343a` | Model route headways, daily service and destination demand |
| `8c51ec9` | Read settings and data paths from `busnet.toml` |
| `5de0bad` | Add the results from the default settings |

## Pull request #6, merged as `3f36d62`

| Commit | Change |
|---|---|
| `c248406` | Move input loading into `busnet/inputs.py`, shared by both scripts |
| `9579c7c` | Let stop balancing keep a given set of stops |
| `60c69f7` | Count every headway source in the daily service totals |
| `9fb79fb` | Add GTFS export |
| `595cb1c` | Add the redesign search (`busnet/optimize.py`) |
| `f315e34` | Add `redesign.py` to run the search and report the result |
| `15473b6` | Regenerate results and add the first redesign |
| `076b8d5` | In `network.geojson`, mark a direction as straightened only if its path changed. Before, both directions of a route were marked when one was straightened |
| `a443946`, `3baf9d5`, `db3cdf3` | Add this documentation under `docs/` |
| `22e1c97` | Link the documentation from the README |
| `306bc2f` | Use the new repository name in the download script's user agent. The GitHub repository was renamed from `router_algorithm` to `route_efficiency`; GitHub redirects the old address |
| `dc34915` | Rank redesign changes by counted boardings where they exist and by the waiting one more bus saves; never drop a route with 1,000 or more counted boardings; leave protected routes (180) alone |
| `5ccdbdb` | Regenerate results with the updated redesign: 595, 149 and 140E are no longer dropped |
| `035a047` | Update the docs for the updated redesign |

## Pull request #8

| Commit | Change |
|---|---|
| `4728fe5` | Add `robustness.py` and `output/robustness/`: the redesign on ten samples of trips and under eleven other settings, the demand model's fit as each input is added, coverage by radius |
| `91337d0` | Add `tests/`: unit tests for the geometry, headways, settings and plans, and a regression test that regenerates `output/` and compares it with the committed files |
| `dc962b4` | Print the fleet-saving option in whole buses on the console, as results.md reports it |
| `37b9e61` | Document the robustness checks and the tests; state when the data is from; pair the population figures consistently; explain route 49's carrier |
| `639025f` | Check every cited figure in research.md against its source and correct the wording; mark unsourced settings as assumptions |
| `0db8e8f` | Record the licence and provenance of every dataset, including that `ayna.db` has no published licence |
| `3ddad62` | Add `docs/paper.md`: whether there is a paper, its outline mapped to the repository, pivots, venues checked on their own pages, format rules and the steps for an independent researcher |
| `9be5ef1` | Rewrite the narrative pages (README, the docs index, roadmap, results, research, redesign, data, paper) in the first person; the reference pages are unchanged |
| `4717ed9` | Add the MIT licence for the code, CC BY 4.0 for the documentation, `CITATION.cff`, and a Licensing section in the README stating each data folder's terms |
