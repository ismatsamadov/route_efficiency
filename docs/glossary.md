# Glossary

Terms as they are used in this repository. Setting names are in `code` font
([configuration.md](configuration.md)).

| Term | Meaning |
|---|---|
| Accessibility | How easily people can reach places by bus. Here: door-to-door times between homes and destinations from the travel model |
| AYNA | Azərbaycan Yerüstü Nəqliyyat Agentliyi, the agency that plans Baku's surface transport and publishes the bus map the data comes from |
| BakıKart | Baku's transport smart card |
| BakuBus | The largest carrier in the data (55 of the 201 routes with stops, among 42 carriers), and the only one whose boardings per route are published (by Bakı Metropoliteni on opendata.az) |
| Boarding | One rider getting on one bus. A trip with one change is two boardings |
| Bus-equivalent | A fractional number of buses. The redesign assigns fractions so that small changes count; whole buses are the fractions rounded up per route |
| Bus-hours, bus-km | Hours and kilometres that buses drive in service in a day. The main operating costs |
| Chainage | Distance along a route's path from its first stop, at each stop |
| Circuity | Distance along the route ÷ straight-line distance. End-to-end circuity uses the two end stops; rider circuity averages over pairs of stops at least 1 km apart |
| CNG | Compressed natural gas; most BakuBus buses run on it |
| Counted boardings | Boardings per route from the BakuBus counts on opendata.az, as opposed to estimated (modelled) boardings |
| Coverage | The share of people with a served stop within `coverage_radius_m` (400 m) |
| Coverage guard | The redesign rule that limits how many people may lose their last stop within `max_access_walk_m` |
| Cruise speed | A bus's moving speed between stops, set by working zone (`cruise_kmh`) |
| Destination share | The share of trip ends drawn to destinations (schools, offices, shops, metro) rather than homes (`destination_share`) |
| Detour | A stretch where a route travels at least 2.5 times the straight line between two of its stops and at least 1.5 km further |
| Direction | One of a route's two ways: 1 outbound, 2 return, as in the AYNA data |
| Distance decay | How quickly trips become less likely with distance: exp(−distance ÷ `trip_decay_km`) |
| Door-to-door time | Walk to the stop + wait + ride + any changes (with their penalty) + walk from the stop |
| Drop | A redesign change that removes a route and gives its buses to the routes that overlap it |
| Duplication ratio | Total route length ÷ length of distinct stop-to-stop links. 1 means no two routes share a link |
| Express route | A route in an express working zone ("ekspres" in the AYNA data): E1, H1, 72, 120E, 121E, 140E, 150E, 594 and 595. Near-duplicate checks leave them out, since skipping a local route's stops is their purpose |
| Fleet | Buses needed to run the service: round-trip time × (1 + `layover_share`) ÷ headway, per route |
| Fleet-saving option | The share of the redesigned network's buses that still gives today's average trip time |
| Frequency, headway | How often buses come. The headway is the minutes between buses; frequency is buses per hour |
| GTFS | General Transit Feed Specification, the standard file format for transit networks and timetables. `frequencies.txt` describes service as "every N minutes" |
| Gravity model | A demand model: trips between two places grow with the people at one end and the pull at the other, and fall with distance |
| Greedy local search | A search that keeps every change that improves the score, one at a time, and never undoes one |
| H3 hexagon | A cell of Uber's hexagonal grid. Kontur's population uses resolution 8 cells, about 0.74 km² |
| Hub | A stop the AYNA data flags as a transport hub; stop balancing never removes one |
| Independent check | Scoring the redesign on a different, larger sample of trips than the search used, so the reported gain is not tuned to the search sample |
| Kontur Population | The population grid used here: people per H3 hexagon, release November 2023 |
| Layover | Recovery time at the end of a trip before the next one, as a share of running time (`layover_share`) |
| Link | The path between two consecutive stops of a route direction |
| Loop route | A route whose ends are less than 1 km apart, or whose path is over 3 times the straight line between them |
| Merge | A redesign change that removes a route whose stops are mostly (at least 85%) served by another route, and gives its buses to the routes it overlaps |
| Near-duplicate | A route with at least 85% of its stops also served by one other route |
| NSGA-II | A genetic algorithm that finds the best trade-offs between two or more goals |
| OpenStreetMap, Overpass | The open world map, and the service used to download features from it |
| Order break | A stop that cannot be placed on its route's shape in order. Many order breaks mean the shape belongs to another direction, or is wrong |
| Pattern | One direction of one route in the code: ordered stops, chainage and path |
| Plan | In the redesign: a network plus the buses assigned to each route |
| Protected route | A route the redesign leaves as it is, apart from giving it buses (`redesign_protected_routes`) |
| Pull (attraction) | How strongly a zone draws trip ends: a mix of its population and its destinations |
| Reference fleet | Buses reported in daily service, 2,300 (`reference_fleet`), used to check the estimated headways |
| Repair | An automatic fix of a defect in the AYNA data when it is loaded, listed in `output/repairs.txt` |
| Ridership-derived headway | A headway estimated from observed boardings: enough trips for each to carry `boardings_per_trip` riders |
| Route | A bus line with a number, such as 7A. Has one or two directions |
| Search sample | The fixed set of trips the redesign scores every change on (`redesign_origins`, `redesign_seed`) |
| Service hours | Hours of service a day (`service_hours`, 17: 06:00 to 23:00) |
| Shift | A redesign change that moves buses from the routes where one more bus would save riders the least waiting to the routes where it would save the most |
| Simulated annealing | A search that sometimes accepts a worse change, to escape a local optimum |
| Square-root rule | The classic result that, to minimise riders' total waiting with a fixed fleet, buses on a route should grow with the square root of its riders × round-trip time. Equivalently, one more bus should save the same waiting on every route; the redesign's shift moves buses towards that |
| Spearman correlation | How similarly two lists rank the same items: 1 is the same order, 0 no relation |
| Stop balancing | Removing stops that are very close to their neighbours, so buses stop less often |
| Stop gap | Distance along the route between two consecutive stops |
| Stop loss | Seconds a bus loses at each stop: braking, doors, pulling out (`stop_loss_s`) |
| Straighten | A redesign change that replaces a detour with the shortest path along links buses already drive |
| TCQSM | Transit Capacity and Quality of Service Manual, a US reference for service levels |
| TNDP, TNDFSP | Transit network design problem; with frequency setting. The research field of choosing routes and frequencies |
| Transfer, change | Getting off one bus and onto another during a trip |
| Transfer penalty | Extra minutes a rider feels for each change, on top of waiting (`transfer_penalty_min`) |
| Trunk corridor | A stretch of at least 1 km where at least 8 routes share every link |
| Working zone | AYNA's service type for a route: urban, suburban, between settlements, within a settlement, intercity, and express variants |
