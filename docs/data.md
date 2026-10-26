# Data

Every file the tools read is committed under `data/`, including everything in
`data/external/`; `.gitignore` excludes only Python caches, virtual environments, the
macOS `.DS_Store` files that Finder creates and the `emails/` folder of letter drafts. [data/SOURCES.md](../data/SOURCES.md)
lists each file with its source and licence; this page explains what each one contains,
how the code uses it, what is wrong with it and what is still missing.

## Overview

| Data | File(s) | Read by | Used for |
|---|---|---|---|
| Bus network (AYNA) | `data/ayna.db` | `busnet/model.py` | Routes, stops, stop order, route shapes |
| Real headways | `data/headways.csv` | `busnet/service.py` | Headways that override estimates |
| Population | `data/external/kontur/*.gpkg` | `busnet/population.py` | Coverage, trip origins and destinations |
| BakuBus boardings | `data/external/opendata/bakubus_passenger-2026.csv` | `busnet/ridership.py` | Headway estimates, ridership columns, model check |
| Metro entries and exits | `data/external/opendata/metro_passengers-2026.csv`, `metro_exits.csv` | `busnet/destinations.py` | Trip destinations |
| Metro network | `data/metro/`, built by `data/build_metro.py` from the metro's own API, OpenStreetMap and Wikidata | not read yet | Stations, train services, running times and departures, for putting the metro into the travel graph |
| Metro intervals | `data/metro_headways.csv` | not read yet | Train intervals the operator has published, with sources |
| OpenStreetMap destinations | `data/external/osm/osm_{education,health,shopping,offices,transport}.json` | `busnet/destinations.py` | Trip destinations |
| OpenStreetMap streets and paths | `data/external/osm/osm_walk_network.json.gz` | `busnet/walking.py`, from `robustness.py` | Walking distances along streets, as a check on the straight-line coverage |
| Benchmark networks (Mandl, Mumford0–3) | `data/external/utrp/CEC2013Supp.zip` | `busnet/utrp.py`, from `benchmark.py` | Testing the redesign's search on networks with published answers ([benchmark.md](benchmark.md)) |
| Reference only | AYNA route lines (`ayna_buslines.kmz`), bus stations, payment types, metro 2025, OSM route tags, statistics tables, district population | not read | Cross-checks and calibration targets |

## The AYNA bus network snapshot (`data/ayna.db`)

A SQLite database built from AYNA's public map API (`map-api.ayna.gov.az`, an
unauthenticated OpenAPI service) by `data/ayna_scraper.py` on 23 October 2026. An
earlier copy of the same data, scraped on 6 May 2026 and kept in
github.com/samirmehd1yev/best_route_finding, is identical row for row (every route,
stop, coordinate, stop sequence and shape point), so the API did not change between
the two dates. The API returns an error for one of its 209 route ids (96, route 144),
in both scrapes. The same snapshot is published on Kaggle with its tables as CSV
(https://doi.org/10.34740/KAGGLE/DSV/21173689).

**Licence.** None is published. The data is AYNA's; neither AYNA's website nor the API
states terms of use. I keep the database here as a research snapshot with attribution
to AYNA; this repository's licence does not extend to it. AYNA also publishes its route
lines (KMZ) and bus stations on opendata.az under CC0 (`data/external/opendata/`), a
cleaner source for route geometry if a future snapshot can be built from them.

### When the data is from

Every result describes the network as AYNA's map API publishes it, and the API returned
exactly the same data on 23 October 2026 as on 6 May 2026, although AYNA's new network
began launching in January 2026 ([research.md](research.md#4-bakus-own-programme)). The
BakuBus counts I use for ridership are from September 2026 and include eight routes that
the map does not carry, so the map lags the network on the street: 500 is counted all
year, 149E from 22 June and 195E from 28 July, and M2 to M6 from 14 and 15 August, when
AYNA started express bus routes "in 6 directions" for the works that closed the metro
between 28 May and Nizami ([Metro](#metro)). September is therefore a month of metro
works. The ranking of routes
by boardings hardly moves (the weekday averages of May and September 2026 rank the 55
routes counted in both months at a Spearman correlation of 0.976), but some routes
gained far more than the rest: 14 by 70%, 7A and 17 by 65% and 2 by 36%, against 13%
for the 55 together. Routes 14 and 2 pass within 200 m of both Nizami and 28 May, and
17 joins Elmlər Akademiyası to Gənclik, so they carry riders around the closed section.
When the API changes, a new scrape and a rerun of the three scripts
([roadmap.md](roadmap.md#when-new-data-arrives)) will show which findings survive; the
repairs are detected from the data, so they adapt to it.

| Table | Rows | Contents |
|---|---|---|
| `buses` | 208 | One row per route: number, carrier, end points, `route_length_km`, `duration_min`, fare (`tariff_qepik`, `tariff_azn`), payment type (`Kart` card or `Nəğd` cash), region (`Bakı` or `Sumqayıt`), working zone, card payment start date, stop counts per direction |
| `stops` | 3,841 | Stop id, code, name, latitude, longitude, hub flag, number of routes |
| `bus_stops` | 11,786 | Ordered stops for each route and direction (1 = outbound, 2 = return) |
| `routes` | 398 | One shape per route direction, as GeoJSON, with a destination label |
| `route_points` | 109,147 | The same shapes, one row per vertex |

Working zones: `Şəhərdaxili` urban (69 routes), `Şəhərətrafı` suburban (101), `Qəsəbələrarası`
between settlements (20), `Qəsəbədaxili` within a settlement (7), `Şəhərdaxili (ekspres)`
urban express (6), `Şəhərətrafı (ekspres)` suburban express (3), `Şəhərlərarası` intercity (2).

### Defects repaired automatically

`busnet/model.py` detects and fixes these when it loads the database; nothing in the
database itself is changed. Each repair is listed in `output/repairs.txt` (23 lines).
The detection rules are in [methodology.md](methodology.md#1-loading-and-repairing-the-network).

| Defect | Where | Repair |
|---|---|---|
| Stop list repeated twice back to back | 120A, both directions | Keep one copy |
| Shapes filed under the wrong direction | 4, 45, 120, 509, 515, 519, 522, 523, 525, 531, 533, 535, 553 | Swap the two shapes |
| Shape stored backwards | 121E both directions, 553 direction 1 | Reverse it |
| Latitude and longitude swapped | 521 direction 2 | Swap them back |
| Latitude equal to longitude on every point | 531 (stored direction 1) | Drop it; draw that direction as straight lines between stops |
| Shape scrambled, with straight jumps of 9 to 20 km | 550, 555, 557 direction 1 | Drop it; straight lines between stops |
| No shape at all | 502, 511 | Straight lines between stops |

After the repairs 394 of 402 route directions use real shapes. Three directions still have
one stop slightly out of order along their shape (35, 536 and 537, direction 2). The median
stop sits 7.2 m from its route line, and 90% sit within 13.7 m.

### Known issues not repaired

| Issue | Effect | How the code handles it |
|---|---|---|
| 7 routes have no stops or shapes: 110, 137, 200, 446, 150A, 539, 556 | They cannot be measured or redesigned | Left out; 201 routes have stops |
| `duration_min` is `floor(route_length_km / 0.6)` on all 208 routes | Not a real time | Never used; times come from the travel model |
| `route_length_km` is the round-trip length (median 1.99 times the one-way shape) | Misleading if read as one-way | Never used; lengths come from the shapes |
| 15 stops lie more than 100 m from their route's line in today's GTFS feed, by MobilityData's validator: nine are a loop through Masazır and Yeni Bakı that route 525's line in direction 1 does not draw (0.2 to 1.1 km off), and stop 3841 on route 537 is 1.1 km off. AYNA's line for route 44 direction 2 also ends 1.7 km before its last stop | Slightly wrong distances near them | The model counts each hop between stops as at least the straight line between them; the GTFS feeds carry lines that stop short on to their end stops; the list is in `output/gtfs_validation/stops_far_from_shape.csv` |
| 385 stops have coordinates but no name and no route | None | Ignored |
| 218 stop names mix Cyrillic letters (ә, Ә, Х) into Azerbaijani Latin; 530 names are shared by several stops, 36 of them more than 1 km apart | A text search for a stop would miss or confuse stops | The code always uses stop ids; names are only displayed |
| Carriers appear under variant spellings (SAHİL and Sahil MMC, XAN and Xan Nəqliyyat MMC, General-Auto-Company with or without spaces) | Carrier totals split | Extra spaces are removed; spelling variants are not merged |
| `card_payment_since` is local midnight stored as UTC | Read naively, the date is one day early | Not used |
| Route 180 (Pirallahı) is cut off: its connecting routes 150A and 446 have no stops in the data | Trips to and from Pirallahı look impossible, so the model sees few riders on 180 | The redesign leaves 180 as it is by default (`redesign_protected_routes`) |

## Population

`data/external/kontur/kontur_population_AZ_20231101.gpkg`: Kontur Population, release
2023-11-01, CC BY (HDX records the licence without a version). A GeoPackage (SQLite)
with one row per H3 hexagon of resolution 8
(about 0.74 km² each); 34,609 hexagons and 10.48 million people for Azerbaijan.

`busnet/population.py` keeps the hexagons whose centre lies inside the box around the
served stops plus 2 km: 2,707 hexagons with 3,043,187 people. For coverage and travel
times each hexagon is split into seven points that share its population (its centre and
six points around it, the way H3 divides a cell), so coverage is not judged from the
centre alone. The points inside the box number 18,952 and carry 3,043,184 people, the
figure every result uses; the small difference is a few points of hexagons at the edge
of the box. The official figures for 1 January 2026 (Baku 2,356,200; Sumqayıt 428,200;
Absheron district 435,200; table in `data/external/stat/`) total 3.22 million, consistent
with the grid.

## Ridership

`data/external/opendata/bakubus_passenger-2026.csv`: daily boardings per BakuBus route,
1 January to 30 September 2026, published by Bakı Metropoliteni on opendata.az (CC BY).
Columns: date, route number, daily boardings.

- 65 routes are in the file; 64 have weekday data in September 2026 (route 206 has none).
- The tools use the weekday average of the latest month: 768,253 boardings a day in
  September 2026.
- 56 of those routes are in the AYNA snapshot with stops (692,288 boardings a day). Eight
  routes in the file are not in the snapshot: 500, 149E, 195E, and M2 to M6, express
  buses AYNA has run for the metro works since mid-August 2026 (65,618 boardings a
  weekday between them in September).
  One counted route, 49, is listed under another carrier (Azlənd Plaza MMC) in the AYNA
  data, which is why the snapshot shows 55 BakuBus routes but 56 routes have counts.
- Only BakuBus routes are covered; the other carriers' routes have no observed boardings.

## Metro

The model uses the metro only as a place trips go to, from two files Bakı Metropoliteni
publishes on opendata.az (CC BY):

- `metro_passengers-2026.csv`: daily entries per station, January to September 2026
  (`metro_passengers-2025.csv` has all of 2025). The weekday average of the latest month
  is used.
- `metro_exits.csv`: 98 exits of 27 stations with coordinates (stored as integers times
  one million). Station names differ between the two files ("Koroghlu" and "Koroglu",
  "8 Noyabr" and "8 Novabr", "Khatai" and "Shah Ismail Khatai"); `busnet/destinations.py`
  matches them exactly, by containment or by close spelling, and all 27 match.
- Each station's entries are split evenly across its exits and act as trip destinations.

To put the metro into the travel graph I collected the network itself, the way AYNA's
map API gives the buses. The metro has its own API: behind metro.gov.az is an open JSON
service (`app-api.metro.gov.az`) that the operator's website and journey planner use.
`data/metro_scraper.py` saves its answers to `data/external/metro_api/`: the stations,
the train services on each line, the service notices, the two departure lists it
publishes, the operator's answers to frequent questions, and its journey planner timed
along every service in both directions. I scraped it on 25 October 2026; the scraper
only reads, and calls the planner the way the public site does. `data/build_metro.py` joins those
answers with OpenStreetMap (track geometry and entrances), Wikidata (opening dates) and
the opendata.az files into the tables in `data/metro/`, and `tests/test_metro.py`
checks that it regenerates them byte for byte.

The network has 27 stations on three lines and 40.7 km of line, and carried 226.8
million passengers in 2025 (State Statistical Committee, in
`stat_urban_electric_transport.csv`, which also counts 376 cars and 612 thousand train
runs made to timetable; `stat_avg_trip_distance.csv` gives an average metro trip of 11.8
km).
Since 15 August 2026 it has not run as it used to. The red and green lines are being
separated, and trains no longer run between 28 May and Nizami; until then green trains
ran from Dərnəgül through 28 May onto the red line's track to Həzi Aslanov. On 25
October 2026 the operator ran five services:

| Line | Service | Interval (`data/metro_headways.csv`) | End to end in the planner, there and back |
|---|---|---|---|
| Red | İçərişəhər – Həzi Aslanov | 2 min at peak hours, 2.5 otherwise | 31.5 and 35.0 min, with a change at Əhmədli to a shuttle while the turnback siding at Həzi Aslanov is repaired |
| Red | Nəriman Nərimanov – Bakmil | irregular, 3 to 51 min apart; every departure is published | 4.5 and 5.0 min |
| Green | Dərnəgül – Nizami, then express bus M1 or M2 to 28 May | 3.5 min | 20.0 and 19.0 min to and from Nizami, and 3 min by bus |
| Green | Cəfər Cabbarlı – Şah İsmayıl Xətai | 8 min | 3.0 and 6.5 min |
| Purple | Xocəsən – 8 Noyabr | 5 min Avtovağzal – 8 Noyabr, 10 min Xocəsən – Avtovağzal (autumn and winter timetable) | 12.5 and 19.0 min, the second with a 6-minute wait at Avtovağzal |

On the track distances from OpenStreetMap, the planner's times give an average speed,
stops included, of 36 to 38 km/h on the red line, 34 to 36 on the green and 27 to 28 on
the purple. A
trip costs 0.60 AZN, whatever the means of payment (the operator's answers to frequent
questions).

| File | Contents |
|---|---|
| `data/metro/stations.csv` | The 27 stations: lines, coordinates (OpenStreetMap), opening date (Wikidata, and OpenStreetMap's), exits (operator) and entrances (OpenStreetMap), the station's name in each source (English, exits file, 2025 and 2026 counts, API), its OpenStreetMap node and Wikidata item |
| `data/metro/route_stops.csv` | OpenStreetMap's 12 route variants, stops in order, with the distance along the track from the previous stop |
| `data/metro/routes.geojson` | The track of each route variant |
| `data/metro/run_times.csv` | Each service end to end both ways as the operator's planner times it: arrival at every station, seconds and track kilometres from the previous one, and whether that step is a train, a bus, a wait or the start |
| `data/metro/departures.csv` | The departure lists the operator publishes: Xocəsən on weekdays and the Bakmil shuttle both ways, 414 departures |
| `data/metro_headways.csv` | Every interval the operator has published, with its source and date; written by hand, like `data/headways.csv` |
| `data/external/metro_api/` | The API's answers as downloaded |
| `data/external/osm/osm_metro_routes.json`, `osm_metro_stations.json` | OpenStreetMap's metro routes, stations and entrances, as of 24 October 2026 |
| `data/external/wikidata/metro_stations.json` | Wikidata's items for the stations on the three lines, with opening dates and neighbouring stations |

A few things to know before using them. The sources spell the stations differently, so
`stations.csv` keeps every spelling and a join never has to guess. The Azerbaijani
column of the exits file turned "28 May" into the date 28.05.2026. The API has one
station, Memar Əcəmi, for the two that the counts and OpenStreetMap keep apart (Memar
Əcəmi on the green line, Memar Əcəmi-2 on the purple); the builder tells them apart by
the line of the service. OpenStreetMap tags the purple-line one with the green station's
Wikidata item, and the builder takes the right item by name. OpenStreetMap already ends
the green line at Nizami, though its track runs on 1.8 km to 28 May, and still has an
İçərişəhər – Bakmil variant where the operator runs a shuttle from Nəriman Nərimanov; its
distances are right either way, but the services come from the operator. The planner
answers for the next trains whatever time it is asked for, so at night it times the
first morning trains; the running times should not depend on that, but its waits do.
Its 6.5 minutes from Şah İsmayıl Xətai to Cəfər Cabbarlı, against 3.0 the other way over
the same 2.2 km, looks like an error in the planner; I keep what it says. Wikidata and
OpenStreetMap disagree on two opening dates (Neftçilər 1970 or 1972, Bakmil March or
December 1979), and the table keeps both.

Not published anywhere I looked: a full timetable beyond the two departure lists,
weekend and evening intervals for the red and green lines, exit counts (only entries),
flows between stations, and train positions. Nor is there a GTFS feed for Baku: the
Mobility Database catalogue, 3,613 feeds on 25 October 2026, has none for Azerbaijan.

## OpenStreetMap destinations

Queried through the Overpass API for the box 39.9 to 40.7 N, 49.3 to 50.45 E on
23 October 2026. Data © OpenStreetMap contributors, Open Database Licence. Each file
records the date of the OpenStreetMap data it holds (`osm3s.timestamp_osm_base`): 23
October 2026 for all of them except `osm_health.json`, which a mirror server answered
with data as of 15 July 2026. `fetch_external.py` now prints that date for every query,
since a lagging mirror is otherwise easy to miss.

| File | Features | Kinds |
|---|---|---|
| `osm_education.json` | 1,402 | schools 723, kindergartens 461, colleges 132, universities 86 |
| `osm_health.json` | 855 | hospitals 531, clinics 324 |
| `osm_shopping.json` | 1,565 | supermarkets 1,330, department stores 85, malls 80, marketplaces 70 |
| `osm_offices.json` | 1,708 | offices 1,076, town halls 423, courthouses 52, and some shops tagged as offices |
| `osm_transport.json` | 98 | railway stations 70, bus stations 28 |

Each feature weighs according to `destination_weights` in `busnet.toml`; kinds not listed
there (such as shops tagged as offices) weigh nothing. With the 98 metro exits this gives
5,569 destination points.

## OpenStreetMap streets and paths (`data/external/osm/osm_walk_network.json.gz`)

Every way tagged `highway` in the study area (39.92 to 40.66 N, 49.37 to 50.39 E, the
served stops plus 2 km) with its tags and its nodes: 99,185 ways and 570,706 nodes,
9.3 MB gzipped, in the shape of an Overpass answer. The Overpass servers refuse a query
of this size whenever they are busy, so `fetch_external.py` cuts it out of Geofabrik's
daily extract of Azerbaijan (`asia/azerbaijan-latest.osm.pbf`, 46.6 MB) with
`data/osm_pbf.py`, a reader of the PBF format in the standard library; the extract
itself is not kept. The committed file holds OpenStreetMap data of 24 October 2026,
20:20 UTC. Data © OpenStreetMap contributors, Open Database Licence.

`busnet/walking.py` keeps the 97,628 ways a pedestrian may use (it drops motorways and
their links, busways, raceways, platforms, cycleways without a `foot` permission, ways
planned, under construction or gone, and ways tagged `foot=no`, `service=private`, or
`access=no` or `access=private` without `foot`), which gives a graph of 562,117 nodes
and 602,943 segments; 98.4% of the nodes are in one connected piece. Every served stop
is within 116 m of it (median 7 m), and the population points within 15 m (median);
27,000 people, 0.9%, sit more than 300 m from any mapped way. The check that uses it is
in [results.md](results.md#who-the-network-reaches); the method in
[methodology.md](methodology.md#5-population-and-coverage). Footpaths are patchy in
OpenStreetMap's Baku, so a walk along the mapped network is an upper bound where a
shortcut is unmapped.

## Benchmark networks (`data/external/utrp/`)

`CEC2013Supp.zip` (449 KB, SHA-256 `b483d39e…5ca2`) is the supplement to Mumford's
(2013) paper: Mandl's network and Mumford0 to Mumford3 as three text files each (node
coordinates, link times in minutes with `Inf` where there is no link, and trips between
every pair of nodes), the route sets her algorithm found best for passengers and for the
operator (`Results/MainResults/Best Route Sets.docx`, as Matlab lines), Table IV of her
paper with their scores (`Results/MainResults/README.docx`), the Pareto fronts of her 20
runs, and her paper's supplementary text. She published it on her Cardiff University
page, which now opens only in a browser, so `fetch_external.py --only utrp` reads the
copy that the Internet Archive's Wayback Machine took on 16 December 2025. The code
reads the files inside the zip; nothing is unpacked.

| Network | Nodes | Links | Trips | Routes | Nodes on a route |
|---|---|---|---|---|---|
| Mandl | 15 | 21 | 15,570 | 6 | 2–8 |
| Mumford0 | 30 | 90 | 342,160 | 12 | 2–15 |
| Mumford1 | 70 | 210 | 1,926,170 | 15 | 10–30 |
| Mumford2 | 110 | 385 | 4,847,900 | 56 | 10–22 |
| Mumford3 | 127 | 425 | 6,394,950 | 60 | 12–25 |

Links and trips are counted from the files: every link time and every demand matrix is
symmetric, and link times are whole minutes from 1 to 11. The numbers of routes and their
bounds are Table II of Mumford (2013), repeated in Table 1 of John, Mumford and Lewis
(2014); they are not in the files, so `busnet/utrp.py` holds them.

## Real headways (`data/headways.csv`)

Columns `route`, `headway_min` and an optional `source`. A route listed here uses this
headway instead of any estimate. Today it holds one row: H1 (Airport Express) every
20 minutes, from an airport.az press release of August 2024. Add rows as real data arrives.

## Searched for and not found

No public source gives route headways or timetables, vehicle GPS positions, ticket
validations by stop, or origin-destination data. I checked the AYNA map API (it returns
only routes, stops and shapes), the 69 transport datasets on opendata.az, OpenStreetMap
(249 bus routes; only M5 carries an interval tag), the BakuBus and AYNA websites, and
news reports. The settings in `busnet.toml` stand in for them, and since such data
cannot be obtained from AYNA, they will stay estimates. The metro is better served: its
operator publishes intervals, running times through its journey planner and two
departure lists ([Metro](#metro)), though no full timetable and no GTFS feed.

## Refreshing

`python3 data/fetch_external.py --refresh` downloads every external file again from the
URLs in the script. OpenStreetMap and the opendata.az files change over time, so results
change after a refresh; commit the new data and the regenerated `output/` together.
`python3 data/metro_scraper.py` asks the metro's API again and `python3
data/build_metro.py` rebuilds `data/metro/` from whatever is in `data/external/`; nothing
reads `data/metro/` yet, so the results do not change. The benchmark supplement
(`--only utrp`) comes from a fixed archived copy and should not change.
