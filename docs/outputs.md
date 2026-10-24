# Outputs

`measure.py` writes `output/`; `redesign.py` writes `output/redesign/`; `robustness.py`
writes `output/robustness/`; `site/build.py` writes the page's files in `site/`
([below](#sitedatajs-and-the-checklist-workbook)). CSV files are UTF-8 with a byte-order mark, so Excel shows
Azerbaijani letters correctly. Shares are
fractions between 0 and 1; distances are km or m as named; times are minutes unless named
otherwise. Blank cells mean "not defined" (for example the circuity of a loop route).

## output/routes.csv — one row per route with stops (201 rows)

| Column | Meaning |
|---|---|
| `route` | Route number as shown on the bus |
| `zone` | Working zone in English (Urban, Suburban, Between settlements, ...) |
| `region` | `Bakı` or `Sumqayıt` |
| `carrier` | Operator, as in the data (extra spaces removed) |
| `fare_azn` | Fare in manat |
| `stops_per_direction` | Stops per direction, averaged over directions |
| `one_way_km` | Length along the path, averaged over directions |
| `geometry` | `shape`, or `partly straight lines` when a direction has no usable shape |
| `shape` | `direct`, `indirect`, `very indirect` or `loop`, from the less direct direction |
| `median_stop_gap_m` | Median distance between consecutive stops |
| `gaps_under_200m`, `gaps_under_300m` | Number of stop gaps shorter than 200 m or 300 m, both directions |
| `end_to_end_circuity` | Path length ÷ straight line between the end stops |
| `excess_over_shortest_pct` | How much longer than the shortest path buses could take between the end stops, % |
| `rider_circuity` | Distance riders travel ÷ straight line, for stop pairs at least 1 km apart |
| `detours`, `detour_excess_km` | Number of detours and the extra km they add, both directions |
| `shared_share`, `heavy_shared_share` | Share of the route's length on links shared with at least one / five other routes |
| `round_trip_min` | Running time out and back |
| `stop_time_share` | Share of running time lost at stops |
| `fuel_l_round_trip`, `co2_kg_round_trip` | Fuel (diesel-equivalent litres) and CO₂ for one round trip |
| `population_within_radius` | People with a stop of this route within `coverage_radius_m` |
| `population_only_this_route` | People for whom this is the only route within that distance |
| `weekday_boardings` | Observed average weekday boardings in the latest month (BakuBus routes only) |
| `boardings_per_km` | `weekday_boardings` ÷ `one_way_km` |
| `headway_min`, `headway_source` | Minutes between buses and where the value came from: `supplied`, `ridership`, `zone` or `default` |
| `trips_per_day` | Trips a day, both directions |
| `fleet` | Buses needed, rounded up |
| `bus_hours_per_day`, `bus_km_per_day`, `fuel_l_per_day` | Daily service the headway implies |

## output/detours.csv — one row per detour (271 rows)

| Column | Meaning |
|---|---|
| `route`, `direction` | Route number and direction (1 or 2) |
| `from_stop`, `to_stop` | Stop names where the detour starts and ends |
| `stops_inside` | Stops between them |
| `inside_stops_only_this_route` | How many of those no other route serves |
| `along_km`, `straight_km`, `excess_km` | Distance along the route, straight line, and the difference |
| `extra_min_per_trip` | Minutes the detour adds to every trip through it |
| `population_only_this_route` | People near the inside stops who have no other route within `coverage_radius_m` |

## output/corridors.csv — stretches where at least 8 routes share every link (21 rows)

| Column | Meaning |
|---|---|
| `from_stop`, `to_stop` | First and last stop |
| `via_stop` | For an out-and-back stretch, the stop where it turns |
| `km`, `stops` | Length and number of stops |
| `mean_routes_per_link`, `max_routes_on_a_link` | Routes sharing each link, on average and at most |
| `routes` | Every route using any of its links |
| `stop_ids` | AYNA stop ids in order |

## output/duplicates.csv — near-duplicate route pairs (72 rows, 25 routes)

| Column | Meaning |
|---|---|
| `route` | The route mostly served by another |
| `inside_route` | The other route |
| `share_of_stops` | Share of `route`'s stops that `inside_route` also serves |
| `route_stops`, `other_route_stops` | Distinct stops of each |
| `same_carrier` | Whether both are run by the same operator |

## output/ridership_check.csv — observed against modelled boardings (56 rows)

| Column | Meaning |
|---|---|
| `route` | BakuBus route in the snapshot |
| `observed_weekday_boardings` | Observed weekday average, latest month |
| `observed_share`, `modelled_share` | Each route's share of the total over these routes |
| `modelled_over_observed` | Ratio of the two shares; above 1 means the model overrates the route |

## output/network.json

| Key | Meaning |
|---|---|
| `network.routes_with_stops`, `route_directions`, `served_stops` | Size of the network measured |
| `network.route_km_one_way_total` | Length of all route directions added up |
| `network.corridor_km`, `duplication_ratio` | Distinct stop-to-stop link km, and route-km per link km |
| `network.median_stop_gap_m`, `share_stop_gaps_under_200m`, `share_stop_gaps_under_300m` | Stop spacing |
| `network.most_routes_on_one_link` | The most routes sharing one link |
| `network.hours_one_trip_each_direction_every_route`, `share_of_that_time_lost_at_stops` | Running time for one trip in each direction of every route, and the share lost at stops |
| `network.fuel_l_one_trip_each_direction_every_route`, `share_of_that_fuel_from_stops` | The same for fuel |
| `network.area_within_coverage_radius_km2` | Area within `coverage_radius_m` of a stop |
| `network.population_in_study_area`, `population_within_coverage_radius`, `share_population_covered` | Coverage |
| `network.accessibility.*` | Door-to-door results: `mean_door_to_door_min` (trips possible within `max_trip_min`), `share_reachable`, `share_within_30_min` / `45` / `60`, `share_trips_without_stop_nearby`, `mean_trip_km_straight_line`, `transfers` (share of possible trips by changes: `walk only`, `0`, `1`, `2`, `3+`), `origins_sampled` |
| `network.operations.*` | Daily service: `trips_per_day`, `bus_hours_per_day`, `bus_km_per_day`, `fleet`, `fuel_l_per_day`, `co2_t_per_day`, `fleet_vs_reference`, `headway_sources` |
| `network.ridership_fit` | `routes_compared`, `spearman`, `pearson_of_log_shares` |
| `inputs` | The file used for each input, or null if it was missing |
| `settings` | Every setting used |
| `headway_sources` | Routes by headway source |
| `repairs` | The data repairs applied |

## output/scenario.json and output/scenario_removed_stops.csv

Written with `--scenario stop-balancing`. `scenario.json` holds `details`
(`removed_stops`, `removed_stop_visits` across all routes, `min_gap_m`, `max_gap_after_m`)
and the full network summary `before` and `after`, with the same keys as `network`
above. `scenario_removed_stops.csv` lists each removed stop: `stop_id`, `name`, `lat`, `lon`.

## output/repairs.txt

One line per data repair applied when loading `ayna.db` ([data.md](data.md#defects-repaired-automatically)).

## output/redesign/changes.csv — each change the search kept

| Column | Meaning |
|---|---|
| `step` | Order in which it was kept |
| `kind` | `merge`, `drop`, `straighten`, `stops` or `shift` |
| `routes` | The route changed (blank for network-wide changes) |
| `change` | What was done, in words |
| `minutes_before`, `minutes_after`, `gain_min` | Average door-to-door minutes on the search sample, counting impossible trips at 120 |
| `people_losing_stop` | People left without any stop within `max_access_walk_m` by this change (fractional because population points are fractions of hexagons) |

## output/redesign/routes.csv — every route before and after

| Column | Meaning |
|---|---|
| `route` | Route number |
| `status` | `kept`, `straightened` (at least one direction), `merged` or `dropped`. Stop balancing alone leaves a route `kept` |
| `protected` | `True` for routes listed in `redesign_protected_routes` |
| `boardings_per_day` | Boardings a weekday the search used for this route in today's network |
| `boardings_source` | `counted` (BakuBus counts on opendata.az) or `estimated` (the model's boardings, scaled so that model and counts agree in total on the counted routes) |
| `buses_before`, `buses_after` | Bus-equivalents assigned (fractional); `buses_after` is 0 for a merged or dropped route |
| `headway_min_before`, `headway_min_after` | Minutes between buses |
| `one_way_km_before`, `one_way_km_after` | Length, averaged over directions |

The `_after` headway and length are blank for merged and dropped routes.

## output/redesign/summary.json

| Key | Meaning |
|---|---|
| `fleet_buses` | Bus-equivalents held constant |
| `routes_before`, `routes_after` | Routes in each plan |
| `changes` | Number of kept changes by kind |
| `search_sample` | Origins, seed, and the average minutes and share of impossible trips before and after on the search sample |
| `minutes_counting_impossible_trips_at_limit` | The same average on the independent check, before and after |
| `share_of_fleet_for_todays_travel_time` | Share of the fleet that gives today's average trip with the new plan, on the independent check and on the search sample |
| `fleet_saving_option` | Bus-equivalents and daily service (`operations`) for that smaller fleet |
| `independent_check.before`, `independent_check.after` | `accessibility` and `operations` as in network.json, plus `served_stops`, `route_km_one_way_total`, `corridor_km`, `duplication_ratio`, `median_stop_gap_m`, `share_stop_gaps_under_300m`, `share_population_covered`. Here every headway comes from the plan's buses, so `headway_sources` counts them under `plan`, and `modelled_boardings` is left out |
| `settings`, `inputs` | As in network.json |

## output/redesign/network.geojson

One line feature per route direction of today's network (402), with `route`, `direction`,
`status` and a `stroke` colour that GitHub and most map tools use:

| `status` | Line drawn | Colour | Features in the latest run |
|---|---|---|---|
| `kept` | The path after the redesign (stop balancing does not move it) | blue `#2a78d6` | 372 |
| `straightened` | The new path of a direction whose detour was straightened | green `#1baf7a` | 14 |
| `dropped` | The old path of a direction of a merged or dropped route | red `#d03b3b` | 16 |

Merged routes are drawn as `dropped`; `routes.csv` tells merges and drops apart.

## output/redesign/gtfs_today.zip and gtfs_redesign.zip

GTFS feeds with `agency.txt`, `stops.txt`, `routes.txt`, `calendar.txt`, `trips.txt`,
`stop_times.txt`, `shapes.txt` and `frequencies.txt`. Each route direction is one trip
that repeats every headway from 06:00 to 23:00, every day of 2026. Stop and route ids are
AYNA's. Stop times come from the travel model, so the feeds describe the model, not an
official timetable.

## output/robustness/fit_ladder.csv — the demand model as each input is added (4 rows)

| Column | Meaning |
|---|---|
| `step`, `inputs` | The step and the inputs the model had: flat 12-minute headways and homes only; headways by service type; plus destinations; plus headways from boardings (the default) |
| `routes_compared` | BakuBus routes in both the model and the counts (56) |
| `spearman`, `pearson_of_log_shares` | As `ridership_fit` in `network.json` |
| `fleet` | Buses the headways of that step imply |
| `headway_sources` | Routes by headway source in that step |

## output/robustness/coverage_radius.csv — people within reach of a stop (5 rows)

| Column | Meaning |
|---|---|
| `radius_m` | 300, 400, 500, 800 or 1,000 m |
| `population_within`, `share_population_covered` | People, and their share of the study area, with a served stop within that distance |

## output/robustness/redesign_seeds.csv — the redesign on other samples of trips (10 rows)

The search is the one `redesign.py` ran; only the trips it is checked on change. Seed 7
is the independent check in `redesign/summary.json`.

| Column | Meaning |
|---|---|
| `seed` | Which 300 origins were sampled |
| `minutes_before`, `minutes_after`, `gain_min` | Average door-to-door minutes, counting a trip that cannot be made within 2 hours as 120, for today's network and the redesign, and the difference |
| `mean_possible_before`, `mean_possible_after` | Average over the trips that can be made |
| `reachable_before`, `reachable_after` | Share of trips that can be made within 2 hours |

## output/robustness/redesign_settings.csv — the search under other assumptions (15 rows)

One row per run of `redesign.py`, the first with the committed settings.

| Column | Meaning |
|---|---|
| `variant`, `what`, `overrides` | A short name, what was changed, and the `--set` values used |
| `changes`, `merges`, `drops`, `straightened`, `stop_balancing`, `shifts` | Changes kept, in total and by kind |
| `routes_after`, `stops_after` | The redesigned network's size |
| `people_losing_stop` | People left without a stop within `max_access_walk_m`, all changes together |
| `search_before`, `search_after` | Average minutes on the search sample (impossible trips at 120) |
| `minutes_before`, `minutes_after`, `gain_min` | The same on the independent check, and the difference |
| `mean_possible_before`, `mean_possible_after` | Average over the trips that can be made, on the independent check |
| `share_of_fleet_for_todays_time` | Share of the fleet that gives today's average trip with the redesign |
| `bus_hours_saving`, `fuel_saving` | What that fleet saves a day, as shares |

## output/robustness/summary.json

`fit_ladder`, `coverage_radius` and `redesign_settings`: the rows of those tables as
lists. `redesign_seeds`: an object with `origins_per_sample` (300), `rows` (the table)
and `gain_min` (the mean, standard deviation, minimum, maximum, count of positive gains
and number of samples). Then the `settings` and `inputs` used.

## site/data.js and the checklist workbook

`site/build.py` writes `data.js` and `checklist.xlsx` for the page in `index.html`, and
with `--og` the link-preview picture `og.png`; none of them is read by the other scripts.

`site/data.js` assigns one object to `window.SITE_DATA`. `meta` holds the dates of the
map data (`scraped`, `same_as`), the month of the BakuBus counts, the coverage radius, the
transfer walk and the time lost per stop (from the settings) and the links, and the travel model's settings (walking speed and detour, change penalty,
longest trip, and how many headways come from each source). `summary` holds the figures the page quotes, taken from `network.json` and the
CSV files: routes, directions and stops, routes per shape class, detours and their extra
km, the detours where nobody depends on the route alone and those with a shorter path,
near-duplicate pairs and those with two carriers, corridors, routes per link, closely
spaced stops, population and covered population.
`issues` holds `repairs` (each line of `repairs.txt` as route, direction, kind and text)
and the defects the repairs do not cover: `no_stops` and `no_shape` (route numbers),
`straight_directions`, `length_round_trip_median`, `duration_formula` (routes whose
`duration_min` equals `floor(route_length_km / 0.6)`, of `routes_in_table`),
`missing_from_map` (counted routes that are not in the map data), `cyrillic_names`,
`shared_names`, `shared_names_far_apart` and `unnamed_unused_stops`. Then the data the
map draws: `stops` (served stops as latitude, longitude, name and AYNA stop id, referred
to by position), `routes` (one object per route with the figures of `routes.csv`, its
estimated headway and its source, its cruise speed and, for each direction, its line, its
stops and the length of every hop), `detours` (the rows of `detours.csv` with their
line and end stops, and `alt`: the shorter path's line, km, km and minutes saved and the
stops it skips, or null), `duplicates`, `corridors` (with their line and routes),
`spacing` (the stops stop balancing removes, each with its shortest distance along a route
to a neighbour, and the scenario's stop visits, hours saved and residents left without a
stop within the coverage radius, from `scenario.json`) and `hexes` (each population
hexagon with people farther than the coverage radius from a stop: its outline, those
people and everyone in it), and `carriers` (one row per carrier, spelling variants
combined: its routes, one-way km, direct routes, median path / straight line, detours and
their km, routes mostly inside another route, closely spaced stops it serves, residents
only one of its routes reaches, and counted boardings). Lines are encoded polylines with
5 decimals; stop coordinates have 6.

`site/checklist.xlsx` holds the lists, one sheet each, with frozen headers and filters:

| Sheet | Rows | Columns |
|---|---|---|
| About | the source, the dates and the definitions | one |
| Data issues | 40: the 23 repairs, the 2 routes without a line, the 7 without stops and the 8 counted routes missing from the map | route, direction, issue, what would fix it |
| Detours | 271, longest extra time first | route, direction, from and to stop, stops inside and those only this route serves, km along the route and in a straight line, extra km, extra minutes per trip (an estimate), residents only this route reaches, whether everyone inside has another route; for the 134 with a shorter path its km, the km and minutes (an estimate) it saves and the stops it skips |
| Near-duplicate routes | 72 | route and carrier, the route that serves most of its stops and its carrier, share of stops shared, stops of each, same carrier |
| Corridors | 21 | from, to, turning point, km, stops, routes per link (mean and busiest link), routes |
| Close stops | 351, closest first | stop name, AYNA stop id, shortest distance along a route to a neighbouring stop, routes |
| Carriers | 39, most routes first | carrier, other spellings, routes and their numbers, one-way km, direct routes, median path / straight line, detours and their km, routes mostly inside another route and those inside another carrier's, close stops served, residents only one of its routes reaches, weekday boardings |
| Routes | 201 | the measured columns of `routes.csv`, without the modelled headways, fleet and fuel |
