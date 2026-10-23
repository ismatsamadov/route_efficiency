# Methodology

How every number in `output/` is made. Module names refer to files in `busnet/`.
Settings in `code` font are in `busnet.toml` ([configuration.md](configuration.md)).

```mermaid
flowchart LR
  db[(ayna.db)] --> repair[Load and repair<br/>model.py]
  repair --> geo[Geometry measures<br/>metrics.py]
  repair --> svc[Headways and daily service<br/>service.py]
  rid[(BakuBus boardings)] --> svc
  hw[(headways.csv)] --> svc
  pop[(Population)] --> dem[Demand<br/>destinations.py, metrics.py]
  osm[(OSM and metro)] --> dem
  svc --> j[Door-to-door trips<br/>graph.py, metrics.py]
  dem --> j
  j --> check[Ridership check]
  rid --> check
```

## 1. Loading and repairing the network

`model.py` reads `ayna.db` into routes, stops and patterns. A pattern is one direction of
one route: its ordered stops, the path between them, and the distance along that path at
each stop (its chainage).

Repairs, applied in this order (each is logged to `output/repairs.txt`):

1. **Repeated stop lists.** A direction whose stop list is the same list twice back to
   back keeps one copy.
2. **Unusable coordinates.** A shape whose latitude equals its longitude on every point is
   dropped. A shape whose median point lies more than 50 km from the median of the route's
   stops is tried with latitude and longitude swapped; if that brings it within 50 km it is
   swapped back, otherwise it is dropped.
3. **Matching stops to shapes** (`geo.match_stops`). Every stop is projected onto every
   segment of the shape. For each stop, the candidates are the closest point of each run of
   segments within 150 m of the stop's nearest distance. A dynamic program then chooses one
   candidate per stop so that the distance along the shape never goes back by more than
   30 m from one stop to the next, with the smallest total offset. A stop with no in-order
   candidate is an **order break**. A shape's fit is (order breaks, median offset).
4. **Which shape belongs to which direction.** Each direction is scored against each
   stored shape and its reverse, and the better of the two is kept. Today's assignment is
   replaced by the alternative (swapped directions, or a lone shape moved to the other
   direction) only on clear evidence: at least max(2, 20% of the route's stops) fewer order
   breaks, or no more breaks and a total median offset below 70% of the current one. A
   shape that fits better reversed is reversed.
5. **Quality gate.** A shape is dropped, and its direction drawn as straight lines between
   stops, if it has more than max(2, 10% of its stops) order breaks, a median offset over
   60 m, or any straight segment longer than 5 km.
6. **Chainage.** The distance along the shape at each stop, starting at zero at the first
   stop. Each hop is at least the straight-line distance between its two stops, which also
   absorbs the occasional stop matched slightly out of order. The stored path runs from the
   first stop to the last.

## 2. Geometry measures

All distances are great-circle (haversine). Grids and buffers use a flat projection
centred on Baku, accurate to better than 1% across the area.

| Measure | Definition |
|---|---|
| One-way length | Chainage of the last stop, averaged over the route's directions |
| Stop gap | Distance along the path between consecutive stops |
| End-to-end circuity | Path length ÷ straight line between the first and last stop (not defined when they are less than 1 km apart) |
| Shape class | Direct up to 1.4; indirect 1.4 to 2; very indirect 2 to 3; loop over 3 or ends less than 1 km apart. A route takes its less direct direction |
| Excess over shortest path | Path length ÷ shortest path between the same two stops, minus 1. The shortest path runs on a graph of every stop-to-stop link some route drives (both ways), plus links between stops less than 80 m apart |
| Rider circuity | For every pair of stops on the direction at least 1 km apart: distance along the route ÷ straight line; averaged |
| Detour | A stretch from stop i to stop j (at most 12 stops and 40% of the route) whose path is at least 2.5 times the straight line and at least 1.5 km longer than it. Overlapping detours keep the largest |
| Extra minutes of a detour | Extra distance ÷ moving speed + stops inside × `stop_loss_s` |
| Shared share | Share of a direction's length on links that at least one other route also uses (heavy: at least five routes) |
| Duplication ratio | Total route-km of all directions ÷ km of distinct directed stop-to-stop links |
| Trunk corridor | A run of consecutive links on which at least 8 routes share every link, at least 1 km long. When it starts and ends within 1 km (out and back), the stop farthest from the start is named as the turn |
| Near-duplicate | A route (at least 10 stops) with at least 85% of its stops also served by one other route; express routes are left out |

## 3. Running time, fuel and CO₂ per trip

For one trip in one direction (`service.py`):

- running time = length ÷ `cruise_kmh` for the route's zone + (stops − 1) × `stop_loss_s`
- fuel = length in km × `fuel_l_per_km` + (stops − 1) × `fuel_l_per_stop`
- CO₂ = fuel × `co2_kg_per_l`

With the defaults, total route-km divided by total running time over all directions is
22 km/h, the bus speed AYNA reported in November 2024.

## 4. Headways and daily service

Each route's headway is the first of (`service.route_headways`):

1. **supplied**: a row in `data/headways.csv`;
2. **ridership**, when `headway_from_ridership` is on and the route has observed boardings:
   trips per direction = weekday boardings ÷ 2 ÷ `boardings_per_trip`, and
   headway = `service_hours` × 60 ÷ trips, kept between `min_headway_min` and `max_headway_min`;
3. **zone**: `headway_by_zone` for the route's working zone;
4. **default**: `default_headway_min`.

Today: 1 supplied (H1), 55 from ridership, 145 by zone. Daily service per route
(`service.operations`), with both directions:

- trips a day = 2 × `service_hours` × 60 ÷ headway
- bus-hours a day = trips a day ÷ 2 × round-trip running time
- bus-km a day and fuel a day follow the same way from length and fuel per trip
- buses needed = round-trip running time × (1 + `layover_share`) ÷ headway, rounded up per route

The network totals are compared with `reference_fleet`: 2,015 buses, 88% of 2,300.

## 5. Population and coverage

`population.py` reads the Kontur hexagons in the box around the served stops plus 2 km.
Each hexagon becomes seven points that share its population: its centre and six points
at a third of the hexagon's width around it, the way H3 divides a cell into seven.

- **Coverage**: people at points with a served stop within `coverage_radius_m`.
- **Area within the radius**: 100 m grid cells whose centre is within the radius of a stop.
- **People only one route serves**: people whose only routes within the radius are that one.

## 6. Demand

No origin-destination data is public, so trips are spread with a gravity model:

- Trips start at homes. Origins are sampled in proportion to population (300 origins,
  seed 7, for the measures).
- From each origin, trips end at every zone in proportion to its pull × exp(−distance ÷
  `trip_decay_km`), and each origin's trips add up to one.
- A zone's pull = (1 − `destination_share`) × its population + `destination_share` × total
  population × its share of all destination weight (`destinations.zone_attraction`).
- Destination weight comes from OpenStreetMap features (`destination_weights` by kind)
  and metro exits (`metro_weight_per_1000_entries` per 1,000 weekday entries at the
  station, split across its exits). Each feature is credited to its nearest zone within 1.5 km.

## 7. Door-to-door trips

`graph.TransitGraph` holds, for every served stop, an arrival node and a departure node,
and for every route direction a chain of on-board nodes:

| Link | Cost |
|---|---|
| Departure at a stop → board a route | half the route's headway + `transfer_penalty_min` |
| On board → next stop of the same route | hop distance ÷ moving speed + `stop_loss_s` |
| On board → get off (arrival node) | 0 |
| Arrival → departure at the same stop | 0 |
| Arrival → departure at another stop within `max_transfer_walk_m` | walking time |

Walking time = straight-line distance × `walk_detour` ÷ `walk_speed_mps`. Walking happens
once between rides, never chained.

A trip walks from its origin point to any stop within `max_access_walk_m`, follows the
cheapest path (Dijkstra's algorithm, up to `max_trip_min`), and walks from a stop within
`max_access_walk_m` to its destination. Every boarding pays the transfer penalty, so one
penalty is taken off at the end: the first boarding is not a change. Trips under 2 km may
also be walked entirely, whichever is quicker.

Reported (`accessibility` in `output/network.json`): the mean door-to-door time of trips
possible within `max_trip_min`; the share of trips possible within 30, 45 and 60 minutes
and within the limit; the share of trips whose origin or destination has no stop within
reach; the average straight-line trip length; and the number of changes on bus trips.

## 8. Ridership check

Each modelled trip is followed back along its path and every boarding it makes is
counted on that route. Both modelled and observed boardings are turned into shares of
their own total over the 56 BakuBus routes in both, and compared with Spearman's rank
correlation (1 means the same ranking) and the correlation of the logarithms of the shares.

| Model inputs | Correlation |
|---|---|
| One headway of 12 minutes for every route, trips to homes only | 0.41 |
| Headways by service type, trips to homes only | 0.56 |
| Plus destinations (OpenStreetMap, metro) | 0.58 |
| Plus headways estimated from boardings | 0.77 |

The last step uses the same boardings it is checked against, so 0.58 is the fair
measure of how well the model predicts (`python3 measure.py --set headway_from_ridership=false`).
In that run the model overrates express routes such as E1, 120E and 72, and underrates
several suburban routes such as 139, 141E, 189 and 163. `output/robustness/fit_ladder.csv`
holds the four steps (section 10).

## 9. Stop balancing

`scenarios.balance_stops` removes a stop only when, on every route direction that uses it,
it is not a terminal, a flagged hub or a protected stop; it lies less than `--min-gap`
metres along the path from its previous or next kept stop; and removing it leaves no gap
longer than `--max-gap` (700 m). Stops served by fewer routes are considered first, so busy
transfer stops survive. In the redesign, a stop that would leave anyone without a stop
within `max_access_walk_m` is protected and the pass runs again.

## 10. Robustness checks

`robustness.py` repeats the main results under other conditions and writes
`output/robustness/` ([outputs.md](outputs.md)).

- **Fit ladder.** The ridership check of section 8, four times, adding one input at a
  time: every route every 12 minutes with trips to homes only; headways by service type;
  plus destinations; plus headways from boardings (the default). Each step runs
  `evaluate_od` on the same 300 origins as `measure.py` and compares the modelled
  boardings with the observed ones. H1 keeps its published headway from step 2 on.
- **Coverage by radius.** The coverage of section 5 at 300, 400, 500, 800 and 1,000 m.
- **Other trip samples.** The redesign search runs exactly as in `redesign.py`, then
  today's network and the redesigned one are scored with `evaluate_od` on ten different
  samples of 300 origins (seeds 1 to 10, the seven-point population, the gravity model
  with destinations). Each row gives the average door-to-door minutes counting a trip
  that cannot be made within 2 hours as 120, as the search does, and the gain. Seed 7 is
  the independent check that `redesign.py` reports.
- **Other assumptions.** `redesign.py` runs again, in parallel processes, under eleven
  changed settings (transfer penalty 2 and 8 minutes; distance decay 4 and 9 km; homes
  only; 45 and 80 boardings per trip; 400 m walks; a search sample of 200 origins and
  one with another seed; nobody may lose a stop), plus the committed settings. Each row
  reports what the search kept, its independent check and its fleet-saving option, from
  that run's `summary.json` and `changes.csv`.

## 11. How far to trust the numbers

- **Measured from the data**: lengths, stop spacing, directness, duplication, corridors,
  near-duplicates, detours (except their minutes), coverage.
- **Estimated with assumptions**: running times, fuel, CO₂, headways, daily service,
  door-to-door times, transfers, modelled boardings. They are for comparing versions of
  the network, not forecasts.
- **Checks**: average speed calibrated to the reported 22 km/h; implied fleet 2,015 against
  2,300 reported; the population grid's 3.04 million against official 3.22 million; model
  ridership ranking 0.58 against observed; the redesign's gain on ten trip samples and
  under eleven other settings ([results.md](results.md#how-robust-the-results-are)).
