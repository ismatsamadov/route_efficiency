# Roadmap

Where I think the work stands on 23 October 2026, and what I would do next. This page is
about what is missing, not what has been built.

## What I would do next

The weakest part of the work is demand. The gravity model ranks routes against the
BakuBus counts at only 0.58, and 145 of the 201 routes have no counts at all, so the
redesign's bus moves rest on estimates. Route 519 is the warning sign: a 3-stop shuttle
that the model credits with 14,700 boardings a day and that the search therefore runs
every 3 minutes. Nothing I can do with public data fixes this, and the data that would
(real headways, boardings for the other carriers' routes, BakıKart validations) cannot
be obtained from AYNA, so the estimates are what the work has to live with and the
paper has to say so plainly.

Until that data exists there are two things I can do alone that would change the
answer, and one I have to wait for. The wait is for the map: AYNA has been launching a
new network since January 2026, but on 23 October 2026 the map API still returned
exactly the data of 6 May ([data.md](data.md#when-the-data-is-from)), so the
before-and-after study has to wait until the API changes; when it does, a new scrape
and a rerun of the three scripts will show which findings survive. The first thing I
can do now is the metro. Today metro stations only attract trips, but many Baku trips
combine bus and metro and some bus routes exist mainly to feed it, so trips that would
use the metro look slower or impossible by bus. Its data is now in place
([data.md](data.md#metro)): stations, the five train services, running times from the
operator's own journey planner, published intervals and track distances, in
`data/metro/` and `data/metro_headways.csv`. What remains is to put them into the travel
graph, with walking links between stations and bus stops, and to decide which metro to
model: the one before 15 August 2026, with green trains running through to Həzi
Aslanov, or today's, cut between Nizami and 28 May for the 11 months the works are
planned to take. The second is vehicle capacity: a maximum-load rule (buses needed =
peak load ÷ bus capacity) so that a frequency shift cannot hand a route more riders
than its buses carry.

The walking check of 25 October 2026 ([results.md](results.md#who-the-network-reaches))
adds a third: the streets and paths of OpenStreetMap are now in the repository
(`data/external/osm/osm_walk_network.json.gz`, read by `busnet/walking.py`), and the
walk to the nearest stop along them is typically 1.54 times the straight line, against
the 1.3 the travel model assumes for every walk. Putting that network into the model's
access and transfer walks, and into the redesign's coverage guard, would lengthen
modelled trips and tighten the guard; the check measures the gap but does not yet close
it.

I would also calibrate the demand model properly: fit `trip_decay_km`,
`destination_share` and `destination_weights` against the observed boardings, try a
doubly constrained gravity model, and keep part of the routes aside for checking so the
fit is not tuned to the data that judges it. That should raise the fair 0.58, but it
would still be calibration against 56 routes of one carrier.

The benchmark test of 27 October 2026 ([benchmark.md](benchmark.md)) suggests one
cheap change to the search itself: on Mumford1 to Mumford3, repeating the
straightening passes until one keeps nothing adds 34 to 53% to the gain in travel time
of a single pass, and `redesign.py` makes a single pass. Repeating its passes, and checking the gain on the
independent sample as before, would show whether Baku's minute is an underestimate.

Everything else can wait, because it would make the method look more serious without
changing the answer much: generating new candidate routes (k-shortest paths between
busy terminals, metro stations and destinations, splitting long routes, cutting loops),
replacing the greedy search with simulated annealing or NSGA-II from pymoo, which can
undo earlier changes, comparing travel times with r5py, and extending the tests to the
kinds of change in `busnet/optimize.py`. The benchmark networks showed what such
methods buy: on Mumford's networks they reach far lower travel times than straightening
a published route set does. The GTFS feeds now pass MobilityData's validator with no
errors (`validate_gtfs.py`); its remaining warnings are AYNA's, chiefly stops that sit
far from their own route's line.

## What this version cannot do

- Headways are estimated for 200 of the 201 routes (55 from boardings, 145 by service
  type, 1 published), so waiting times, fleet, bus-hours and fuel per route are
  approximate.
- Demand comes from a gravity model that ranks routes at 0.58, so estimated riders per
  route can be far off; the redesign uses counts for the 56 BakuBus routes and
  estimates for the other 145.
- The metro is not in the travel graph; there is no vehicle capacity or crowding; there
  is one all-day weekday average with no peak, night or weekend pattern; walking is
  straight-line distance times 1.3, so walks across rail lines, motorways or the sea
  look shorter than they are (along OpenStreetMap's streets and paths the walk to the
  nearest stop is typically 1.54 times the line, and 66% of people within 400 m in a
  straight line becomes 45%; [results.md](results.md#who-the-network-reaches)); and
  speeds are set by service type, not by street.
- Observed boardings exist only for BakuBus, so 145 routes of other carriers have
  nothing to check against.
- The map API returned the same data on 23 October 2026 as on 6 May, while AYNA has
  been launching a new network since January, so the map may lag the street and mix
  old and new routes; 7 routes have no stops, and route 180 (Pirallahı) looks cut off
  because its connecting routes are missing from the data.
- The population grid is from November 2023: 3.04 million people in the study area
  against 3.22 million official for 2026.
- The search is greedy and only changes existing routes, so it finds improvements, not
  the best network. On the benchmark networks it improves published route sets on both
  scores, but methods that build and reshape routes reach far lower travel times
  ([benchmark.md](benchmark.md)).
- Fuel is in diesel-equivalent litres; CNG and electric buses are not modelled
  separately.
- The loader reads only AYNA's tables, so another city needs a reader for its own map
  format (GTFS, for example) before anything else runs; the service types that key the
  headway and speed settings are AYNA's names too.

## Questions that are not mine to answer

Several settings are really policy choices, and I have only picked defaults for them.
Whether the redesign's gain should be taken as faster trips with today's fleet or as
today's trip times with about 12% fewer buses is the first; the results report both.
How many people may lose a stop within walking distance so that the rest travel faster
is the second: today the limits are 500 per change and 3,000 in total, at 500 m
(`redesign_max_people_losing_stop`, `redesign_max_people_losing_stop_total`,
`max_access_walk_m`), and the robustness run shows that a limit of zero costs nothing
here. How much riders mind changing buses is the third: the model counts each change as
5 extra minutes on top of waiting (`transfer_penalty_min`), a figure a survey or AYNA's
own model could set for Baku. Which routes must stay as they are, whether express
routes, school services or routes bound by contracts, belongs in
`redesign_protected_routes`, which today holds only 180. Whether routes of different
carriers can be merged at all matters, because 59 of the 72 near-duplicate pairs
involve two carriers; the gross-cost contracts AYNA plans would make it easier. And how
any of this compares with AYNA's own redesign I cannot say: its consultant's network
needs about 2,800 buses, against about 2,300 in service.

## When new data arrives

Real headways go into `data/headways.csv`; then rerun the three scripts. For a new
network snapshot, run `python3 <repository>/data/ayna_scraper.py` in an empty folder
outside the repository (it writes `ayna_data/ayna.db` there), replace `data/ayna.db`
with that file and rerun the three scripts; the repairs are detected from the data, so
they adapt to the new snapshot, and `output/repairs.txt` shows any new ones. Fresh
public data comes from `python3 data/fetch_external.py --refresh`, and a fresh metro
from `python3 data/metro_scraper.py` followed by `python3 data/build_metro.py`. AYNA's
bicycle lanes and parking points come with the other opendata.az files; after a refresh,
`python3 bicycle.py` puts the new lanes beside the network again, and when AYNA says
what the 649 MPS points in its parking file are, or publishes when each lane was built
and what separates it from traffic, `docs/data.md` is where that goes. Whatever changes, I
commit the new data and the regenerated `output/` together, so results always match
their inputs.
