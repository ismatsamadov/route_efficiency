# The redesign search

`python3 redesign.py` looks for a better bus network with today's fleet. The code is in
`busnet/optimize.py`; the command and its outputs are in `redesign.py`. Settings are in
the `[redesign]` table of `busnet.toml`.

## The idea

Most cities that redesigned their bus networks fixed the operating budget and redrew the
routes to serve riders better within it (see [research.md](research.md)), and I do the
same on a computer. I start from today's routes, each with the buses its estimated
headway implies, and try the changes other redesigns used: merging routes that repeat
each other, dropping routes that carry few riders per bus, straightening detours,
removing closely spaced stops, and moving buses from quiet routes to busy ones. Each
change is scored with the door-to-door travel model and kept only if riders' average
trip gets shorter and nobody beyond a small allowance loses their last stop within
walking distance. Then I check the final network on a different sample of trips than
the search used. The fleet never changes: a route that gets shorter keeps its buses and
therefore runs more often, and a dropped route's buses go to the routes that overlap it.

## A plan

A plan is a network plus a number of buses for each route. The numbers are fractional
"bus-equivalents" so small changes count; headway = round-trip running time × (1 +
`layover_share`) ÷ buses, never below `min_headway_min`. Today's plan has 1,916
bus-equivalents on 201 routes. Rounding each route up to whole buses, as the daily-service
measures do, gives 2,015.

## What is minimised

The average door-to-door time over a fixed sample of trips, counting a trip that cannot
be made within `max_trip_min` (120) as 120 minutes, so losing access is penalised.

- The sample: `redesign_origins` (100) origins drawn by population with
  `redesign_seed` (11), one point per population hexagon. From each origin, trips go to
  every zone by the gravity model of [methodology.md](methodology.md#6-demand); the
  lightest destinations are skipped once 99.5% of the origin's trips are covered.
- Scoring a plan takes under a second, so hundreds of changes can be tried.
- Because every plan is scored on the same trips, differences between plans are not
  sampling noise.

## Riders per route

Drops and frequency shifts need to know how many people ride each route.

- Counted boardings exist for the 56 BakuBus routes (opendata.az, weekday average of
  the latest month).
- Estimated boardings stand in for the other routes: the model's boardings, scaled so
  that, over the counted routes, the model's total equals the counts' total.

A count always wins over the model. A route the model underrates is therefore never
dropped for looking empty, which happened to 595, 149 and 140E in the first version of
the search. `output/redesign/routes.csv` gives the figure used for each route and its
source. Counts only steer which changes are tried. Whether a change is kept is still
decided by door-to-door time in the model.

### Which routes gain or lose buses

A route's riders wait on average half its headway, and its headway is its round-trip
time divided by its buses. One more bus on a route therefore saves its riders about
riders × headway ÷ buses ÷ 2 minutes of waiting a day.

A shift moves buses from the routes where that saving is smallest to those where it is
largest. This is the idea behind the square-root rule of frequency setting: with a fixed
fleet, total waiting is lowest when buses grow with the square root of riders × round-trip
time. Unlike riders per bus, the saving falls quickly as a short route gains buses.

## Rules every change must keep

| Rule | Setting |
|---|---|
| The total number of buses stays the same | (built in) |
| No more than this many people may lose their last stop within `max_access_walk_m` in one change | `redesign_max_people_losing_stop` = 500 |
| ...or across all changes together | `redesign_max_people_losing_stop_total` = 3000 |
| No route is made to run less often than every `max_headway_min` (30) minutes by moving its buses away | `max_headway_min` |
| No route gets buses beyond what it can use at `min_headway_min` (3) minutes | `min_headway_min` |
| A merge needs the route it merges into to still exist | (built in) |
| A route with at least this many counted weekday boardings is never dropped | `redesign_protect_boardings` = 1000 |
| Protected routes are never merged, dropped, straightened, stop-balanced or thinned out; they may gain buses | `redesign_protected_routes` = ["180"] |

People who lose their stop are counted on the finer seven-points-per-hexagon population.

## The changes it tries

| Kind | What it does | Candidates |
|---|---|---|
| merge | Drops a route whose stops are mostly (at least 85%) on another route; its buses go to the up to three routes that share most of its stops | Every near-duplicate pair, closest first, one per route |
| drop | Drops a route; its buses go to the routes that share most of its stops, or across the network if none do | The `redesign_max_drop` (20) routes with the fewest boardings a day per bus ([counted or estimated](#riders-per-route)), leaving out protected routes and routes with at least `redesign_protect_boardings` counted boardings |
| straighten | Replaces a detour with the shortest path between its two end stops along stop-to-stop links that some route drives today, in the right direction; the route stops at the stops on that path. Two stop poles less than 60 m apart count as one place | Detours whose straight path is at least 500 m shorter; the `redesign_max_straighten` (80) that save most time |
| stops | Stop balancing at 250 m (then 300 m), keeping any stop that is someone's only one within walking distance | Once, after the others |
| shift | Moves `redesign_shift_share` (20%) of the buses of the 5, 10 or 20 routes where a bus [saves riders the least waiting](#which-routes-gain-or-lose-buses) to the same number of routes where it saves the most, in proportion to that saving. Protected routes never give buses | Up to `redesign_shift_rounds` (4) rounds |

## The search, step by step

1. Score today's plan, and work out [boardings per route](#riders-per-route), counted
   where known and estimated elsewhere.
2. Build the merge, drop and straighten candidates.
3. Score each candidate alone against today's plan. Keep those that improve the average
   by more than `redesign_min_gain_min` (0.005 minutes) without breaking a rule.
4. Apply them in order of improvement. Before each one, score it again against the plan
   as it stands, since earlier changes alter its effect, and keep it only if it still helps.
5. Try stop balancing at 250 m, then 300 m, and keep the first that helps.
6. Up to four rounds: recount riders per route, try the three shifts, keep the best one
   that helps.
7. Independent check: score today's plan and the result on a different, larger
   sample (300 origins, seed 7, seven points per hexagon, the same model as `measure.py`).
8. Fleet option: find, by halving the interval six times, the smallest share of the
   new plan's buses (scaled evenly) whose average trip on the independent sample is no
   longer than today's. That is the saving if the improvement is taken as fewer buses
   instead of faster trips.

The run takes about two minutes and is deterministic: the same inputs give the same files.

## Reading the result

- `output/redesign/changes.csv`: each kept change in order, with the average minutes
  before and after on the search sample and the people who lost their last stop.
- `output/redesign/routes.csv`: each route's status (kept, straightened, merged,
  dropped), whether it is protected, the boardings used for it and their source, and its
  buses, headway and length before and after.
- `output/redesign/summary.json`: the independent check, the fleet option, settings and
  inputs.
- `output/redesign/network.geojson`: the redesigned network on a map. GitHub draws it;
  blue lines are kept, green straightened, red dropped or merged.
- `output/redesign/gtfs_today.zip` and `gtfs_redesign.zip`: both networks as GTFS feeds,
  to open in other tools such as r5py or a GTFS viewer.

The latest result is described in [results.md](results.md#the-redesign).

## How to treat the result

I treat the result as candidate changes for people who know the city to review, not a
finished plan. Each dropped or merged route should be checked with its operator and
riders, because the model does not know contracts, depots, school runs or vehicle
types. Each straightened detour should be looked at on the map: the shortest path may
use a street that is unsuitable, and the stops it skips may serve a hospital or school.
The inputs are what they are: headways are estimates, the demand model matches observed
ridership only moderately (0.58), and there is no crowding. For the 145 routes without
counts, riders are estimates and can be far off, so the estimate behind every dropped
route and every route that gains or loses many buses deserves a look; in the latest
result, route 519, a 3-stop shuttle the model credits with 14,700 boardings a day, goes
from every 15 to every 3 minutes. When local knowledge says a route must not be changed,
add it to `redesign_protected_routes` and run the search again: a protected route is
never merged, dropped or straightened, keeps its stops and never gives up buses, but it
can still receive buses, so protecting 519 would not hold it at every 15 minutes.

## Tuning

```sh
python3 redesign.py --set redesign_max_people_losing_stop=0 \
                    --set redesign_max_people_losing_stop_total=0   # nobody may lose their stop
python3 redesign.py --set redesign_origins=200                     # steadier, about twice as slow
python3 redesign.py --set redesign_max_drop=0                      # never drop a route
python3 redesign.py --set transfer_penalty_min=8                   # riders dislike changes more
python3 redesign.py --set 'redesign_protected_routes=["180", "519"]'   # also protect 519 (it can still gain buses)
python3 redesign.py --set redesign_protect_boardings=0             # let the search drop any route
```

Use `--out output/redesign_<name>` to keep variants side by side.

## Limitations

The search improves today's routes and invents none; generating new routes (for
example k-shortest paths between busy places) is the next step in
[roadmap.md](roadmap.md). It is greedy, keeping every improving change and never undoing
one, so simulated annealing or NSGA-II could find better combinations. And some of the
gain does not carry over to new trips: counting impossible trips at 120 minutes, the
average improved by 1.35 minutes on the search sample (79.66 to 78.31) but by 0.76
minutes on the independent check (74.82 to 74.06), which is the figure I quote.

The model underneath has its own gaps. There is no vehicle capacity, so a route can be
given more riders than its buses carry. Headways for 145 routes come from the zone
table, not data. Counts describe today's network, so when a merge moves riders onto a
counted route its count is not raised and later shifts may undervalue that route; and
counts decide which changes are tried, but the model's demand decides which are kept,
with 145 routes having no counts at all. The metro is not part of the travel model; it
only attracts trips.

## Extending it

A new kind of change is a class with `kind`, `routes`, `apply(plan, ctx)` returning a new
`Plan` (or `None` if it no longer applies) and `describe(network)`. Add its candidates in
`candidates()` or a step in `search()`; the scoring, the rules and the logging apply to it
automatically. See [code.md](code.md#extending-the-code).
