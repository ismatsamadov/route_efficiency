# Results

These results come from the committed data with the default settings in `busnet.toml`.
They were generated on 23 October 2026 by:

```sh
python3 measure.py --scenario stop-balancing --min-gap 250
python3 redesign.py
```

Every number below is in `output/` ([outputs.md](outputs.md) explains each file). There
are two kinds of number:

- **Measured** numbers come straight from the network data: lengths, directness,
  overlap, detours, stop spacing and coverage.
- **Estimated** numbers depend on the assumptions in [configuration.md](configuration.md):
  times, fuel, daily service and modelled riders. Use them to compare versions of the
  network, not as forecasts.

## In short

- **Routes are indirect.** Only 29 of 201 routes run within 1.4 times the straight line
  between their ends. 74 are very indirect or loops.
- **Routes overlap.** Every stop-to-stop link carries 1.93 routes on average. On 21
  stretches (71 km), 8 or more routes share every link. 25 routes have at least 85% of
  their stops on one other route.
- **Detours are common and mostly unnecessary.** There are 271 detours on 139 routes,
  adding 939 km to one trip in each direction of every route. For 217 of them, nobody
  near the stops inside the detour depends on that route alone.
- **Stops are close together.** 23.9% of gaps between stops are under 300 m. Stopping
  takes an estimated 19% of buses' running time and 20% of their fuel.
- **Access is limited.** 66% of the 3.04 million people around the network live within
  400 m of a stop. An average modelled trip takes 52 minutes door to door, and only 29%
  of trips can be made within 45 minutes.
- **The first redesign helps a little.** With the same fleet, it shortens the average
  trip from 51.8 to 50.9 minutes. Alternatively, it gives today's travel times with about
  12% fewer buses, fuel and CO₂. Its changes are candidates to review, not a plan. Three
  of the routes it drops carry riders the model does not see ([below](#check-these-before-acting)).

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

- **Duplication ratio 1.93.** Buses run 7,398 km of route over 3,824 km of distinct
  links. Up to 26 routes use one link.
- **21 trunk corridors**, 71 km in total, where 8 or more routes share every link. The
  three longest, and the one used by the most routes:

| Corridor | Length | Routes per link (mean / most) | Routes using it |
|---|---|---|---|
| X.R.Ulutürk küç. 5 saylı ASAN Xidmət – Dövlət Gömrük Komitəsinin Akademiyası | 12.0 km | 15.8 / 21 | 27 |
| Maştağa Olimpiya İdman Kompleksi – Atletlər kəndi | 11.5 km | 15.2 / 21 | 22 |
| Bakı Poladtökmə ASC – Bakı Poladtökmə, out and back via Azadlıq m/st | 9.2 km | 10.4 / 14 | 15 |
| Xәtai Rayon Mәhkәmәsi – Neftçilər m/st | 3.5 km | 15.1 / 25 | 29 |

  `output/corridors.csv` has all 21 and their routes. Stop names here are spelled as in
  the data, which sometimes mixes Cyrillic letters into Azerbaijani names.

- **25 near-duplicate routes**, in 72 pairs. In 59 of the pairs the two routes belong to
  different carriers. Examples:

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

`network.json` reports the 400 m value. The others come from runs with
`--set coverage_radius_m=300` (and so on). The 12.8% beyond 800 m is close to the 17%
with limited bus access that AYNA's consultant reported in 2025.

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

- **Observed.** BakuBus routes carried 768,253 boardings on an average weekday in
  September 2026, on 64 routes. 56 of those routes are in the snapshot, with 692,288.
- **Busiest.** Route 14 carries 31,303 boardings a weekday and the most per km of route
  (2,285).
- **Least used.** Route 150E recorded only 16.5 boardings a weekday, so it probably
  barely ran in September. Apart from it, route 595 carries the fewest per km of route
  (90).
- **How well the model ranks routes.** The model's boardings per route rank the 56 routes
  with a Spearman correlation of:

| Model inputs | Correlation |
|---|---|
| Headways by service type, trips to homes only | 0.56 |
| Plus destinations (OpenStreetMap, metro) | 0.58 |
| Plus headways estimated from observed boardings (the default) | 0.77 |

`network.json` shows 0.77 because the default settings estimate headways from the same
boardings the check compares against. That makes the check partly circular. The fair
figure is 0.58, from `python3 measure.py --set headway_from_ridership=false`. That run
also implies a fleet of 1,848 buses.

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

## The first redesign

`python3 redesign.py` with the default settings ([redesign.md](redesign.md) explains the
method). It kept 28 changes:

- 5 merges: 114B, 100, 173A, 210 and 169;
- 4 drops: 164, 595, 149 and 140E;
- 14 straightened detours on 12 routes;
- one stop-balancing pass removing 340 stops;
- 4 frequency shifts moving 24, 17, 11 and 5 bus-equivalents.

Routes go from 201 to 192.

### The 28 changes

Gains are average door-to-door minutes on the search sample (100 origins), counting a
trip that is impossible within 2 hours as 120 minutes. "People" counts people left with
no stop within 500 m. Full wording is in `output/redesign/changes.csv`.

| Step | Change | Gain (min) | People |
|---|---|---|---|
| 1 | Merge 114B into 114A (92% of its stops on 114A) | 0.061 | 0 |
| 2 | Drop 164 (few modelled riders per bus) | 0.049 | 171 |
| 3 | Merge 100 into 108B (93%) | 0.038 | 0 |
| 4 | Straighten 161 direction 2 near Hövsan: 1.8 km shorter, 8 stops skipped | 0.031 | 0 |
| 5 | Straighten 132 direction 2, the same stretch: 1.8 km shorter, 8 stops skipped | 0.015 | 0 |
| 6 | Merge 173A into 173B (94%) | 0.021 | 20 |
| 7 | Straighten 509 direction 1 (Xocasən şosesi): 6.6 km shorter, 8 stops skipped | 0.022 | 0 |
| 8 | Drop 595 | 0.014 | 0 |
| 9 | Straighten 166 direction 1: 3.9 km shorter, 4 stops skipped | 0.017 | 0 |
| 10 | Straighten 32 direction 1: 2.2 km shorter, 5 stops skipped | 0.017 | 0 |
| 11 | Merge 210 into 215 (93%) | 0.016 | 495 |
| 12 | Straighten 509 direction 2: 6.1 km shorter, 7 stops skipped | 0.019 | 0 |
| 13 | Straighten 525 direction 1: 6.6 km shorter, 9 stops skipped | 0.016 | 0 |
| 14 | Straighten 157 direction 2: 3.0 km shorter, 6 stops skipped | 0.011 | 0 |
| 15 | Straighten 40 direction 1: 1.8 km shorter, 8 stops skipped | 0.011 | 0 |
| 16 | Drop 149 | 0.010 | 0 |
| 17 | Straighten 17 direction 2: 3.1 km shorter, 10 stops skipped | 0.011 | 0 |
| 18 | Straighten 3 direction 1: 2.1 km shorter, 4 stops skipped | 0.010 | 0 |
| 19 | Merge 169 into 168 (91%) | 0.009 | 0 |
| 20 | Straighten 537 direction 1: 3.4 km shorter, no stops skipped | 0.008 | 0 |
| 21 | Straighten 525 direction 2: 2.3 km shorter, 9 stops skipped | 0.008 | 0 |
| 22 | Drop 140E | 0.006 | 0 |
| 23 | Straighten 125 direction 2: 1.8 km shorter, 9 stops skipped | 0.005 | 0 |
| 24 | Stop balancing at 250 m: 340 stops removed, none that is someone's only stop | 0.217 | 0 |
| 25 | Move 24 buses from the 20 routes with the fewest modelled riders per bus to the 20 with the most | 0.350 | 0 |
| 26 | The same, 17 buses | 0.173 | 0 |
| 27 | The same, 11 buses | 0.085 | 0 |
| 28 | The same, 5 buses | 0.037 | 0 |

The gain of 1.28 minutes on the search sample divides as follows:

| Kind of change | Gain | Share of the gain |
|---|---|---|
| Moving buses to busier routes | 0.64 min | half |
| Stop balancing | 0.22 min | 17% |
| Straightening | 0.20 min | 16% |
| Merges | 0.14 min | 11% |
| Drops | 0.08 min | 6% |

The bus moves depend most on the model's riders per route, which it gets only roughly
right (0.58). They are therefore the least certain part of the result.

### Before and after

Measured on the independent check: 300 other origins, with seven population points per
hexagon (`output/redesign/summary.json`).

| Measure | Today | Redesign | Change |
|---|---|---|---|
| Routes | 201 | 192 | −9 |
| Stops served | 3,456 | 3,103 | −353 |
| Route length, all directions | 7,398 km | 6,906 km | −6.6% |
| Distinct links | 3,824 km | 3,651 km | −4.5% |
| Duplication ratio | 1.93 | 1.89 | |
| Median stop gap | 420 m | 469 m | |
| Gaps under 300 m | 23.9% | 14.7% | |
| People within 400 m of a stop | 65.96% | 65.80% | about 4,900 fewer people; 687 have no stop within 500 m any more |
| Average door-to-door time, possible trips | 51.8 min | 50.9 min | −0.9 min |
| Trips possible within 30 / 45 / 60 minutes | 16.2 / 29.4 / 42.2% | 16.5 / 30.3 / 43.3% | |
| Trips possible within 2 hours | 66.3% | 66.4% | |
| Average counting impossible trips as 120 min | 74.8 min | 74.1 min | −0.7 min |
| Possible trips with two or more changes | 16.5% | 17.4% | more changes |
| Trips a day | 33,363 | 34,565 | +3.6% |
| Bus-hours a day | 28,327 | 28,327 | same fleet |
| Bus-km a day | 588,994 | 595,077 | +1.0% |
| Buses, rounded up per route | 2,015 | 2,010 | |
| Fuel a day | 226,592 L | 226,310 L | −0.1% |
| CO₂ a day | 605.0 t | 604.2 t | |

The same buses run more trips on shorter routes, so frequencies rise and waits shorten.
Bus-km rise a little, but fuel falls slightly because buses stop less.

On the search sample itself, the capped average fell more, from 79.7 to 78.4 minutes,
because the search was tuned to those trips. Quote the independent check.

### Or: today's travel times with fewer buses

The improvement can be taken as a smaller fleet instead. With 88.3% of the redesigned
network's buses, cut evenly on every route, the independent check's average trip
(counting impossible trips as 120 minutes) is no longer than today's. The share is
found by halving an interval six times, so it is accurate to about one percentage point.

| Measure | Today | Redesign with 88% of the buses | Change |
|---|---|---|---|
| Bus-equivalents | 1,916 | 1,692 | −11.7% |
| Buses, rounded up per route | 2,015 | 1,794 | −221 |
| Bus-hours a day | 28,327 | 25,007 | −11.7% |
| Bus-km a day | 588,994 | 525,341 | −10.8% |
| Fuel a day | 226,592 L | 199,789 L | −11.8% |
| CO₂ a day | 605 t | 533 t | −11.8% |

On the search sample the same calculation gives 80%, which overstates the saving for
the same reason as above.

### Check these before acting

1. **Three dropped routes carry real riders the model misses.** 595 carries 2,399
   boardings a weekday, 149 carries 4,605 and 140E carries 3,133: about 10,100 in all.
   They are BakuBus routes. The model gives them 2%, 3% and 0% of their observed share
   of riders, so it judged them nearly empty. Do not drop them on this evidence. The
   next version of the search should use observed boardings where they exist (see
   [roadmap.md](roadmap.md)).
2. **Some people lose their stop.** Merging 210 into 215 leaves 495 people without a
   stop within 500 m, just under the limit of 500 per change. Dropping 164 strands 171
   and merging 173A strands 20, for 687 in total.
3. **Route 180 (Pirallahı) runs less often.** It goes from every 20 to every 30 minutes,
   because the model sees few riders on it. Its connecting routes are missing from the
   data ([data.md](data.md#known-issues-not-repaired)).
4. **Riders per bus favours very short routes.** Route 519, 2.1 km and 3 stops, gains
   buses in every shift and goes from every 15 to every 3.7 minutes. Routes 197, 198, 550
   and 554 drop to every 30 minutes.
5. **More riders must change buses.** The share of trips with two or more changes rises
   from 16.5% to 17.4%.
6. **Look at every straightened stretch on the map.** Open
   `output/redesign/network.geojson`. The new path follows links that buses drive
   today, but turns, one-way streets and the skipped stops (schools, clinics) need
   checking on the ground.

### What the results do not say

They are not forecasts. They rest on estimated headways, a gravity model of demand that
ranks routes only moderately well, and no vehicle capacity or crowding. They show where
the network wastes time and which changes look promising. They cannot replace counts,
GPS data or local knowledge. [roadmap.md](roadmap.md) lists what would make them firmer.
