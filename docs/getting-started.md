# Getting started

## Requirements

- Python 3.11 or newer (`python3 --version`). The settings reader uses `tomllib`, which
  arrived in 3.11.
- Nothing else. The code uses only Python's standard library, and every input file is in
  the repository, so no internet connection is needed to regenerate results.
- Only for the optional check of the GTFS feeds: Java 17 or newer and MobilityData's
  validator ([below](#checking-the-gtfs-feeds)).

## Regenerate every result

From the repository root:

```sh
python3 measure.py --scenario stop-balancing --min-gap 250
python3 redesign.py
python3 robustness.py
```

| Command | Writes | Time |
|---|---|---|
| `python3 measure.py` | `output/` measures of today's network | about 8 s |
| `python3 measure.py --scenario stop-balancing --min-gap 250` | the same, plus `output/scenario.json` and `output/scenario_removed_stops.csv` | about 12 s |
| `python3 redesign.py` | `output/redesign/` | about 2 minutes |
| `python3 robustness.py` | `output/robustness/`: the results on other trip samples and under other assumptions | about 15 minutes (8 processes) |
| `python3 site/build.py` | `site/data.js` and `site/checklist.xlsx`, the page's data, from `output/`; with `--og` also `site/og.png` (needs Chrome) | about 3 s |

The committed `output/` folder was produced by exactly these three commands. Running
them again gives byte-identical files: random sampling uses fixed seeds and every list
is sorted before use. This was checked on a fresh clone of the repository. One caveat:
Python 3.12 changed how `sum()` adds floats, so Python 3.11 can differ from the
committed files in the last digits of some numbers; the regression test allows that.

## Run the tests

```sh
python3 -m unittest                            # about 15 s
BUSNET_SLOW_TESTS=1 python3 -m unittest        # also regenerates the redesign and the robustness checks, about 20 minutes
```

The tests check the geometry, the headway and daily-service rules, the settings reader
and the redesign's plan arithmetic on a small made-up network, regenerate `output/`
to compare it with the committed files, and rebuild the page's data and checklists to
compare them with the committed ones ([code.md](code.md#checking-a-change)).

## See the page

```sh
python3 site/build.py --og     # after any change to output/
python3 -m http.server         # then open http://localhost:8000/ (or /#tour for the tour)
```

`index.html` is the page for readers of the results ([code.md](code.md#the-page)). It
needs an internet connection for the map library and the base map tiles; everything
else is in the repository. GitHub Pages publishes it when Settings → Pages is set to
deploy from the branch `main`, folder `/ (root)`.

## Checking the GTFS feeds

The two feeds in `output/redesign/` can be checked with MobilityData's canonical GTFS
validator, the same checker the R package gtfstools runs with `validate_gtfs()`. It is a
Java program and not part of the repository: install Java 17 or newer, download
`gtfs-validator-8.0.1-cli.jar` from the validator's
[releases page](https://github.com/MobilityData/gtfs-validator/releases), then run

```sh
python3 validate_gtfs.py --jar path/to/gtfs-validator-8.0.1-cli.jar   # under a minute
```

`--java` names the Java executable if it is not on the PATH, and `--date` the date the
validator's date rules use (26 October 2026 by default, so that a rerun gives the same
files). It writes `output/gtfs_validation/notices.csv` and `stops_far_from_shape.csv`
([outputs.md](outputs.md#outputgtfs_validation--what-the-gtfs-validator-says-about-the-feeds));
run it again whenever `redesign.py` changes the feeds. Version 8.0.1 finds no errors in
either feed.

## Change something and see the effect

1. Edit a value in `busnet.toml` (see [configuration.md](configuration.md)), or add real
   data, for example real headways in `data/headways.csv`.
2. Run the three commands again.
3. `git diff output/` shows what changed in every result.

To try a value once without editing the file:

```sh
python3 measure.py --set transfer_penalty_min=8
python3 redesign.py --set redesign_max_people_losing_stop=0 --out output/redesign_strict
```

`--set` can be repeated. `--config none` ignores `busnet.toml` and uses the built-in
defaults (and then finds no data files except `data/ayna.db`).

## Refresh the public data

```sh
python3 data/fetch_external.py             # download only files that are missing
python3 data/fetch_external.py --refresh   # download everything again
python3 data/fetch_external.py --only osm  # one group: kontur, opendata, stat, osm or wikidata
                                           # (osm also cuts the walking network out of Geofabrik's 47 MB extract, about a minute)
python3 data/metro_scraper.py              # the metro's own API again (about 20 requests)
python3 data/build_metro.py                # rebuild data/metro/ from the downloads
```

Refreshing changes the inputs, so results will change. Commit refreshed data and the
regenerated `output/` together. OpenStreetMap queries go through public Overpass servers,
which are sometimes slow; the script retries and tries three servers, and you can run it
again for anything that failed. It prints the date of the OpenStreetMap data each server
answered with: a mirror can be months behind, and then the file is better fetched again
later. Nothing reads `data/metro/` yet, so the metro scripts do not change the results.

## Messages you may see

| Message | Meaning | What to do |
|---|---|---|
| `Settings error: unknown setting(s): ...` | A name in `busnet.toml` or `--set` is misspelled | Use one of the names the message lists |
| `missing population: ... (using assumptions instead)` | A data file named in `busnet.toml` is not there | Restore it with `data/fetch_external.py`, or accept that the related measures are skipped |
| `metro stations without exit coordinates: ...` | A metro station name could not be matched to an exit | Check the names in the two metro files |
| `ModuleNotFoundError: No module named 'tomllib'` | Python older than 3.11 | Use Python 3.11 or newer |
| `The redesign needs population data` | `redesign.py` without a population file | Restore the Kontur file |

## Where to go next

- Results so far: [results.md](results.md)
- How the numbers are made: [methodology.md](methodology.md)
- How the redesign works: [redesign.md](redesign.md)
