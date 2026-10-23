# How efficient are Baku's bus routes? An open-data measurement and a fleet-neutral redesign

Ismat Samadov, Independent researcher, Baku, Azerbaijan. ORCID 0009-0007-7919-4950.

Draft of 23 October 2026 for Case Studies on Transport Policy (article; target under
7,000 words). Numbers are those of release v1.0.0 of the repository (DOI
10.5281/zenodo.23602094); every one of them can be regenerated from it.

## Highlights

- Baku's 201 bus routes measured from public data: 74 very indirect or loops, 1.93 routes per link
- 271 detours add 939 km per trip cycle; 217 of them serve nobody who lacks another route
- A gravity demand model built from open data ranks routes against counts at 0.58
- A fleet-neutral redesign gives today's travel times with about 12% fewer buses
- The gain holds on ten trip samples and under eleven alternative assumptions

## Abstract

Baku's bus network of about 200 routes is being redesigned, but no public evaluation of
it exists and the data needed for one, timetables, vehicle positions and
origin–destination flows, is not published. This paper asks how much a bus network can
be measured, and how much a redesign can be tested, from public data alone. From the
route and stop geometry of the transport agency's public map, a population grid,
OpenStreetMap destinations, metro entries and the daily boardings of one operator, I
repair the geometry, measure directness, duplication, detours, stop spacing and
coverage, and build a door-to-door travel model with a gravity demand model whose route
ranking agrees with observed boardings at a Spearman correlation of 0.58. Only 29 of 201
routes run within 1.4 times the straight line between their ends; buses run 7,398 km of
route over 3,824 km of distinct links; 271 detours add 939 km to one trip in each
direction of every route; 23.9% of stop gaps are under 300 m; and 66% of the 3.04
million residents live within 400 m of a stop. A greedy search that keeps today's fleet
and applies the changes used by redesigns elsewhere shortens the average modelled trip
from 51.8 to 50.9 minutes, or delivers today's travel times with about 12% fewer buses,
fuel and CO₂. On ten independent trip samples the gain is 0.68–0.81 minutes, and under
eleven alternative assumptions 0.58–0.84; a stricter rule under which nobody loses a stop
gains as much as the default. The pipeline, data and results are released for others to
regenerate or apply to other cities with only a public map.

Keywords: bus network design; public transport; open data; accessibility; Baku;
transit network design problem

## 1. Introduction

Most of the world's cities run their buses on networks that grew route by route, and
many have found, when they finally redrew them, that fewer, straighter and more frequent
routes serve more people for the same money (Houston in 2015, Barcelona between 2012 and
2018, Dublin since 2021). Baku, a city of 2.4 million with a metropolitan area of 3.2
million, is in the middle of such a redesign: the transport agency AYNA has analysed all
routes with an international consultant on a digital twin of the city since 2023,
raised bus speeds with 114 km of bus lanes, and began launching a new network in
January 2026 (Ministry of Digital Development and Transport, 2023, 2026). What the
public can see of this is the agency's map of routes and stops and a handful of figures
in press releases. There is no published evaluation of the network, and the data that
such an evaluation normally rests on, timetables, vehicle positions and where riders
travel, is not public.

This paper asks a narrower question than the agency's consultant could: how much can be
learned about a bus network, and how far can a redesign be tested, from public data
alone? The answer matters beyond Baku. Many cities publish a map and little else, and a
method that works from the map, a population grid and OpenStreetMap can be applied
wherever those exist.

Three things are new here. First, a complete measurement of Baku's network from its
geometry, after repairing defects in the public data that would otherwise distort every
figure. Second, a door-to-door travel model built only from public data, with its
agreement against observed ridership stated rather than assumed. Third, a fleet-neutral
redesign search whose result is checked on trips it was not tuned to and under
alternative assumptions, so that the size of its gain and the uncertainty around it are
both reported. The whole pipeline, with every input and every result, is released as a
standard-library Python repository that regenerates the figures in this paper from
three commands.

I claim no new algorithm. The search is a greedy local search over today's routes, and
the findings are not forecasts: headways for most routes are estimated, the demand model
is a gravity model, and the network is described as the agency's map publishes it. What
the paper offers is a reproducible diagnosis, an estimate of what a cautious redesign
would gain, and an honest account of what that estimate depends on.

## 2. Background

### 2.1 Baku's bus network and its reform

Baku's surface public transport is planned by AYNA (Azərbaycan Yerüstü Nəqliyyat
Agentliyi) and operated by 42 carriers, of which the state operator BakuBus runs 55 of
the 201 routes in the agency's data. About 2,300 buses were in daily service in January
2026, up from 1,720 in 2022, and 55% of the fleet was described as eco-friendly
(Ministry of Digital Development and Transport, 2026). In December 2023 the Ministry
presented the Mobility Transformation Program, under which AYNA, with an international
consulting company, analysed all route lines and now optimises routes on a digital twin
of Baku; 1.6 million bus trips a day were reported (Ministry of Digital Development and
Transport, 2023). In November 2024 the minister reported that bus lanes and route
optimisation had raised the speed of buses in Baku from 18 to 22 km/h (Report.az,
2024). In September 2025 the consultant's assessment found weak integration between
Baku and Absheron routes, overlapping routes, and 17% of residents with limited access
to the bus network; the new network was expected to need about 2,800 buses, and
gross-cost contracts were planned (APA, 2025). The new network began launching in
January 2026 with eight routes.

None of the consultant's data is public. The agency's map API publishes routes, stops,
stop sequences and route shapes, and the state operator's daily boardings per route are
published on the national open-data portal; nothing else is. The map data used here
were scraped on 6 May 2026 and again on 23 October 2026; the two scrapes are identical
in every table, so the map had not yet been updated for the new network while the
boardings file already lists eight routes the map does not carry.

### 2.2 What other redesigns did, and what they measured

Whole-network redesigns elsewhere followed a similar recipe: fewer, straighter routes
that run more often, overlapping routes merged into frequent trunks, stops spaced
further apart, and bus lanes where routes stack up. Seoul reorganised all its bus
services on one day in 2004 into trunk and feeder routes with median bus lanes, one
fare and operators paid per vehicle-kilometre; bus speeds rose from 11 to 22 km/h by
2010, passengers by 20%, and operating cost fell by up to 9% (Allen, 2013). Houston
redrew nearly every route in 2015 within about the same budget, moving 80% of resources
to ridership and 20% to coverage; local bus ridership rose 1.2% in the first year,
Saturdays 13% and Sundays 34% (Schmitt, 2016; Walker, 2014, 2015). Barcelona's Nova
Xarxa replaced radial lines with 28 grid lines designed for 3- to 8-minute headways;
ridership on replaced corridors rose 6% to 24%, with about 26% of trips involving a
transfer (Badia et al., 2016; Lynn, 2017). Moscow's Magistral consolidated 39 central
routes into 17 in 2016 and reported surface ridership up by a third in a year (ITU,
2018). Dublin's BusConnects, rolled out area by area since 2021 with added service,
reports boardings up 48% in redesigned areas against 8% elsewhere to the end of 2024
(BusConnects, 2025). Tbilisi and Tashkent, closer to Baku in their inherited networks,
replaced minibus-style service with larger buses and shorter headways and report
ridership up 30% and 26% (EBRD, 2024; Kun.uz, 2026). How much each gained went with
whether service was added at the same time.

Two measures recur in the planning guidelines these cities used. For riders, the
door-to-door time of walking, waiting, riding and changing, with a penalty per change,
and the share of residents within walking distance of a stop: the Transit Capacity and
Quality of Service Manual defines a bus route's coverage area as 400 m from a stop, and
Montreal data put the 85th percentile of home-based walks to a bus at 524 m
(El-Geneidy et al., 2014). For operators, bus-hours, bus-kilometres and the fleet
needed. Guidelines also exist for network shape: a Soviet planning norm of 1981, still
cited in the region, limited a route to 1.2–1.3 times the straight line between its
ends, loops excepted (RSFSR Ministry of Motor Transport, 1981); Miami-Dade and Denver
keep a detour only if the minutes it adds to through riders, divided by the riders it
serves, stay under five or three minutes (Miami-Dade Transit, 2005); average stop
spacing is about 352 m in the United States and 359 m across 38 cities elsewhere
(Devunuri et al., 2023), with agencies such as TriMet and TransLink aiming for 240–400 m
on local routes; and removing closely spaced stops saved TriMet nearly 6% of running
time with no significant ridership loss (El-Geneidy et al., 2006). A Russian study of
Bryansk calls sharing over 75% of a route's length with another route inappropriate
(Sivakov et al., 2022), and King County Metro's guidelines keep parallel routes at
least half a mile apart (King County Metro, 2021).

### 2.3 Designing a network by computer

Choosing a set of bus routes is the transit network design problem; choosing their
frequencies as well is the transit network design and frequency setting problem. Both
are NP-hard, and the literature searches rather than enumerates (Kepaptsoglou and
Karlaftis, 2009; Farahani et al., 2013; Ibarra-Rojas et al., 2015; Durán-Micco and
Vansteenwegen, 2022). Objectives are riders' time, including waiting and a transfer
penalty of about five minutes, the shares of demand served directly or with one or two
changes, and operator cost; constraints are the number and length of routes, coverage of
all stops, the fleet and a minimum frequency. Methods range from choosing routes from a
candidate pool, through local search, simulated annealing and tabu search, to
evolutionary algorithms and, recently, graph neural networks trained by reinforcement
learning, which report new best results on the Mumford benchmarks and up to 19% lower
cost in a simulation of the real network of Laval, Canada (Holliday et al., 2025). The
standard test networks, Mandl's 15 nodes and Mumford's 30 to 127, are far smaller than
Baku's 3,456 stops (Mandl, 1980; Mumford, 2013).

I use a greedy local search for three reasons. It is transparent, since every kept
change can be explained in one sentence, which matters when people have to approve it.
It runs on a laptop in minutes. And the quality of the answer depends far more on the
demand data than on the search: without origin–destination data, a better optimiser
would only optimise the same gravity model more thoroughly. The demand model follows the
gravity tradition (Simini et al., 2012; Pappalardo et al., 2022), and the two better
options, smart-card trip chaining, which recovered alighting points for over 80% of
boardings in Santiago (Munizaga and Palma, 2012), and mobile-phone records, which
produced four new routes for Abidjan (Berlingerio et al., 2013), need data that is not
available in Baku.

## 3. Data

### 3.1 Sources

Table 1 lists every input. All are public; all are committed in the repository with
their licences, so the results regenerate without network access.

Table 1. Data sources.

| Data | Source and date | Licence | Used for |
|---|---|---|---|
| 208 bus routes, 3,841 stops, stop sequences and 398 route shapes | AYNA map API (map-api.ayna.gov.az), scraped 23 October 2026; identical to a scrape of 6 May 2026 | None published; redistributed as a research snapshot with attribution | Routes, stops, order, geometry |
| Daily boardings per BakuBus route, 1 January to 30 September 2026 | Bakı Metropoliteni via opendata.az | CC BY | Headway estimates, model check, route ranking |
| Daily entries per metro station, and 98 exit coordinates of 27 stations | Bakı Metropoliteni via opendata.az | CC BY | Trip destinations |
| Population on H3 hexagons of about 0.74 km² | Kontur Population, release 2023-11-01 | CC BY | Coverage, trip origins and destinations |
| 5,628 destinations: schools, kindergartens, colleges, universities, hospitals, clinics, supermarkets, department stores, malls, marketplaces, offices, town halls, courthouses, railway and bus stations | OpenStreetMap via the Overpass API, 23 October 2026 | ODbL | Trip destinations |
| One published headway (route H1, every 20 minutes) | airport.az, August 2024 | | Headway where known |
| Official population by district, 1 January 2026 | State Statistical Committee | | Check of the grid |

The study area is the box around the served stops plus 2 km. It holds 2,707 hexagons
with 3.04 million people; the official figures for Baku, Sumqayıt and the Absheron
district total 3.22 million, consistent with a grid two years older. Each hexagon is
split into seven points that share its population, the way H3 subdivides a cell, so
that coverage is not judged from one point per hexagon.

### 3.2 Defects and repairs

The map data has defects that would distort every measure if taken at face value, and
none is documented. The route length field is the round-trip length, and the duration
field is the length divided by 0.6 on every route, so neither is a measurement. On 13
routes the two shapes are filed under the wrong direction; on three directions the shape
is stored backwards; one has latitude and longitude swapped; one has latitude equal to
longitude on every point; three are scrambled rings with straight jumps of 9 to 20 km;
two routes have no shape; one lists each direction's stops twice; and seven routes have
no stops at all.

Rather than fix these by hand, the loading code detects them from the data, so the
repairs survive a new scrape. Every stop is projected onto every segment of a shape, and
a dynamic programme places the stops along the shape so that their distance along it
never goes back by more than 30 m, minimising the total offset; a stop with no in-order
position is an order break. Each direction is scored against each stored shape and its
reverse, and the stored assignment is replaced only on clear evidence: at least two or
20% of the route's stops fewer order breaks, or no more breaks and a median offset below
70% of the current one. A shape that still cannot explain its stops, with more than two
or 10% of them out of order, a median offset over 60 m or a straight segment over 5 km,
is dropped and that direction is drawn as straight lines between stops. The 23 repairs
are logged. After them, 394 of 402 route directions use real shapes, the median stop
sits 7.2 m from its line and 90% sit within 13.7 m, and three directions keep one stop
slightly out of order.

### 3.3 The period described

The results describe the network as the agency's map published it on 6 May 2026 and
still published it on 23 October 2026, with ridership from September 2026. The map lags
the street: eight routes in the boardings file (M2 to M6, 500, 149E and 195E) do not
exist on the map. The findings therefore describe the inherited network that the
reform is replacing, which is the right object for a before-and-after comparison once
the map is updated.

## 4. Methods

### 4.1 Geometry measures

All distances are great-circle; grids and buffers use a flat projection centred on Baku,
accurate to better than 1% across the area. A pattern is one direction of one route:
its ordered stops, the path between them, and the distance along the path at each stop.
One-way length is the distance along the path at the last stop, averaged over a route's
directions. End-to-end circuity is path length divided by the straight line between the
first and last stop, undefined when they are less than 1 km apart; a route's shape class
comes from its less direct direction: direct up to 1.4, indirect to 2, very indirect to
3, and a loop above 3 or with ends less than 1 km apart. Excess over the shortest path
compares the path with the shortest route between the same two stops on a graph of every
stop-to-stop link that some route drives, both ways, plus links between stops less than
80 m apart, so that it asks how much longer the route is than buses could already go on
streets they use. Rider circuity averages, over every pair of stops at least 1 km apart,
the distance along the route divided by the straight line. A detour is a stretch of at
most 12 stops and 40% of the route whose path is at least 2.5 times the straight line
between its ends and at least 1.5 km longer; overlapping candidates keep the largest.
The duplication ratio is total route-kilometres of all directions divided by kilometres
of distinct directed links. A trunk corridor is a run of consecutive links at least
1 km long on which at least eight routes share every link. A near-duplicate is a route
of at least ten stops with at least 85% of them also served by one other route; express
routes are left out, since skipping a local route's stops is their purpose.

### 4.2 Running time, fuel and daily service

For one trip in one direction, running time is length divided by the moving speed of the
route's working zone plus 20 s at every stop after the first; fuel is 0.30 diesel-
equivalent litres per kilometre plus 0.05 litres per stop, which gives 43 L/100 km at
2.65 stops per kilometre, the Braunschweig test-cycle figure for diesel buses (Nylund
and Koponen, 2012); CO₂ is 2.67 kg per litre (IPCC, 2006). Moving speeds by zone (22 km/h
urban, 29 suburban and urban express, 36 suburban express, 25 within and 31 between
settlements, 40 intercity) were set so that total route-kilometres divided by total
running time over all directions equals the 22 km/h the agency reported. Fuel is kept
in diesel-equivalent litres because no split of the fleet by fuel is published and CNG
and diesel emit roughly the same CO₂ per kilometre.

Each route's headway is the first of: a published value (one route); an estimate from
observed boardings where they exist, as trips per direction equal to weekday boardings
divided by two and by 60 boardings per trip, over 17 service hours, kept between 3 and
30 minutes (55 routes); or a value by working zone, 10 minutes urban, 15 suburban and
urban express, 20 suburban express and settlement routes, 30 intercity (145 routes).
Trips a day, bus-hours, bus-kilometres and fuel follow from the headway, the round-trip
running time and length; buses needed per route are round-trip time times 1.15 for
layover divided by headway, rounded up. The implied fleet is compared with the 2,300
buses reported in service.

### 4.3 Demand

No origin–destination data is public, so trips are spread with a gravity model. Origins
are sampled in proportion to population. From each origin, trips end at every zone in
proportion to its pull times exp(−distance / 6 km), and each origin's trips sum to one.
A zone's pull is half its population and half its share of destination weight, where
destination weight comes from OpenStreetMap features weighted by kind (a university 10,
a mall 10, a hospital 8, a school 3, a supermarket 2, an office 1) and from metro
stations at 2 per 1,000 weekday entries, split across their exits; each feature is
credited to its nearest zone within 1.5 km. The decay of 6 km gives an average
straight-line trip of 8.0 km; the official average bus trip of 15.6 km includes
intercity buses.

### 4.4 Door-to-door journeys

The journey graph holds, for every served stop, an arrival and a departure node, and for
every route direction a chain of on-board nodes. Boarding costs half the route's headway
plus a 5-minute transfer penalty; riding to the next stop costs the hop distance at the
zone's moving speed plus 20 s; alighting and staying at a stop cost nothing; walking to
another stop within 300 m costs the straight-line distance times 1.3 at 1.25 m/s,
once between rides, never chained. A journey walks from its origin to any stop within
500 m, follows the cheapest path by Dijkstra's algorithm up to 120 minutes, and walks
from a stop within 500 m to its destination; one transfer penalty is removed at the end,
since the first boarding is not a change, and trips under 2 km may be walked entirely.
Reported are the mean door-to-door time of trips possible within 120 minutes, the shares
possible within 30, 45, 60 and 120 minutes, the share of trips without a stop within
reach at one end, and the distribution of changes. Each modelled trip is also pushed
back along its path to count a boarding on every route it uses, which gives the model's
boardings per route.

### 4.5 Checking the model against observed boardings

The model's boardings and the observed boardings are turned into shares of their own
totals over the 56 BakuBus routes present in both, and compared by Spearman's rank
correlation. The check is run four times, adding one input at a time: one 12-minute
headway for every route with trips to homes only; headways by service type; destinations
added; headways from boardings added. The last step uses the counts it is checked
against and is reported as circular.

### 4.6 The redesign search

A plan is a network plus a fractional number of buses per route; headway equals
round-trip time with layover divided by buses, never below 3 minutes, so a route that
gets shorter keeps its buses and runs more often. The objective is the average
door-to-door time over a fixed sample of trips, with a trip impossible within 120
minutes counted at 120, from 100 origins drawn by population with one point per hexagon;
scoring a plan takes under a second. The fleet never changes. A change is kept only if
it lowers the average by at least 0.005 minutes and leaves no more than 500 people
without any stop within 500 m, and no more than 3,000 across all changes, counted on the
finer seven-point population. No route is made to run less often than every 30 minutes
by losing buses, and no route gets more buses than it can use at 3 minutes.

Riders per route are counted where counts exist and otherwise estimated as the model's
boardings scaled so that, over the counted routes, model and counts agree in total; a
count always wins over the model, and a route with at least 1,000 counted weekday
boardings is never dropped. Route 180, whose connecting routes have no stops in the
data, is protected from every change. Five kinds of change are tried. A merge drops a
near-duplicate route and gives its buses to the up to three routes sharing most of its
stops. A drop removes one of the 20 routes with the fewest riders per bus, its buses
going to the routes it overlaps or across the network. A straightening replaces a detour
with the shortest path between its end stops along links some route drives today, in
the right direction, keeping the stops on that path; the 80 detours saving most time are
tried. Stop balancing removes stops closer than 250 m (then 300 m) to a neighbour on
every route that uses them, keeping terminals, hubs and any stop that is someone's only
one within reach. A shift moves 20% of the buses of the 5, 10 or 20 routes where one more
bus saves riders the least waiting, riders times headway divided by buses, to the same
number of routes where it saves the most, the marginal form of the square-root rule of
frequency setting.

The search screens each structural change alone against today's plan, applies the
improving ones in order of gain while re-checking each against the plan as it stands,
tries stop balancing, and then up to four rounds of shifts, recounting riders per route
each round. The result is scored on an independent check: 300 other origins, with a
different seed and the seven-point population, the same model that measures today's
network. Finally the share of the fleet that would give today's average trip on the
independent check is found by halving an interval six times, accurate to about one
percentage point.

### 4.7 Robustness

Three checks ask how much the result depends on the sample and the assumptions. The
redesign and today's network are scored on ten further samples of 300 origins. The
search is run again under eleven changed settings: a transfer penalty of 2 and of 8
minutes, distance decay of 4 and of 9 km, trips to homes only, 45 and 80 boardings per
trip, walks of at most 400 m, a search sample of 200 origins, another search sample of
100, and a coverage guard that lets nobody lose a stop. And coverage is measured at
300, 400, 500, 800 and 1,000 m.

## 5. Results

### 5.1 The network today

Baku's 201 routes with stops run in 402 directions over 3,456 served stops; the median
route is 17.1 km one way with 27.5 stops. The routes are indirect (Table 2). The median
route is 1.77 times the straight line between its ends, and only 20 of the 182 non-loop
routes meet the 1.3 limit of the Soviet norm. The median route is 21% longer than the
shortest path buses could take between its ends on links they already drive, and for a
rider the median route covers 1.45 times the straight-line distance between any two of
its stops at least 1 km apart. Indirect routes carry many riders: six of the 20 busiest
BakuBus routes are very indirect or loops, including the busiest, route 14, with 31,303
boardings a weekday. The least direct routes are loops: 517 at 9.3 times the straight
line, 4 at 7.8, 155 at 6.2, 44 at 4.6 and 2 at 4.1.

Table 2. Directness of the 201 routes, from the less direct direction of each.

| Shape class | Path length ÷ straight line between the ends | Routes |
|---|---|---|
| Direct | up to 1.4 | 29 |
| Indirect | 1.4 to 2 | 98 |
| Very indirect | 2 to 3 | 55 |
| Loop | over 3, or ends less than 1 km apart | 19 |

The routes overlap. Buses run 7,398 km of route over 3,824 km of distinct links, a
duplication ratio of 1.93, and up to 26 routes use one link. There are 21 trunk
corridors, 71 km in total, where eight or more routes share every link; the longest runs
12.0 km along X. R. Ulutürk street with 15.8 routes per link on average and 27 routes
using it, and the busiest, 3.5 km between the Xətai district court and Neftçilər metro
station, is used by 29 routes with up to 25 on one link. Twenty-five routes are
near-duplicates, in 72 pairs, and in 59 of the pairs the two routes belong to different
carriers: route 190 has 100% of its stops on route 160, 120A has 96% on 149 and on 205,
118B has 96% on 118A, and 173A and 173B, and 197 and 198, each have 94% on each other.

Detours are common and mostly unnecessary. There are 271 on 139 routes; together they
add 939 km to one trip in each direction of every route. For 217 of them, 719 km on 118
routes, everyone living within 400 m of the stops inside the detour also has another
route within 400 m. The longest, on route 177, covers 21.2 km between two stops 7.8 km
apart, adding 13.4 km and 27.5 minutes to every through trip for 53 people whom only
that route serves.

Stops are close together: the median gap is 420 m, 5.4% of gaps are under 200 m and
23.9% under 300 m. At 20 s and 0.05 litres per stop, stopping takes an estimated 18.8%
of running time and 20.4% of fuel.

### 5.2 Who the network reaches

Of the 3.04 million people in the study area, 55.5% live within 300 m of a served stop,
66.0% within 400 m, 73.4% within 500 m, 87.2% within 800 m and 91.5% within 1,000 m
(Figure 3). The 12.8% beyond 800 m is close to the 17% with limited bus access that the
agency's consultant reported in 2025. Door to door, on 300 origins sampled by
population, the average possible trip takes 51.8 minutes; 16.2% of trips can be made
within 30 minutes, 29.4% within 45, 42.2% within 60 and 66.3% within two hours; 34.6%
of trips have no stop within 500 m at one end or both; the average trip is 8.0 km in a
straight line. Of the possible trips, 11.4% are walked, 28.9% need no change, 43.2% one,
15.0% two and 1.5% three or more.

### 5.3 Daily service and how far the model can be trusted

The estimated headways imply 33,363 trips a day, 28,327 bus-hours, 588,994 bus-km,
226,592 diesel-equivalent litres and 605 tonnes of CO₂, and a fleet of 2,015 buses, 88%
of the 2,300 reported in service. The implied fleet landing near the reported one
suggests the headways are realistic overall, though individual routes can be far off.

BakuBus routes carried 768,253 boardings on an average weekday in September 2026 on 64
routes, 56 of which are in the map with 692,288. Route 14 carries the most, 31,303 a
weekday and 2,285 per kilometre of route; route 150E recorded only 16.5, so it probably
barely ran. The model's ranking of the 56 counted routes improves as inputs are added
(Table 3, Figure 4): a flat 12-minute headway for every route gives a Spearman
correlation of 0.41, headways by service type 0.56, destinations 0.58, and headways from
the boardings themselves 0.77, which is circular. The fair figure is 0.58. In that run
the model overrates the express and long suburban routes E1 (6.4 times its observed
share), 205 (3.4), 120E (2.6) and 72 (2.2), and gives the suburban routes 139, 141E, 189
and 163 and the express 140E under 15% of their observed shares. This is the figure to
keep in mind for everything that follows: the model ranks routes only moderately well,
and the redesign uses counts where they exist for exactly that reason.

Table 3. Spearman correlation between modelled and observed boardings on 56 BakuBus
routes as each input is added.

| Model inputs | Correlation | Fleet implied |
|---|---|---|
| One headway of 12 minutes for every route; trips to homes only | 0.41 | 2,030 |
| Headways by service type; trips to homes only | 0.56 | 1,848 |
| Plus destinations from OpenStreetMap and the metro | 0.58 | 1,848 |
| Plus headways estimated from observed boardings (circular) | 0.77 | 2,015 |

### 5.4 Stop balancing alone

Removing stops closer than 250 m to a neighbour on every route that uses them, keeping
terminals and hubs and never leaving a gap over 700 m, removes 351 stops (883 stop
visits). The median gap rises from 420 to 473 m and the share under 300 m falls from
23.9% to 14.2%; the share of people within 400 m of a stop falls by 0.15 points, from
65.96% to 65.82%; at today's headways 28 fewer buses are needed, bus-hours fall 1.5% and
fuel 1.7%; the average door-to-door trip shortens from 51.8 to 51.6 minutes and the
share of possible trips falls from 66.3% to 66.0%.

### 5.5 The redesign

With the default settings the search kept 27 changes: five merges (114B into 114A, 100
into 108B, 173A into 173B, 210 into 215, 169 into 168), three drops (164, 39 and 150E),
14 straightened detours on 12 routes, one stop-balancing pass removing 338 stops, and
four shifts moving 25, 19, 19 and 14 bus-equivalents from the 20 routes where a bus saves
riders the least waiting to the 20 where it saves the most. Routes go from 201 to 193.
No route with 1,000 or more counted boardings a weekday was dropped. On the search
sample the capped average fell by 1.35 minutes, of which the bus shifts gave 54%, stop
balancing 16%, straightening 15%, merges 11% and drops 5%.

On the independent check (Table 4), the average possible trip shortens from 51.82 to
50.86 minutes, the shares within 30, 45 and 60 minutes rise from 16.2, 29.4 and 42.2% to
16.6, 30.3 and 43.4%, and the capped average falls from 74.82 to 74.06 minutes. Route
length falls 5.8% and distinct links 3.8%; the duplication ratio goes from 1.93 to 1.90;
the median stop gap rises to 470 m and the share of gaps under 300 m falls to 14.6%. The
same buses run 3.2% more trips on shorter routes, so frequencies rise and waits shorten;
bus-kilometres rise 1.3% and fuel stays level because buses also stop less. The price is
paid in coverage and changes: about 5,000 fewer people are within 400 m of a stop, 976
have no stop within 500 m any more, and the share of trips with two or more changes
rises from 16.5% to 17.4%.

Table 4. Today's network and the redesign on the independent check (300 origins).

| Measure | Today | Redesign |
|---|---|---|
| Routes | 201 | 193 |
| Stops served | 3,456 | 3,105 |
| Route length, all directions (km) | 7,398 | 6,970 |
| Distinct links (km) | 3,824 | 3,678 |
| Median stop gap (m) | 420 | 470 |
| People within 400 m of a stop | 65.96% | 65.80% |
| Average door-to-door time, possible trips (min) | 51.82 | 50.86 |
| Average counting impossible trips as 120 min | 74.82 | 74.06 |
| Trips possible within 45 minutes | 29.4% | 30.3% |
| Trips possible within 2 hours | 66.3% | 66.4% |
| Possible trips with two or more changes | 16.5% | 17.4% |
| Trips a day | 33,363 | 34,418 |
| Bus-hours a day | 28,327 | 28,327 |
| Bus-km a day | 588,994 | 596,868 |
| Fuel a day (diesel-equivalent litres) | 226,592 | 226,708 |

The improvement can instead be taken as a smaller fleet. With 88.3% of the redesigned
network's buses, cut evenly on every route, the independent check's capped average is no
longer than today's: 1,692 bus-equivalents instead of 1,916, or 1,796 whole buses
instead of 2,015; bus-hours fall from 28,327 to 25,007 (−11.7%), bus-kilometres from
588,994 to 526,923 (−10.5%), fuel from 226,592 to 200,140 litres (−11.7%) and CO₂ from
605 to 534 tonnes a day.

### 5.6 How robust the gain is

Scored on ten different samples of 300 origins, the redesign's gain in the capped average
is 0.68 to 0.81 minutes, mean 0.77 with a standard deviation of 0.04, and positive in
every sample (Figure 5); the level itself moves by about 4 minutes between samples
(73.6 to 77.5 for today's network), so the gain should be quoted with its range and the
level not to two decimals. Under the eleven changed settings (Table 5) the gain stays
between 0.58 and 0.84 minutes and today's travel times need 87 to 90% of the buses in
every run (10 to 13% less fuel); it is smallest with shorter trips or shorter walks and
largest with a larger search sample. What the search keeps is also stable: two to four
drops, 12 to 17 straightened detours, one stop-balancing pass and four shifts in every
run, and five merges in nine of the twelve. A larger or a different search sample keeps
32 or 33 changes instead of 27 with the same gain on the independent sample, so the
sample decides the changes at the margin, not the effect.

One run matters for policy. Under a strict coverage guard, in which no change may leave
anyone without a stop within 500 m, the search keeps 24 changes and gains 0.77 minutes,
as much as the default run's 0.76. The 976 people the default run leaves without a stop
buy nothing.

Table 5. The search under other assumptions: gain on the independent check and the share
of the fleet that gives today's travel times.

| Setting | Changes | Gain (min) | Fleet for today's times |
|---|---|---|---|
| Default settings | 27 | 0.76 | 88% |
| Transfer penalty 2 minutes instead of 5 | 26 | 0.80 | 88% |
| Transfer penalty 8 minutes | 26 | 0.72 | 88% |
| Distance decay 4 km instead of 6 | 27 | 0.59 | 90% |
| Distance decay 9 km | 26 | 0.83 | 88% |
| Trips end at homes only | 25 | 0.82 | 87% |
| 45 boardings per trip instead of 60 | 25 | 0.73 | 88% |
| 80 boardings per trip | 26 | 0.81 | 88% |
| Walks of at most 400 m instead of 500 | 24 | 0.58 | 90% |
| Search sample of 200 origins | 32 | 0.84 | 87% |
| Search sample with another seed | 33 | 0.79 | 88% |
| Nobody may lose a stop | 24 | 0.77 | 88% |

### 5.7 What to check before acting

The changes are candidates for people who know the city to review, not a plan, and the
search itself flags where its evidence is thin. Route 519, a 2.1 km shuttle with three
stops and no counts, is credited by the model with 14,700 boardings a day and raised
from every 15 minutes to every 3; its riders should be counted before a bus is added.
The three dropped routes have little evidence behind them: 164 and 39 have no counts and
estimated boardings of 133 and 582 a day, and 150E recorded 16.5 boardings a weekday.
Six routes without counts (131, 197, 198, 550, 551, 554) go from every 15 to every 30
minutes on estimates alone, and two more (54 and 50) from every 10 to about every 24.
Each straightened stretch follows links that buses drive today, but turns, one-way
streets and the skipped stops, some of which serve schools and clinics, need checking on
the ground. And the merge of 210 into 215 alone leaves 495 people without a stop within
500 m, just under the limit per change; the strict guard avoids it at no cost.

## 6. Discussion

### 6.1 Against the agency's own findings

Working only from public data, the diagnosis points the same way as the consultant's:
overlapping routes, weak links between parts of the region, and a sixth to a fifth of
residents with poor access. The consultant found 17% with limited access; here 12.8%
live more than 800 m from a stop and 34% more than 400 m. The consultant's network needs
about 2,800 buses against about 2,300 in service; the fleet-neutral search finds that
today's 2,015 implied buses could be 12% fewer at today's travel times, which is not a
contradiction, since the consultant redesigns for growth and the search here only
removes waste. Where the agency's model and this one disagree, the agency's should be
trusted on anything that depends on data it has and this work does not: headways,
vehicle capacity and where riders travel.

### 6.2 Limitations

The results are not forecasts. Headways are estimated for 200 of 201 routes; the demand
model ranks routes at 0.58; the metro is not in the travel graph, so trips that would
use it look slower or impossible by bus; there is no vehicle capacity or crowding, so
busy routes look better than they are and a shift can overload them; there is one
all-day weekday average, straight-line walking times 1.3, and speeds by service type
rather than by street; counts exist for one operator only; the population grid is two
years older than the official figures; and the search is greedy over existing routes,
so it finds improvements, not the best network, and invents no routes. The gain of
about one minute per trip is small; what the robustness checks establish is its sign and
its order of magnitude, not its second decimal. The map describes the inherited network,
not the one being launched.

### 6.3 Transferability

Everything here needs only a public map with stop sequences and shapes, a population
grid and OpenStreetMap; the boardings of one operator improved the model from 0.56 to
0.58 and, more importantly, kept the search from dropping busy routes. The repairs are
detected rather than hard-coded, and every assumption is a setting with its source, so
the pipeline can be pointed at another city's map. The method's weakest link travels
with it: without origin–destination data the demand model is a gravity model, and the
checks in Section 5.6 are the minimum that should accompany any such estimate.

### 6.4 Choices that are not the model's to make

Several settings are policy choices that the model only parameterises: whether the gain
is taken as faster trips or fewer buses; how many people may lose a stop within walking
distance so that others travel faster, where the strict answer of none costs nothing
here; how much riders mind changing buses; which routes are fixed by contracts or school
service; and whether routes of different carriers can be merged at all, which matters
because 59 of the 72 near-duplicate pairs involve two carriers and the gross-cost
contracts the agency plans would make it easier.

## 7. Conclusions

From public data alone, Baku's bus routes can be shown to be indirect, heavily
duplicated and full of detours that serve nobody uniquely, with a third of residents
beyond a 400 m walk of a stop. A travel model built from the same data ranks routes
against observed boardings only moderately well, and says so. Within that limit, a
cautious redesign that keeps every bus, merges near-duplicates, straightens detours,
thins stops and moves buses to where they save the most waiting delivers today's travel
times with about 12% fewer buses, or trips about a minute shorter, and the gain survives
other samples and other assumptions. The strict version that strands nobody gives up
none of it. The pipeline, data and results are released so that the figures can be
regenerated, the assumptions changed, and the method applied to the next city whose
agency publishes a map and nothing else.

## Declarations

Data and code availability: every input, setting, script and result is in the
repository ismatsamadov/route_efficiency, release v1.0.0, archived at
https://doi.org/10.5281/zenodo.23602094 (all versions: 10.5281/zenodo.23602093). The
code is under the MIT License; OpenStreetMap extracts are © OpenStreetMap contributors
under the Open Database License (openstreetmap.org/copyright); Kontur Population is
CC BY; the opendata.az datasets are CC BY (Bakı Metropoliteni); the AYNA map data has
no published terms and is redistributed as a research snapshot with attribution.

Ethics: this study analysed only publicly available, aggregated, non-personal data (bus
routes and stops, a population grid, daily boardings per route). No human participants
were involved and no ethics approval was required.

Competing interests: none. Funding: none.

Author contributions: single author.

Declaration of generative AI use: [required by the target journal; state the tools used
in preparing the manuscript and that the author reviewed and edited the content and
takes responsibility for it].

## Figures

Figure 1. Baku's bus network with each route direction coloured by its shape class
(direct, indirect, very indirect, loop). Source: output/routes.csv and
output/redesign/network.geojson.

Figure 2. Overlap: the 21 trunk corridors where eight or more routes share every link,
line width by routes per link. Source: output/corridors.csv.

Figure 3. Share of residents within 300, 400, 500, 800 and 1,000 m of a served stop.
Source: output/robustness/coverage_radius.csv.

Figure 4. The demand model's Spearman correlation with observed boardings as each input
is added. Source: output/robustness/fit_ladder.csv.

Figure 5. Gain of the redesign on ten trip samples (left) and under eleven alternative
settings (right), with the default run marked. Source: output/robustness/redesign_seeds.csv
and redesign_settings.csv.

Figure 6. The redesign: kept route directions in blue, straightened ones in green,
dropped or merged ones in red. Source: output/redesign/network.geojson.

All maps carry: © OpenStreetMap contributors, ODbL, openstreetmap.org/copyright.

## References

Allen, H. (2013). Bus reform in Seoul, Republic of Korea. Case study prepared for Global Report on Human Settlements 2013. UN-Habitat. https://unhabitat.org/sites/default/files/2013/06/GRHS.2013.Case_.Study_.Seoul_.Korea_.pdf

APA (2025, September). Azerbaijan to implement gross contract system to ensure sustainable public transport financing. https://en.apa.az/infrastructure/azerbaijan-to-implement-gross-contract-system-to-ensure-sustainable-public-transport-financing-478431

Abkowitz, M. D., & Engelstein, I. (1982). Temporal and spatial dimensions of running time in transit systems. Transportation Research Record, 877, 64–67.

Badia, H., Argote-Cabanero, J., & Daganzo, C. F. (2016). How network structure can boost and shape the demand for bus transit. Institute of Transportation Studies, University of California, Berkeley. https://its.berkeley.edu/node/4590

Berlingerio, M., Calabrese, F., Di Lorenzo, G., Nair, R., Pinelli, F., & Sbodio, M. L. (2013). AllAboard: A system for exploring urban mobility and optimizing public transport using cellphone data. In Data for Development (D4D) Challenge, NetMob 2013. https://perso.uclouvain.be/vincent.blondel/netmob/2013/D4D-book.pdf

BusConnects (2025). BusConnects Dublin progress report, March 2025. National Transport Authority. https://busconnects.ie/wp-content/uploads/2025/04/BusConnects-Dublin-Progress-Report-March-2025-WEB.pdf

Devunuri, S., Lehe, L. J., Qiam, S., Pandey, A., & Monzer, D. (2023). Bus stop spacing statistics: Theory and evidence. arXiv:2208.04394. https://arxiv.org/abs/2208.04394

Durán-Micco, J., & Vansteenwegen, P. (2022). A survey on the transit network design and frequency setting problem. Public Transport, 14, 155–190.

EBRD (2024). Tbilisi gets greener and more inclusive. https://www.ebrd.com/news/2024/tbilisi-gets-greener-and-more-inclusive.html

El-Geneidy, A. M., Strathman, J. G., Kimpel, T. J., & Crout, D. T. (2006). Effects of bus stop consolidation on passenger activity and transit operations. Transportation Research Record, 1971, 32–41.

El-Geneidy, A., Grimsrud, M., Wasfi, R., Tétreault, P., & Surprenant-Legault, J. (2014). New evidence on walking distances to transit stops: Identifying redundancies and gaps using variable service areas. Transportation, 41(1), 193–210. https://doi.org/10.1007/s11116-013-9508-z

Farahani, R. Z., Miandoabchi, E., Szeto, W. Y., & Rashidi, H. (2013). A review of urban transportation network design problems. European Journal of Operational Research, 229(2), 281–302. https://doi.org/10.1016/j.ejor.2013.01.001

Holliday, A., El-Geneidy, A., & Dudek, G. (2025). A neural-evolutionary algorithm for autonomous transit network design. Transportmetrica B: Transport Dynamics, 13(1). https://doi.org/10.1080/21680566.2025.2561863

Ibarra-Rojas, O. J., Delgado, F., Giesen, R., & Muñoz, J. C. (2015). Planning, operation, and control of bus transport systems: A literature review. Transportation Research Part B, 77, 38–75. https://doi.org/10.1016/j.trb.2015.03.002

IPCC (2006). 2006 IPCC guidelines for national greenhouse gas inventories, Volume 2, Chapter 1. https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_1_Ch1_Introduction.pdf

ITU (2018). The case of Moscow. United for Smart Sustainable Cities. https://www.itu.int/en/publications/Documents/tsb/2018-U4SSC-Case-of-Moscow/files/basic-html/page40.html

Kepaptsoglou, K., & Karlaftis, M. (2009). Transit route network design problem: Review. Journal of Transportation Engineering, 135(8), 491–505. https://doi.org/10.1061/(ASCE)0733-947X(2009)135:8(491)

King County Metro (2021). King County Metro service guidelines, November 17, 2021. https://cdn.kingcounty.gov/-/media/king-county/depts/metro/documents/about/policies/equity/metro-service-guidelines-111721.pdf

Kun.uz (2026, February 26). Tashkent bus revenue hits UZS 644 billion as passenger numbers double. https://kun.uz/en/48790711

Lynn, J. (2017). Barcelona's bus network: Better access if you change buses. Human Transit. https://humantransit.org/2017/04/guest-post-barcelonas-bus-network-better-access-if-you-change-buses.html

Mandl, C. E. (1980). Evaluation and optimization of urban public transportation networks. European Journal of Operational Research, 5(6), 396–404. https://doi.org/10.1016/0377-2217(80)90126-5

Miami-Dade Transit (2005). Service standards presentation to the Regional Transportation Committee, November 10, 2005. https://www.miamidade.gov/citt/library/strategic-financial-studies/2013/cost-other-studies/analysis-activity/2006-1ServiceStandardPresentation%20%5BCompatibility%20Mode%5D.pdf

Ministry of Digital Development and Transport of Azerbaijan (2023, December 18). Presentation of Mobility Transformation Program in Azerbaijan took place. https://mincom.gov.az/en/media-en/news/presentation-of-mobility-transformation-program-in-azerbaijan-took-place

Ministry of Digital Development and Transport of Azerbaijan (2026). Roundtable on the 2025 State Program for the improvement of transport infrastructure in Baku and surrounding areas. https://mincom.gov.az/en/media-en/news/roundtable-on-the-2025-state-program-for-the-improvement-of-transport-infrastructure-in-baku-and-surrounding-areas

Mumford, C. L. (2013). New heuristic and evolutionary operators for the multi-objective urban transit routing problem. In 2013 IEEE Congress on Evolutionary Computation (pp. 939–946). https://doi.org/10.1109/CEC.2013.6557668

Munizaga, M. A., & Palma, C. (2012). Estimation of a disaggregate multimodal public transport origin–destination matrix from passive smartcard data from Santiago, Chile. Transportation Research Part C, 24, 9–18.

Nylund, N.-O., & Koponen, K. (2012). Fuel and technology alternatives for buses: Overall energy efficiency and emission performance. VTT Technology 46. https://sarjaweb.vtt.fi/pdf/technology/2012/T46.pdf

Pappalardo, L., Simini, F., Barlacchi, G., & Pellungrini, R. (2022). scikit-mobility: A Python library for the analysis, generation, and risk assessment of mobility data. Journal of Statistical Software, 103(4). https://doi.org/10.18637/jss.v103.i04

Report.az (2024, November). Minister: Azerbaijan plans to fully electrify its bus fleet by 2030. https://report.az/en/amp/cop29/minister-azerbaijan-plans-to-fully-electrify-its-bus-fleet-by-2030

RSFSR Ministry of Motor Transport (1981). Order No. 200 of 31 December 1981 on the rules for organising passenger transport by road (repealed). https://zakonbase.ru/content/part/76594

Schmitt, A. (2016, August 17). A year after Houston's bus network redesign, ridership is up. Streetsblog. https://sf.streetsblog.org/2016/08/17/a-year-after-houstons-bus-network-redesign-ridership-is-up

Simini, F., González, M. C., Maritan, A., & Barabási, A.-L. (2012). A universal model for mobility and migration patterns. Nature, 484, 96–100.

Sivakov, V. V., Kamynin, V. V., & Tikhomirov, P. V. (2022). Improving transport services in Bryansk. World of Transport and Transportation, 20(4), 247–252. https://doi.org/10.30932/1992-3252-2022-20-4-9

Walker, J. (2014, May). Houston: A transit network reimagined. Human Transit. https://humantransit.org/2014/05/houston-a-transit-network-reimagined.html

Walker, J. (2015, February). Houston's reimagined network: Don't let us make it look easy. Human Transit. https://humantransit.org/2015/02/houstons-reimagined-network-dont-let-us-make-it-look-easy.html
