# Configuration

Every assumption and every data path lives in `busnet.toml` at the repository root. The
defaults are defined once, in `busnet/assumptions.py`; `busnet.toml` repeats them with
their sources so they can be read and changed in one place.

## How settings are read

`busnet/config.py` reads the file and builds the settings:

- The `[data]` table holds file paths. Relative paths are read relative to the folder of
  the settings file.
- Every other table only groups settings for readers: `[walking]`, `[service]`, `[speed]`,
  `[fuel]`, `[demand]` and `[redesign]` are flattened, so their keys must be setting names
  (the names in the tables below).
- Three settings are tables themselves: `[headway_by_zone]`, `[cruise_kmh]` and
  `[destination_weights]`. Values given there are merged with the defaults, so you can
  change one zone or one destination kind and keep the rest.
- A name that is not a setting stops the run with `Settings error: unknown setting(s)`,
  listing the valid names, so a typo is never silently ignored.
- `--set name=value` overrides one setting (or one data path) for a single run. The value
  is read as TOML: `--set default_headway_min=10`, `--set headway_from_ridership=false`,
  `--set 'headway_by_zone={"Şəhərdaxili" = 8}'`. It can be repeated.
- `--config other.toml` uses another file; `--config none` uses the built-in defaults.
- Every run records the settings it used in `output/network.json` (and
  `output/redesign/summary.json`) under `settings`, and the data files it found under
  `inputs`.

## Data paths (`[data]`)

| Key | Default in busnet.toml | Contents |
|---|---|---|
| `db` | `data/ayna.db` | The AYNA network snapshot (required) |
| `population` | `data/external/kontur/kontur_population_AZ_20231101.gpkg` | Population grid (.gpkg or a CSV with latitude, longitude, population) |
| `ridership` | `data/external/opendata/bakubus_passenger-2026.csv` | Daily boardings per route |
| `headways` | `data/headways.csv` | Real headways: `route,headway_min[,source]` |
| `destinations` | five `data/external/osm/osm_*.json` files | OpenStreetMap features from Overpass |
| `metro_passengers` | `data/external/opendata/metro_passengers-2026.csv` | Daily entries per metro station |
| `metro_exits` | `data/external/opendata/metro_exits.csv` | Metro exit coordinates |

A missing file is reported (`missing ...: (using assumptions instead)`) and the run goes on
without it: no population means no coverage, access or redesign; no ridership means
headways come from the zone table; no destinations means trips end at homes only.

## Walking (`[walking]`)

| Setting | Default | Meaning | Source or reason |
|---|---|---|---|
| `walk_speed_mps` | 1.25 | Walking speed, metres per second (4.5 km/h) | Common planning value |
| `walk_detour` | 1.3 | Street distance divided by straight-line distance when walking | Common planning value |
| `max_access_walk_m` | 500 | Furthest straight-line walk between a home or destination and a stop; also the distance the redesign's coverage guard protects | Planning practice (400 to 500 m) |
| `max_transfer_walk_m` | 300 | Furthest walk between stops when changing buses | Keeps transfers realistic |
| `coverage_radius_m` | 400 | A person counts as served with a stop within this distance | TCQSM convention; TransLink uses 450 m |

## Service frequency and transfers (`[service]`, `[headway_by_zone]`)

Each route's headway (minutes between buses) is the first of: a row in `data/headways.csv`;
an estimate from observed boardings when `headway_from_ridership` is on; the value for its
working zone in `[headway_by_zone]`; `default_headway_min`.

| Setting | Default | Meaning | Source or reason |
|---|---|---|---|
| `default_headway_min` | 12 | Headway for a route with no better information | Assumption |
| `headway_from_ridership` | true | Estimate BakuBus headways from their observed boardings | Uses the opendata.az counts |
| `boardings_per_trip` | 60 | Average boardings on one one-way trip of a 12 m bus, used for that estimate | Assumption; checked through the fleet total |
| `service_hours` | 17 | Hours of service a day (06:00 to 23:00) | Assumption |
| `min_headway_min` | 3 | Shortest headway allowed | Practical limit |
| `max_headway_min` | 30 | Longest headway allowed for estimates, and the floor of service the redesign keeps on every route | Planning practice |
| `transfer_penalty_min` | 5 | Extra minutes a rider perceives for each change, on top of waiting | Usual value in the literature |
| `layover_share` | 0.15 | Recovery time at terminals as a share of running time (for fleet size) | Assumption |
| `reference_fleet` | 2300 | Buses in daily service, all operators | Ministry of Digital Development, January 2026 |
| `headway_by_zone` | urban 10, urban express 15, suburban 15, suburban express 20, within a settlement 20, between settlements 20, intercity 30 | Headway by working zone (keys are the Azerbaijani zone names) | Assumption |

The estimated headways imply 2,015 buses in service, 88% of `reference_fleet`, which
suggests they are realistic.

## Speed (`[speed]`, `[cruise_kmh]`)

| Setting | Default | Meaning | Source or reason |
|---|---|---|---|
| `cruise_kmh` | urban 22, urban express 29, suburban 29, suburban express 36, within a settlement 25, between settlements 31, intercity 40 | Moving speed between stops by working zone, km/h | Calibrated so the network-wide average speed is 22 km/h, the figure AYNA reported in November 2024 |
| `default_cruise_kmh` | 25 | Moving speed for a zone not in the table | Assumption |
| `stop_loss_s` | 20 | Seconds lost at every stop: slowing, doors, pulling out (boarding time excluded) | nMotion 2015 (about 20 s); WMATA 10 to 20 s |

## Fuel and emissions (`[fuel]`)

| Setting | Default | Meaning | Source or reason |
|---|---|---|---|
| `fuel_l_per_km` | 0.30 | Diesel-equivalent litres per km of steady driving, 12 m bus | With the next value, gives 43 L/100 km at 2.65 stops/km, the Braunschweig test cycle result for diesel buses (43.8 L/100 km, VTT 2012) |
| `fuel_l_per_stop` | 0.05 | Extra litres for one stop-start cycle | VTT 2012 measured 0.03 to 0.07 L |
| `co2_kg_per_l` | 2.67 | kg of CO₂ per litre of diesel, tank to wheel | IPCC 2006 |

Baku's BakuBus fleet is mostly CNG with a growing electric share; CNG buses use about 35%
more energy than diesel for similar CO₂ per km, so diesel-equivalent litres are a fair
common unit.

## Demand (`[demand]`, `[destination_weights]`)

| Setting | Default | Meaning | Source or reason |
|---|---|---|---|
| `trip_decay_km` | 6.0 | Trips between two places fall off as exp(−distance / this) | Assumption; gives an average trip of 8 km in a straight line. The official average bus trip is 15.6 km (2025) but includes intercity buses |
| `max_trip_min` | 120 | Door-to-door times above this count as "not possible" | Assumption |
| `destination_share` | 0.5 | Share of trip ends drawn to destinations rather than homes (0 = homes only) | Assumption |
| `metro_weight_per_1000_entries` | 2.0 | Pull of a metro station per 1,000 weekday entries | Assumption |
| `destination_weights` | office 1, townhall 3, courthouse 3, kindergarten 1, school 3, college 5, university 10, clinic 2, hospital 8, supermarket 2, department_store 4, mall 10, marketplace 8, station 5, bus_station 5 | Pull of one OpenStreetMap feature of each kind | Assumption |

## Redesign search (`[redesign]`)

| Setting | Default | Meaning |
|---|---|---|
| `redesign_origins` | 100 | Trip origins in the search sample; more is slower and steadier |
| `redesign_seed` | 11 | Which origins are sampled; the final check uses another sample |
| `redesign_min_gain_min` | 0.005 | Smallest improvement in average minutes worth keeping |
| `redesign_max_straighten` | 80 | Detours to try straightening (the ones saving most time first) |
| `redesign_max_drop` | 20 | Routes with the fewest modelled riders per bus to try dropping |
| `redesign_max_people_losing_stop` | 500 | People one change may leave without any stop within `max_access_walk_m` |
| `redesign_max_people_losing_stop_total` | 3000 | The same, for all changes together |
| `redesign_shift_share` | 0.2 | Share of a route's buses moved in one frequency shift |
| `redesign_shift_rounds` | 4 | Rounds of frequency shifts |

## Which results depend on which settings

| Results | Depend on |
|---|---|
| Lengths, stop spacing, directness, duplication, corridors, near-duplicates, detours (except their minutes) | Only the data |
| Coverage | `coverage_radius_m`, population |
| Run times, stop-time share, detour minutes | `cruise_kmh`, `stop_loss_s` |
| Fuel and CO₂ | `fuel_l_per_km`, `fuel_l_per_stop`, `co2_kg_per_l`, plus headways for daily totals |
| Headways, daily trips, bus-hours, bus-km, fleet | The `[service]` settings, `data/headways.csv`, ridership |
| Door-to-door access, transfers, ridership check | Walking, service, speed and demand settings, population, destinations |
| Redesign | All of the above plus `[redesign]` |

## Examples

```sh
# riders feel a change as 8 extra minutes instead of 5
python3 measure.py --set transfer_penalty_min=8

# no change may leave anyone without a stop within reach
python3 redesign.py --set redesign_max_people_losing_stop=0 --set redesign_max_people_losing_stop_total=0

# a larger, steadier search sample
python3 redesign.py --set redesign_origins=200

# trips end at homes only
python3 measure.py --set destination_share=0
```
