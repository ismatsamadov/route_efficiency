# Getting started

## Requirements

- Python 3.11 or newer (`python3 --version`). The settings reader uses `tomllib`, which
  arrived in 3.11.
- Nothing else. The code uses only Python's standard library, and every input file is in
  the repository, so no internet connection is needed to regenerate results.

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
and the redesign's plan arithmetic on a small made-up network, and regenerate `output/`
to compare it with the committed files ([code.md](code.md#checking-a-change)).

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
python3 data/fetch_external.py --only osm  # one group: kontur, opendata, stat or osm
```

Refreshing changes the inputs, so results will change. Commit refreshed data and the
regenerated `output/` together. OpenStreetMap queries go through public Overpass servers,
which are sometimes slow; the script retries and tries three servers, and you can run it
again for anything that failed.

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
