# Outputs

`measure.py` writes `output/`; `redesign.py` writes `output/redesign/`. CSV files are
UTF-8 with a byte-order mark, so Excel shows Azerbaijani letters correctly. Shares are
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
| `kept` | The path after the redesign (stop balancing does not move it) | blue `#2a78d6` | 370 |
| `straightened` | The new path of a direction whose detour was straightened | green `#1baf7a` | 14 |
| `dropped` | The old path of a direction of a merged or dropped route | red `#d03b3b` | 18 |

Merged routes are drawn as `dropped`; `routes.csv` tells merges and drops apart.

## output/redesign/gtfs_today.zip and gtfs_redesign.zip

GTFS feeds with `agency.txt`, `stops.txt`, `routes.txt`, `calendar.txt`, `trips.txt`,
`stop_times.txt`, `shapes.txt` and `frequencies.txt`. Each route direction is one trip
that repeats every headway from 06:00 to 23:00, every day of 2026. Stop and route ids are
AYNA's. Stop times come from the travel model, so the feeds describe the model, not an
official timetable.
