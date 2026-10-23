# Results

I generated these results on 23 October 2026 from the committed data with the default
settings in `busnet.toml`:

```sh
python3 measure.py --scenario stop-balancing --min-gap 250
python3 redesign.py
python3 robustness.py
```

Every number below is in `output/` ([outputs.md](outputs.md) explains each file). Two
kinds of number appear. Measured ones come straight from the network data (lengths,
directness, overlap, detours, stop spacing and coverage) and are facts about the
snapshot. Estimated ones depend on the assumptions in [configuration.md](configuration.md)
(times, fuel, daily service and modelled riders); I use them to compare versions of the
network, not as forecasts.

## In short

The routes are indirect: only 29 of the 201 run within 1.4 times the straight line
between their ends, and 74 are very indirect or loops. They overlap: every stop-to-stop
link carries 1.93 routes on average, on 21 stretches totalling 71 km eight or more
routes share every link, and 25 routes have at least 85% of their stops on one other
route. Detours are common and mostly unnecessary: 271 of them on 139 routes add 939 km
to one trip in each direction of every route, and for 217 of them nobody near the stops
inside the detour depends on that route alone. Stops are close together, with 23.9% of
the gaps under 300 m, so that stopping takes an estimated 19% of the buses' running
time and 20% of their fuel. And access is limited: 66% of the 3.04 million people
around the network live within 400 m of a stop, the average modelled trip takes 52
minutes door to door, and only 29% of trips can be made within 45 minutes.

The redesign helps, but only a little. With the same fleet it shortens the average trip
from 51.8 to 50.9 minutes; alternatively it gives today's travel times with about 12%
fewer buses, fuel and CO₂. The gain is small but it holds up: on ten samples of trips
the redesign saves 0.68 to 0.81 minutes a trip (mean 0.77), under eleven other
assumptions 0.58 to 0.84, and today's travel times then need 87 to 90% of the buses
([how robust the results are](#how-robust-the-results-are)). I treat the changes as
candidates to review, not a plan; [what to check first](#check-these-before-acting) is
listed below.

## Today's network

### Size

| Measure | Value |
|---|---|
| Routes with stops | 201 (402 route directions) |
| Stops served | 3,456 |
| Route length, all directions added up | 7,398 km |
| Median route, one way | 17.1 km, 27.5 stops |
| Distinct stop-to-stop links | 3,824 km |

### Directness

| Shape (from the less direct direction) | Routes |
|---|---|
| Direct: up to 1.4 times the straight line between its ends | 29 |
| Indirect: 1.4 to 2 times | 98 |
| Very indirect: 2 to 3 times | 55 |
| Loop: over 3 times, or ends less than 1 km apart | 19 |

- The median route is 1.77 times the straight line between its ends. Only 20 of 182
  non-loop routes meet the 1.3 limit of the Soviet planning norm.
- The median route is 21% longer than the shortest path buses could take between its
  ends on links that buses already drive.
- For riders, the median route covers 1.45 times the straight-line distance between any
  two of its stops at least 1 km apart.
- Indirect routes carry many riders. 6 of the 20 busiest BakuBus routes are very
  indirect or loops, including the busiest, route 14, with 31,303 boardings a weekday.
- The least direct routes are loops: 517 (9.3 times), 4 (7.8), 155 (6.2), 44 (4.6) and
  2 (4.1).

### Overlap

- The duplication ratio is 1.93: buses run 7,398 km of route over 3,824 km of distinct
  links, and up to 26 routes use one link.
- There are 21 trunk corridors, 71 km in total, where 8 or more routes share every
  link. The three longest, and the one used by the most routes:

| Corridor | Length | Routes per link (mean / most) | Routes using it |
|---|---|---|---|
| X.R.Ulutürk küç. 5 saylı ASAN Xidmət – Dövlət Gömrük Komitəsinin Akademiyası | 12.0 km | 15.8 / 21 | 27 |
| Maştağa Olimpiya İdman Kompleksi – Atletlər kəndi | 11.5 km | 15.2 / 21 | 22 |
| Bakı Poladtökmə ASC – Bakı Poladtökmə, out and back via Azadlıq m/st | 9.2 km | 10.4 / 14 | 15 |
| Xәtai Rayon Mәhkәmәsi – Neftçilər m/st | 3.5 km | 15.1 / 25 | 29 |

  `output/corridors.csv` has all 21 and their routes. Stop names here are spelled as in
  the data, which sometimes mixes Cyrillic letters into Azerbaijani names.

- 25 routes are near-duplicates, in 72 pairs; in 59 of the pairs the two routes belong
  to different carriers. Examples:

| Route | Inside | Share of its stops | Same carrier |
|---|---|---|---|
| 190 | 160 | 100% | yes |
| 120A | 149, and 205 | 96% | no |
| 118B | 118A | 96% | no |
| 139 | 107, and 189 | 96% | no / yes |
| 173A and 173B | each other | 94% | yes |
| 197 and 198 | each other | 94% | no |

### Detours

A detour is a stretch where the bus travels at least 2.5 times the straight line between
two of its stops, and at least 1.5 km further ([methodology.md](methodology.md#2-geometry-measures)).

- There are 271 detours on 139 routes. Together they add 939 km to one trip in each
  direction of every route.
- For 217 of the detours (719 km, on 118 routes), everyone who lives near the stops
  inside the detour also has another route within 400 m.

The longest:

| Route, direction | From – to | Along the route | Straight line | Extra per trip | People only this route serves |
|---|---|---|---|---|---|
| 177, 2 | Maştağa parkı – 59 saylı poçt şöbəsi | 21.2 km | 7.8 km | 13.4 km, 27.5 min | 53 |
| 164, 2 | 294 nömrəli tam orta məktəb – 253 nömrəli tam orta məktəb | 19.7 km | 7.7 km | 12.0 km, 25.5 min | 36 |
| 112, 2 | Şüvәlan yolu – Dendrologiya İnstitutu | 15.4 km | 3.7 km | 11.7 km, 25.3 min | 1,661 |
| 169, 1 | Bakı Ekspo Mərkəzi – Binə Atçılıq qəsəbəsi | 15.8 km | 5.6 km | 10.2 km, 23.4 min | 0 |
| 169, 2 | Binə Atçılıq qəsəbəsi – Heydər Əliyev pr. 441 | 16.5 km | 6.6 km | 9.9 km, 22.8 min | 0 |
| E1, 1 | Səbail Rayonu Dövlət Yol Polisi İdarəsi – Abşeron ticarət mərkəzi | 15.8 km | 5.9 km | 9.9 km, 21.8 min | 0 |

The routes with the most detour length are 205 (5 detours, 26.0 km), 169 (3, 22.9 km),
112 (2, 19.4 km), 70 (3, 18.3 km), E1 (2, 17.9 km) and 33 (5, 17.7 km).

### Stop spacing

- Consecutive stops are a median 420 m apart. 5.4% of gaps are under 200 m and 23.9%
  under 300 m.
- With 20 seconds and 0.05 litres lost per stop, stopping takes 18.8% of running time and
  20.4% of fuel.
- The routes with the most gaps under 300 m: 81 (46 gaps), 592 (43), 103 (41), 567 (40)
  and 55 (39).

### Who the network reaches

| People within ... of a served stop | Share of 3.04 million |
|---|---|
| 300 m | 55.5% |
| 400 m (the coverage setting) | 66.0% |
| 500 m | 73.4% |
| 800 m | 87.2% |
| 1,000 m | 91.5% |

`network.json` reports the 400 m value; `output/robustness/coverage_radius.csv` has all
five (the same as runs with `--set coverage_radius_m=300` and so on). The 12.8% beyond
800 m is close to the 17% with limited bus access that AYNA's consultant reported in 2025.

Door-to-door, on 300 origins sampled by population:

| Measure | Value |
|---|---|
| Average door-to-door time of trips possible within 2 hours | 51.8 min |
| Trips possible within 30 / 45 / 60 minutes | 16.2% / 29.4% / 42.2% |
| Trips possible within 2 hours | 66.3% |
| Trips with no stop within 500 m at one end or both | 34.6% |
| Average trip length, straight line | 8.0 km |
| Possible trips by changes: walk only / none / one / two / three or more | 11.4% / 28.9% / 43.2% / 15.0% / 1.5% |

### Daily service, fuel and CO₂ (estimated)

| Measure | Value |
|---|---|
| Headways | 1 from published data (H1), 55 from boardings, 145 by service type |
| Trips a day | 33,363 |
| Bus-hours a day | 28,327 |
| Bus-km a day | 588,994 |
| Buses needed | 2,015, 88% of the 2,300 reported in service |
| Fuel a day | 226,592 litres, diesel-equivalent |
| CO₂ a day | 605 tonnes |

The implied fleet lands near the reported one, which suggests the estimated headways are
realistic overall. Individual routes can still be far off.

### Ridership, and how well the model matches it

- BakuBus routes carried 768,253 boardings on an average weekday in September 2026, on
  64 routes; 56 of those routes are in the snapshot, with 692,288.
- Route 14 is the busiest, with 31,303 boardings a weekday and the most per km of route
  (2,285).
- Route 150E recorded only 16.5 boardings a weekday, so it probably barely ran in
  September; apart from it, route 595 carries the fewest per km of route (90).
- The model's boardings per route rank the 56 routes with a Spearman correlation of
  (`output/robustness/fit_ladder.csv`):

| Model inputs | Correlation |
|---|---|
| One headway of 12 minutes for every route, trips to homes only | 0.41 |
| Headways by service type, trips to homes only | 0.56 |
| Plus destinations (OpenStreetMap, metro) | 0.58 |
| Plus headways estimated from observed boardings (the default) | 0.77 |

`network.json` shows 0.77 because the default settings estimate headways from the same
boardings the check compares against, which makes the check partly circular. The fair
figure, and the one I quote, is 0.58, from
`python3 measure.py --set headway_from_ridership=false`; that run also implies a fleet of
1,848 buses.

In the fair run, the model overrates express and long suburban routes: E1 (6.4 times
its observed share), 205 (3.4), 120E (2.6), 72 (2.2). It underrates others: the
suburban routes 139, 141E, 189 and 163, and the express 140E, get under 15% of their
observed share. `output/ridership_check.csv` has the comparison route by route for the
default run.

## Stop balancing alone

`--scenario stop-balancing --min-gap 250` removes stops closer than 250 m to a neighbour
on every route that uses them. It keeps terminals and hubs, and never leaves a gap over
700 m (`output/scenario.json`).

| Measure | Today | After | Change |
|---|---|---|---|
| Stops served | 3,456 | 3,105 | 351 removed (883 stop visits) |
| Median stop gap | 420 m | 473 m | |
| Gaps under 300 m | 23.9% | 14.2% | |
| People within 400 m of a stop | 65.96% | 65.82% | −0.15 points |
| Buses needed at today's headways | 2,015 | 1,987 | −28 |
| Bus-hours a day | 28,327 | 27,895 | −1.5% |
| Fuel a day | 226,592 L | 222,707 L | −1.7% |
| CO₂ a day | 605 t | 595 t | |
| Average door-to-door time | 51.8 min | 51.6 min | |
| Trips possible within 2 hours | 66.3% | 66.0% | |

## The redesign

`python3 redesign.py` with the default settings ([redesign.md](redesign.md) explains the
method). It kept 27 changes:

- 5 merges: 114B, 100, 173A, 210 and 169;
- 3 drops: 164, 39 and 150E;
- 14 straightened detours on 12 routes;
- one stop-balancing pass removing 338 stops;
- 4 frequency shifts moving 25, 19, 19 and 14 bus-equivalents.

Routes go from 201 to 193. Route 180 is protected and left as it is. No route with
1,000 or more counted boardings a weekday was dropped.

### Riders per route

Drops and frequency shifts rank routes by boardings a day: counted for the 56 BakuBus
routes in the opendata.az data (692,288 a weekday) and estimated for the other 145
routes (733,436 a weekday, the model's boardings scaled so that on the counted routes
the model and the counts agree in total). Together that is 1.43 million boardings a
weekday, close to the 1.6 million daily bus trips AYNA reported in 2023; a trip with a
change counts as two boardings. `output/redesign/routes.csv` gives each route's figure
and its source.

### The 27 changes

Gains are average door-to-door minutes on the search sample (100 origins). A trip that is
impossible within 2 hours counts as 120 minutes. "People" counts people left with no stop
within 500 m. The full wording is in `output/redesign/changes.csv`.

| Step | Change | Gain (min) | People |
|---|---|---|---|
| 1 | Merge 114B into 114A (92% of its stops on 114A) | 0.061 | 0 |
| 2 | Drop 164: 14 boardings a day per bus (estimated) | 0.049 | 171 |
| 3 | Merge 100 into 108B (93%) | 0.038 | 0 |
| 4 | Straighten 161 direction 2 near Hövsan: 1.8 km shorter, 8 stops skipped | 0.031 | 0 |
| 5 | Straighten 132 direction 2, the same stretch: 1.8 km shorter, 8 stops skipped | 0.015 | 0 |
| 6 | Merge 173A into 173B (94%) | 0.021 | 20 |
| 7 | Straighten 509 direction 1 (Xocasən şosesi): 6.6 km shorter, 8 stops skipped | 0.022 | 0 |
| 8 | Straighten 166 direction 1: 3.9 km shorter, 4 stops skipped | 0.017 | 0 |
| 9 | Straighten 32 direction 1: 2.2 km shorter, 5 stops skipped | 0.017 | 0 |
| 10 | Merge 210 into 215 (93%) | 0.016 | 495 |
| 11 | Straighten 509 direction 2: 6.1 km shorter, 7 stops skipped | 0.019 | 0 |
| 12 | Straighten 525 direction 1: 6.6 km shorter, 9 stops skipped | 0.016 | 0 |
| 13 | Straighten 157 direction 2: 3.0 km shorter, 6 stops skipped | 0.011 | 0 |
| 14 | Straighten 40 direction 1: 1.8 km shorter, 8 stops skipped | 0.011 | 0 |
| 15 | Straighten 17 direction 2: 3.1 km shorter, 10 stops skipped | 0.011 | 0 |
| 16 | Straighten 3 direction 1: 2.1 km shorter, 4 stops skipped | 0.010 | 0 |
| 17 | Drop 39: 84 boardings a day per bus (estimated) | 0.011 | 0 |
| 18 | Merge 169 into 168 (91%) | 0.009 | 0 |
| 19 | Straighten 537 direction 1: 3.4 km shorter, no stops skipped | 0.008 | 0 |
| 20 | Straighten 525 direction 2: 2.3 km shorter, 9 stops skipped | 0.008 | 0 |
| 21 | Drop 150E: 3 boardings a day per bus (counted) | 0.005 | 290 |
| 22 | Straighten 125 direction 2: 1.8 km shorter, 9 stops skipped | 0.005 | 0 |
| 23 | Stop balancing at 250 m: 338 stops removed, none that is someone's only stop | 0.217 | 0 |
| 24 | Move 25 buses from the 20 routes where a bus saves riders the least waiting to the 20 where it saves the most | 0.332 | 0 |
| 25 | The same, 19 buses | 0.175 | 0 |
| 26 | The same, 19 buses | 0.127 | 0 |
| 27 | The same, 14 buses | 0.088 | 0 |

The gain of 1.35 minutes on the search sample divides as follows (shares rounded):

| Kind of change | Gain | Share of the gain |
|---|---|---|
| Moving buses to where they save the most waiting | 0.72 min | 54% |
| Stop balancing | 0.22 min | 16% |
| Straightening | 0.20 min | 15% |
| Merges | 0.14 min | 11% |
| Drops | 0.07 min | 5% |

The bus moves depend most on riders per route. Riders are counted for only 56 routes and
estimated for the rest by a model that ranks routes only roughly right (0.58). The bus
moves are therefore the least certain part of the result.

### Before and after

Measured on the independent check: 300 other origins, with seven population points per
hexagon (`output/redesign/summary.json`).

| Measure | Today | Redesign | Change |
|---|---|---|---|
| Routes | 201 | 193 | −8 |
| Stops served | 3,456 | 3,105 | −351 |
| Route length, all directions | 7,398 km | 6,970 km | −5.8% |
| Distinct links | 3,824 km | 3,678 km | −3.8% |
| Duplication ratio | 1.93 | 1.90 | |
| Median stop gap | 420 m | 470 m | |
| Gaps under 300 m | 23.9% | 14.6% | |
| People within 400 m of a stop | 65.96% | 65.80% | about 5,000 fewer people; 976 have no stop within 500 m any more |
| Average door-to-door time, possible trips | 51.82 min | 50.86 min | −0.97 min |
| Trips possible within 30 / 45 / 60 minutes | 16.2 / 29.4 / 42.2% | 16.6 / 30.3 / 43.4% | |
| Trips possible within 2 hours | 66.3% | 66.4% | |
| Average counting impossible trips as 120 min | 74.82 min | 74.06 min | −0.76 min |
| Possible trips with two or more changes | 16.5% | 17.4% | more changes |
| Trips a day | 33,363 | 34,418 | +3.2% |
| Bus-hours a day | 28,327 | 28,327 | same fleet |
| Bus-km a day | 588,994 | 596,868 | +1.3% |
| Buses, rounded up per route | 2,015 | 2,017 | |
| Fuel a day | 226,592 L | 226,708 L | +0.05% |
| CO₂ a day | 605.0 t | 605.3 t | |

The same buses run more trips on shorter routes, so frequencies rise and waits shorten.
Bus-km rise a little. Fuel stays about the same, because buses also stop less.

On the search sample itself, the capped average fell more, from 79.66 to 78.31 minutes,
because the search was tuned to those trips. I quote the independent check.

### Or: today's travel times with fewer buses

The improvement can be taken as a smaller fleet instead. With 88.3% of the redesigned
network's buses, cut evenly on every route, the independent check's average trip
(counting impossible trips as 120 minutes) is no longer than today's. The share is found
by halving an interval six times, so it is accurate to about one percentage point.

| Measure | Today | Redesign with 88% of the buses | Change |
|---|---|---|---|
| Bus-equivalents | 1,916 | 1,692 | −11.7% |
| Buses, rounded up per route | 2,015 | 1,796 | −219 |
| Bus-hours a day | 28,327 | 25,007 | −11.7% |
| Bus-km a day | 588,994 | 526,923 | −10.5% |
| Fuel a day | 226,592 L | 200,140 L | −11.7% |
| CO₂ a day | 605 t | 534 t | −11.7% |

On the search sample the same calculation gives 79%, which overstates the saving for the
same reason as above.

### What changed from the first version

My first run of the search (commit `fe1a6f1`) ranked routes by modelled riders only. It
dropped routes 595, 149 and 140E, which carry about 10,100 counted boardings a weekday,
and cut route 180 to Pirallahı from every 20 to every 30 minutes, which told me that the
model could not be allowed to overrule a count. The current version uses counts where
they exist, never drops a route with 1,000 or more counted boardings, moves buses by the
waiting time they save, and leaves 180 alone; 595 and 140E now gain buses instead. The
overall effect is about the same: the average trip goes from 51.82 to 50.86 minutes,
against 50.88 in the first version, and 88% of the buses give today's travel times in
both.

### Check these before acting

1. Route 519 ends up running every 3 minutes. It is a 2.1 km route with 3 stops and no
   counts; the model estimates 14,700 boardings a day for it, so the search raises it
   from every 15 minutes to the shortest headway allowed. I would count its riders
   before adding a single bus.
2. Some people lose their stop. Merging 210 into 215 leaves 495 people without a stop
   within 500 m, just under the limit of 500 per change; dropping 150E strands 290,
   dropping 164 strands 171, and merging 173A strands 20, which is 976 people in total.
   Run with `redesign_max_people_losing_stop=0` and
   `redesign_max_people_losing_stop_total=0`, the search keeps 24 changes, strands
   nobody, and gains as much: 0.77 against 0.76 minutes on the independent check
   (`output/robustness/redesign_settings.csv`). The stricter rule costs nothing here,
   and I would use it.
3. The dropped routes have little evidence behind them. 164 and 39 have no counts; their
   estimated boardings are 133 and 582 a day. 150E recorded only 16.5 boardings a
   weekday in September. All three should be checked with their operators.
4. Some routes lose buses on estimates alone: 131, 197, 198, 550, 551 and 554 go from
   every 15 to every 30 minutes, and 54 and 50 from every 10 to about every 24. None of
   them has counts.
5. More riders must change buses: the share of trips with two or more changes rises
   from 16.5% to 17.4%.
6. Every straightened stretch needs looking at on the map
   (`output/redesign/network.geojson`). Each new path follows links that buses drive
   today, but turns, one-way streets and the skipped stops (schools, clinics) still need
   checking on the ground.

### What the results do not say

They are not forecasts. They rest on estimated headways, a gravity model of demand that
ranks routes only moderately well, and no vehicle capacity or crowding. What they show
is where the network wastes time and which changes look promising; they cannot replace
counts, GPS data or local knowledge, and [roadmap.md](roadmap.md) says what I would
want before trusting them further. The next section shows which of them survive other
trip samples and other assumptions.

## How robust the results are

I wrote `robustness.py` to repeat the main results under other conditions
([methodology.md](methodology.md#10-robustness-checks)); it writes `output/robustness/`
([outputs.md](outputs.md)). Minutes below are the capped average the search uses:
door-to-door minutes, with a trip that cannot be made within 2 hours counted as 120.

### On other samples of trips

The redesign above was checked on one sample of 300 origins (seed 7). Scored on ten
samples, with the search itself unchanged (`redesign_seeds.csv`):

| Trip sample | Today | Redesign | Gain | Possible trips only, today → redesign |
|---|---|---|---|---|
| 1 | 77.06 | 76.34 | 0.73 | 52.1 → 51.2 min |
| 2 | 77.49 | 76.71 | 0.78 | 52.4 → 51.5 min |
| 3 | 74.67 | 73.86 | 0.80 | 52.4 → 51.6 min |
| 4 | 75.11 | 74.33 | 0.78 | 51.2 → 50.3 min |
| 5 | 73.57 | 72.76 | 0.81 | 52.3 → 51.5 min |
| 6 | 75.50 | 74.74 | 0.76 | 50.8 → 50.0 min |
| 7 (the independent check above) | 74.82 | 74.06 | 0.76 | 51.8 → 50.9 min |
| 8 | 75.70 | 75.02 | 0.68 | 51.3 → 50.5 min |
| 9 | 74.15 | 73.34 | 0.80 | 50.9 → 49.9 min |
| 10 | 74.33 | 73.52 | 0.81 | 52.6 → 51.8 min |
| All ten | | | mean 0.77, standard deviation 0.04, from 0.68 to 0.81 | |

The gain is positive in every sample. The level moves by about 4 minutes between
samples (73.6 to 77.5 for today's network), because each sample draws different
origins; the difference between the two networks on the same sample moves by 0.13
minutes, about a thirtieth of that. So I quote the gain with its range, not the level
to two decimals.

### Under other assumptions

The search run again with one setting changed, each run checked on the usual
independent sample (`redesign_settings.csv`). Every run also kept one stop-balancing
pass.

| Setting | Changes kept | Routes left | People losing their stop | Today → redesign | Gain | Fleet for today's times | Fuel saved |
|---|---|---|---|---|---|---|---|
| The settings in busnet.toml | 27 (5 merges, 3 drops, 14 straightened, 4 shifts) | 193 | 976 | 74.82 → 74.06 | 0.76 | 88% | 11.7% |
| Riders mind a change less: 2 minutes instead of 5 | 26 (5 merges, 3 drops, 13 straightened, 4 shifts) | 193 | 976 | 73.18 → 72.37 | 0.80 | 88% | 11.7% |
| Riders mind a change more: 8 minutes instead of 5 | 26 (5 merges, 2 drops, 14 straightened, 4 shifts) | 194 | 828 | 76.32 → 75.60 | 0.72 | 88% | 11.6% |
| Shorter trips: distance decay 4 km instead of 6 | 27 (5 merges, 4 drops, 13 straightened, 4 shifts) | 192 | 1,391 | 67.53 → 66.95 | 0.59 | 90% | 10.1% |
| Longer trips: distance decay 9 km instead of 6 | 26 (5 merges, 2 drops, 14 straightened, 4 shifts) | 194 | 828 | 80.53 → 79.69 | 0.83 | 88% | 12.4% |
| Trips end at homes only, with no destinations | 25 (5 merges, 2 drops, 13 straightened, 4 shifts) | 194 | 687 | 77.90 → 77.07 | 0.82 | 87% | 13.2% |
| Counted routes run more often: 45 boardings per trip instead of 60 | 25 (5 merges, 2 drops, 13 straightened, 4 shifts) | 194 | 687 | 74.26 → 73.53 | 0.73 | 88% | 12.4% |
| Counted routes run less often: 80 boardings per trip instead of 60 | 26 (5 merges, 2 drops, 14 straightened, 4 shifts) | 194 | 828 | 75.45 → 74.64 | 0.81 | 88% | 11.6% |
| People walk at most 400 m to a stop instead of 500 | 24 (5 merges, 2 drops, 12 straightened, 4 shifts) | 194 | 405 | 79.49 → 78.91 | 0.58 | 90% | 10.2% |
| A search sample twice as large: 200 origins instead of 100 | 32 (7 merges, 3 drops, 17 straightened, 4 shifts) | 191 | 1,133 | 74.82 → 73.99 | 0.84 | 87% | 13.1% |
| Another search sample of the same size: seed 23 instead of 11 | 33 (8 merges, 4 drops, 16 straightened, 4 shifts) | 189 | 1,986 | 74.82 → 74.03 | 0.79 | 88% | 12.5% |
| No change may leave anyone without a stop within reach | 24 (3 merges, 2 drops, 14 straightened, 4 shifts) | 196 | 0 | 74.82 → 74.05 | 0.77 | 88% | 11.6% |

The gain stays between 0.58 and 0.84 minutes, and today's travel times need 87 to 90%
of the buses in every run (10 to 13% less fuel), so the direction of the result does not
depend on any one assumption. The smallest gains come with shorter trips (decay 4 km)
and shorter walks (400 m), the largest with a search sample twice as large.

What the search keeps is also stable: two to four drops, 12 to 17 straightened detours,
one stop-balancing pass and four bus shifts in every run, and five merges in nine of
the twelve (three under the strict coverage guard, seven and eight with the larger and
the other search sample). A larger search sample (200 origins) or a different one (seed
23) keeps 32 or 33 changes instead of 27, with the same gain on the independent sample,
which tells me the search sample decides the changes at the margin, not the effect.
Those two runs also strand more people (1,133 and 1,986), still within the 3,000
allowed.

The result I find most useful is the strict coverage guard: with nobody allowed to lose
a stop, the search keeps 24 changes and gains 0.77 minutes, as much as the default run.
The 976 people the default run leaves without a stop buy nothing; see
[Check these before acting](#check-these-before-acting).

### The demand model as each input is added

| Model inputs | Spearman | Correlation of log shares | Fleet implied |
|---|---|---|---|
| One headway of 12 minutes for every route; trips to homes only | 0.41 | 0.41 | 2,030 |
| Headways by service type; trips to homes only | 0.56 | 0.51 | 1,848 |
| Plus destinations (OpenStreetMap, metro) | 0.58 | 0.49 | 1,848 |
| Plus headways estimated from observed boardings (the default) | 0.77 | 0.61 | 2,015 |

Each input improves the ranking of the 56 counted routes. Headways by service type add
most (0.41 to 0.56), destinations a little more (0.58); the last step uses the counts
themselves and is not a fair test. 0.58 is the figure I quote for the model
(`fit_ladder.csv`).

### Coverage by walking distance

The table in [Who the network reaches](#who-the-network-reaches) comes from
`coverage_radius.csv`: 55.5% of people within 300 m of a served stop, 66.0% within
400 m, 73.4% within 500 m, 87.2% within 800 m and 91.5% within 1,000 m.
