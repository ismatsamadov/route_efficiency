# Roadmap

Where the work stands on 23 October 2026, what to do next, what the current version
cannot do, and which decisions and data are needed from people outside the code.

## Done

| Step | Where |
|---|---|
| Audit of the AYNA snapshot, and automatic repair of its defects (23 repairs) | `busnet/model.py`, [data.md](data.md) |
| Network measures: directness, detours, overlap, trunk corridors, stop spacing, coverage | `busnet/metrics.py`, `output/` |
| Headways from published data, boardings or service type; daily trips, bus-hours, bus-km, fleet, fuel, CO₂ | `busnet/service.py` |
| Door-to-door travel model with demand from population, OpenStreetMap and metro; check against observed boardings | `busnet/graph.py`, `busnet/metrics.py`, `busnet/destinations.py` |
| Every input committed; every assumption in `busnet.toml`; results regenerate byte for byte | `data/`, `busnet.toml` |
| Stop-balancing scenario | `measure.py --scenario stop-balancing` |
| GTFS export of today's network and of the redesign | `busnet/gtfs.py` |
| First redesign search, with an independent check and a fleet-saving option | `busnet/optimize.py`, `redesign.py`, [results.md](results.md#the-first-redesign) |
| Documentation | `docs/` |

## Next, in order of value

1. **Use observed ridership in the redesign.** The search dropped routes 595, 149 and
   140E, which carry about 10,100 boardings a weekday that the model does not see
   ([results.md](results.md#check-these-before-acting)). Two changes would fix this:
   - In `optimize.candidates()`, never offer a route with observed boardings as a drop
     unless its observed boardings per bus are also low.
   - In `Shift`, rank routes by observed boardings where they exist.
2. **Fix the riders-per-bus ranking.** It favours very short routes: route 519, with 3
   stops, ends up every 3.7 minutes. Better options:
   - rank by the time a bus would save riders, not by riders per bus;
   - or cap the frequency gain of short routes.
3. **Ask AYNA for data** ([list below](#data-to-request-from-ayna-and-the-operators)).
   Real headways alone would replace 200 estimates.
4. **Improve the demand model.** Raise the fair ridership correlation (0.58) by calibrating
   `trip_decay_km`, `destination_share` and `destination_weights` against the observed
   boardings, and by trying a doubly constrained gravity model. Keep part of the routes
   aside for checking, so the fit is not tuned to the data that judges it.
5. **Add the metro to the travel model.** Today metro stations only attract trips. Many
   Baku trips combine bus and metro, and some bus routes exist mainly to feed it.
6. **Add vehicle capacity.** Set frequencies with a maximum-load rule (buses needed =
   peak load ÷ bus capacity), so no route is given more riders than it can carry.
7. **Generate new routes.** So far the search only changes existing routes. New
   candidates could come from:
   - k-shortest paths between busy terminals, metro stations and destinations;
   - splitting long routes;
   - cutting loops.
8. **Search better.** Try simulated annealing, or NSGA-II from pymoo, to trade rider time
   against bus-hours. Both can also undo earlier changes, which the greedy search never
   does.
9. **Check against benchmarks.** Run the evaluator on the Mandl and Mumford test networks
   and compare with published results ([research.md](research.md#5-designing-a-network-by-computer)).
10. **Add tests.**
    - Unit tests for `geo.match_stops`, `service.route_headways`, `config.load_config`
      errors and `Plan` arithmetic.
    - A regression test that regenerates `output/` and compares it with the committed
      files.
11. **Validate the GTFS feeds** with the MobilityData validator. Compare travel times with
    r5py.
12. **Update the published efficiency report** with the redesign and its map. The export
    script for the report already includes the redesign data.

## Limitations of the current version

| Limitation | Effect |
|---|---|
| Headways are estimated: 1 published, 55 from boardings, 145 by service type | Waiting times, fleet, bus-hours and fuel per route are approximate |
| Demand comes from a gravity model, which ranks routes with a correlation of 0.58 | Modelled riders per route can be far off. The redesign trusts them for drops and shifts |
| No metro in the travel graph | Trips that would use the metro look slower or impossible by bus |
| No vehicle capacity or crowding | Busy routes look better than they are; frequency shifts can overload them |
| One all-day average, weekdays only | No peak or night service; no weekend pattern |
| Straight-line walking × 1.3 | Walks across rail lines, motorways or the sea look shorter than they are |
| Speeds by service type, not by street | Congested streets and bus lanes are not distinguished |
| Observed boardings only for BakuBus | 145 routes of other carriers have no ridership to check against |
| Snapshot of 6 May 2026 | AYNA's new network began launching in January 2026, so the snapshot may mix old and new routes. 7 routes have no stops, and route 180 (Pirallahı) looks cut off |
| Population grid from November 2023 | 3.04 million people in the study area against 3.22 million official for 2026 |
| Greedy search over existing routes | It finds improvements, not the best network; it invents no new routes |
| Fuel in diesel-equivalent litres | CNG and electric buses are not modelled separately |

## Open questions for decision-makers

These are choices for people, not code. Each one has a setting that can follow the
answer.

1. **Faster trips or fewer buses?** The redesign can take its gain as shorter trips
   with today's fleet, or as today's trip times with about 12% fewer buses. Both are
   reported.
2. **Ridership or coverage?** How many people may lose a stop within walking distance
   for the rest to travel faster? Today the limits are 500 per change and 3,000 in
   total, at 500 m (`redesign_max_people_losing_stop`,
   `redesign_max_people_losing_stop_total`, `max_access_walk_m`).
3. **How much do riders mind changing buses?** The model counts each change as 5 extra
   minutes on top of waiting (`transfer_penalty_min`). A survey or AYNA's own model
   could set this for Baku.
4. **Which routes are fixed?** For example express routes, school services, or routes
   bound by contracts. A list of protected routes could be added as a setting.
5. **Can routes of different carriers be merged?** 59 of the 72 near-duplicate pairs
   involve two carriers. The gross-cost contracts AYNA plans would make this easier.
6. **How does this compare with AYNA's own redesign?** Its consultant's network needs
   about 2,800 buses, against about 2,300 in service.

## Data to request from AYNA and the operators

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

## Updating the work when data arrives

- **Real headways.** Add rows to `data/headways.csv`, then rerun both scripts.
- **A new network snapshot.**
  1. In an empty folder outside the repository, run
     `python3 <repository>/data/ayna_scraper.py`. It writes `ayna_data/ayna.db` in that
     folder.
  2. Replace `data/ayna.db` with that file.
  3. Rerun both scripts. The repairs detect defects from the data, so they adapt to
     the new snapshot. Check `output/repairs.txt` for new ones.
- **Fresh public data.** Run `python3 data/fetch_external.py --refresh`.
- **Commit together.** Commit new data and the regenerated `output/` in the same commit,
  so results always match their inputs.
