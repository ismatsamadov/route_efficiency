# Data

Every file the tools read is committed under `data/`, including everything in
`data/external/`; `.gitignore` excludes only Python caches, virtual environments and the
macOS `.DS_Store` files that Finder creates. [data/SOURCES.md](../data/SOURCES.md)
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
| OpenStreetMap destinations | `data/external/osm/osm_{education,health,shopping,offices,transport}.json` | `busnet/destinations.py` | Trip destinations |
| Reference only | AYNA route lines (`ayna_buslines.kmz`), bus stations, payment types, metro 2025, OSM route tags, statistics tables, district population | not read | Cross-checks and calibration targets |

## The AYNA bus network snapshot (`data/ayna.db`)

A SQLite database built from AYNA's public map API (`map-api.ayna.gov.az`, an
unauthenticated OpenAPI service), taken from the `data/ayna.sqlite` snapshot in
github.com/samirmehd1yev/best_route_finding (added in commit `8010c00` on 6 May 2026,
coordinates repaired in commit `b8c51d5` on 11 October 2026). Its `meta` table records:
scraped 6 May 2026, coordinates repaired 11 October 2026, database built 23 October 2026.
`data/ayna_scraper.py` is the script that builds this kind of database from the API; the
committed database was built by the snapshot's own pipeline (it has a `meta` table the
script does not write).

**Licence.** None is published. The data is AYNA's; neither AYNA's website nor the API
states terms of use, and the snapshot repository has no licence file (the "ISC" in its
README, in its `package.json` and in the `meta` table's source field is that repository's
code licence, not a data licence). The database is kept here as a research snapshot
with attribution to AYNA; this repository's licence does not extend to it. For
publication, cite AYNA as the source and the snapshot repository at the commits above,
or take a fresh snapshot with `data/ayna_scraper.py` so that the provenance is your own.
AYNA also publishes its route lines (KMZ) and bus stations on opendata.az under CC0
(`data/external/opendata/`), a cleaner source for route geometry if a future snapshot
can be built from them.

### When the data is from

Every result describes the network as it was on 6 May 2026. AYNA's new network began
launching in January 2026 ([research.md](research.md#4-bakus-own-programme)), and the
BakuBus counts used for ridership are from September 2026, so the two describe the
network some months apart: eight routes in the counts (M2, M3, M4, M5, M6, 500, 149E,
195E) do not exist in the snapshot. Before building on the results, take a new snapshot
and rerun the tools ([roadmap.md](roadmap.md#updating-the-work-when-data-arrives)); the
repairs are detected from the data, so they adapt to it.

| Table | Rows | Contents |
|---|---|---|
| `buses` | 208 | One row per route: number, carrier, end points, `route_length_km`, `duration_min`, fare (`tariff_qepik`, `tariff_azn`), payment type (`Kart` card or `Nəğd` cash), region (`Bakı` or `Sumqayıt`), working zone, card payment start date, stop counts per direction |
| `stops` | 3,841 | Stop id, code, name, latitude, longitude, hub flag, number of routes |
| `bus_stops` | 11,786 | Ordered stops for each route and direction (1 = outbound, 2 = return) |
| `routes` | 398 | One shape per route direction, as GeoJSON, with a destination label |
| `route_points` | 109,147 | The same shapes, one row per vertex |
| `meta` | 4 | Source and dates |

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
| 13 stops lie more than 150 m from a route that serves them (the last stops of route 44 direction 2 are 0.6 to 1.7 km off) | Slightly wrong distances near them | None yet |
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
  newer routes in the file are not in the snapshot: M2, M3, M4, M5, M6, 500, 149E, 195E.
  One counted route, 49, is listed under another carrier (Azlənd Plaza MMC) in the AYNA
  data, which is why the snapshot shows 55 BakuBus routes but 56 routes have counts.
- Only BakuBus routes are covered; the other carriers' routes have no observed boardings.

## Metro

From Bakı Metropoliteni on opendata.az (CC BY):

- `metro_passengers-2026.csv`: daily entries per station, January to September 2026. The
  weekday average of the latest month is used.
- `metro_exits.csv`: 98 exits of 27 stations with coordinates (stored as integers times
  one million). Station names differ between the two files ("Koroghlu" and "Koroglu",
  "8 Noyabr" and "8 Novabr", "Khatai" and "Shah Ismail Khatai"); `busnet/destinations.py`
  matches them exactly, by containment or by close spelling, and all 27 match.
- Each station's entries are split evenly across its exits and act as trip destinations.

## OpenStreetMap destinations

Queried through the Overpass API for the box 39.9 to 40.7 N, 49.3 to 50.45 E on
23 October 2026. Data © OpenStreetMap contributors, Open Database Licence.

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

## Real headways (`data/headways.csv`)

Columns `route`, `headway_min` and an optional `source`. A route listed here uses this
headway instead of any estimate. Today it holds one row: H1 (Airport Express) every
20 minutes, from an airport.az press release of August 2024. Add rows as real data arrives.

## Searched for and not found

No public source gives route headways or timetables, vehicle GPS positions, ticket
validations by stop, or origin-destination data. Checked: the AYNA map API (it returns
only routes, stops and shapes), the 69 transport datasets on opendata.az, OpenStreetMap
(249 bus routes; only M5 carries an interval tag), the BakuBus and AYNA websites, and news
reports. The settings in `busnet.toml` stand in for them; see [roadmap.md](roadmap.md) for
what to request from AYNA.

## Refreshing

`python3 data/fetch_external.py --refresh` downloads every external file again from the
URLs in the script. OpenStreetMap and the opendata.az files change over time, so results
change after a refresh; commit the new data and the regenerated `output/` together.
