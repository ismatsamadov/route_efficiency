# Roadmap

Where I think the work stands on 23 October 2026, and what I would do next. This page is
about what is missing, not what has been built.

## What I would do next

The weakest part of the work is demand. The gravity model ranks routes against the
BakuBus counts at only 0.58, and 145 of the 201 routes have no counts at all, so the
redesign's bus moves rest on estimates. Route 519 is the warning sign: a 3-stop shuttle
that the model credits with 14,700 boardings a day and that the search therefore runs
every 3 minutes. Nothing I can do with public data fixes this. It needs boardings for
the other carriers' routes and, ideally, BakıKart validations, which is why the first
thing on my list is to ask AYNA for the data in the table at the end of this page. Real
headways would replace 200 estimates at the same time.

Until that data exists there are three things I can do alone that would change the
answer. The first is a new snapshot. The network is from 6 May 2026 and AYNA has been
launching a new one since January ([data.md](data.md#when-the-data-is-from)), so I do
not know which findings still hold; scraping the map again and rerunning the three
scripts would tell me, and it would turn this snapshot into the "before" of a
before-and-after study. The second is the metro. Today metro stations only attract
trips, but many Baku trips combine bus and metro and some bus routes exist mainly to
feed it, so trips that would use the metro look slower or impossible by bus. The third
is vehicle capacity: a maximum-load rule (buses needed = peak load ÷ bus capacity) so
that a frequency shift cannot hand a route more riders than its buses carry.

I would also calibrate the demand model properly: fit `trip_decay_km`,
`destination_share` and `destination_weights` against the observed boardings, try a
doubly constrained gravity model, and keep part of the routes aside for checking so the
fit is not tuned to the data that judges it. That should raise the fair 0.58, but it
would still be calibration against 56 routes of one carrier.

Everything else can wait, because it would make the method look more serious without
changing the answer much: generating new candidate routes (k-shortest paths between
busy terminals, metro stations and destinations, splitting long routes, cutting loops),
replacing the greedy search with simulated annealing or NSGA-II from pymoo, which can
undo earlier changes, running the evaluator on the Mandl and Mumford benchmarks to
compare with published results, validating the GTFS feeds with the MobilityData
validator and comparing travel times with r5py, and extending the tests to the kinds of
change in `busnet/optimize.py` and to the GTFS writer.

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
  look shorter than they are; and speeds are set by service type, not by street.
- Observed boardings exist only for BakuBus, so 145 routes of other carriers have
  nothing to check against.
- The snapshot is from 6 May 2026 and may mix old and new routes; 7 routes have no
  stops, and route 180 (Pirallahı) looks cut off because its connecting routes are
  missing from the data.
- The population grid is from November 2023: 3.04 million people in the study area
  against 3.22 million official for 2026.
- The search is greedy and only changes existing routes, so it finds improvements, not
  the best network.
- Fuel is in diesel-equivalent litres; CNG and electric buses are not modelled
  separately.

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

## Data I would ask AYNA for

| Data | Replaces | Ideal format |
|---|---|---|
| Timetables or headways per route, by time of day | Headway estimates for 200 routes | GTFS, or a CSV like `data/headways.csv` |
| Archived vehicle positions (AVL/GPS) | Assumed speeds, stop losses and layover; shows bunching and reliability | CSV of positions, or GTFS-Realtime |
| BakıKart validations: anonymised card id, time, stop or vehicle | The gravity model: where riders really travel, through trip chaining | CSV |
| Boardings for routes of other carriers | Ridership for the 145 routes without it | Same as the BakuBus file on opendata.az |
| Buses per route, with type, capacity and fuel | Estimated fleet per route; capacity; fuel by type | CSV |
| Fuel or energy use per route or depot | The fuel model | CSV |
| Depot locations | Empty running to and from routes | Coordinates |
| The new network's routes, as launched | An up-to-date snapshot | GTFS, or a new scrape of the AYNA map |
| Passenger counts by stop | Which stops can go, and which detours riders actually use | CSV |

## When new data arrives

Real headways go into `data/headways.csv`; then rerun the three scripts. For a new
network snapshot, run `python3 <repository>/data/ayna_scraper.py` in an empty folder
outside the repository (it writes `ayna_data/ayna.db` there), replace `data/ayna.db`
with that file and rerun the three scripts; the repairs are detected from the data, so
they adapt to the new snapshot, and `output/repairs.txt` shows any new ones. Fresh
public data comes from `python3 data/fetch_external.py --refresh`. Whatever changes, I
commit the new data and the regenerated `output/` together, so results always match
their inputs.
