# Data sources

Every file the measurements read is committed here, so `python3 measure.py` reproduces
every result without downloading anything. `python3 data/fetch_external.py --refresh`
downloads the external files again from the sources below. Retrieved 23 October 2026
unless noted.

## Bus network

| File | Contents | Source | Licence |
|---|---|---|---|
| `ayna.db` | 208 routes, 3,841 stops, stop sequences and route shapes | AYNA map API (`map-api.ayna.gov.az`, an unauthenticated OpenAPI service), via the `data/ayna.sqlite` snapshot in github.com/samirmehd1yev/best_route_finding (scraped and committed 6 May 2026, commit `8010c00`; coordinates repaired 11 October 2026, commit `b8c51d5`) | None. The data is AYNA's; neither AYNA nor the API publishes terms of use (ayna.gov.az states only "All rights reserved"). The snapshot repository has no licence file; the "ISC" in its README, `package.json` and the `meta` table covers its code, not AYNA's data. Redistributed here as a research snapshot with attribution to AYNA; this repository's licence does not extend to it |
| `ayna_scraper.py` | Script that builds `ayna.db` from the AYNA API | This repository | |
| `headways.csv` | Real headways where a public source gives one; add rows as data arrives | See the `source` column ([airport.az, August 2024](https://www.airport.az/en/press-release/h1-airport-express-route-will-now-operate-24-7-for-the-convenience-of-passengers/)) | |

The licences of the opendata.az datasets below come from the portal's CKAN metadata
(`https://admin.opendata.az/api/3/action/package_show?id=<dataset id>`), which records
the generic Open Definition `cc-by` and `cc-zero` entries without a version; the dataset
web pages do not display them. The three State Statistical Committee tables are
downloaded from the Committee's open-data API (see `fetch_external.py`) and are also
published on opendata.az by the Committee (datasets `f3d36c3a-8bdc-4ceb-9bd5-2c73d2db2d8d`,
`843bdfbf-9c46-4e07-b9a7-1d831ba3697a` and `1ea3ff52-a1bd-46a8-9d95-0fe2e0b35798`), where
their licence is recorded as CC0.

## Population

| File | Contents | Source | Licence |
|---|---|---|---|
| `external/kontur/kontur_population_AZ_20231101.gpkg` | Population on H3 hexagons (~0.74 km²), 10.48 million people in Azerbaijan | Kontur Population, release 2023-11-01, [HDX](https://data.humdata.org/dataset/kontur-population-azerbaijan) | CC BY (HDX: Creative Commons Attribution International; no version stated) |
| `external/stat/population_by_district_2026.xls` | Official population by city and district, 1 January 2026 | State Statistical Committee, [table 1.15](https://www.stat.gov.az/source/demoqraphy/en/001_15en.xls) | Official statistics; no licence stated |

## Ridership and travel

| File | Contents | Source | Licence |
|---|---|---|---|
| `external/opendata/bakubus_passenger-2026.csv` | Daily boardings per BakuBus route, January to September 2026 | Bakı Metropoliteni via [opendata.az](https://admin.opendata.az/dataset/32766a9d-479c-41ff-a660-7b739b4ff034) | CC BY |
| `external/opendata/bakubus_payment_type-2026.csv` | Monthly share of payment types per BakuBus route | Bakı Metropoliteni via [opendata.az](https://admin.opendata.az/dataset/a98b2492-680a-401a-ab39-4e2b6ad0f270) | CC BY |
| `external/opendata/metro_passengers-2025.csv`, `metro_passengers-2026.csv` | Daily entries per metro station | Bakı Metropoliteni via [opendata.az](https://admin.opendata.az/dataset/66051a52-1172-4c59-8ea2-1062562c991f) | CC BY |
| `external/opendata/metro_payment_type-2026.csv` | Monthly share of payment types per metro station | Bakı Metropoliteni via [opendata.az](https://admin.opendata.az/dataset/2d3f1d95-5465-4e54-a14e-555c02785729) | CC BY |
| `external/opendata/metro_exits.csv` | Coordinates of 98 metro exits | Bakı Metropoliteni via [opendata.az](https://admin.opendata.az/dataset/3108fb32-8483-4126-8283-17f2f1452548) | CC BY |
| `external/opendata/ayna_buslines.kmz` | Official bus route lines, November 2025 | AYNA via [opendata.az](https://admin.opendata.az/dataset/366c03c3-f60a-4198-b8e4-959af2082296) | CC0 |
| `external/opendata/ayna_bus_stations.geojson` | Intercity bus stations and their coordinates | AYNA via [opendata.az](https://admin.opendata.az/dataset/0d42439f-191f-40f5-82df-21742123465e) | CC0 |
| `external/opendata/stat_avg_trip_distance.csv` | Average trip length per passenger by mode and year | State Statistical Committee, table DT_BJ_050 | CC0 |
| `external/opendata/stat_passengers_by_mode.csv` | Passengers carried by mode and year | State Statistical Committee, table DT_BJ_004 | CC0 |
| `external/opendata/stat_urban_electric_transport.csv` | Urban electric transport statistics | State Statistical Committee, table DT_BJ_049 | CC0 |

## Destinations (OpenStreetMap)

Queried through the Overpass API for the box 39.9–40.7 N, 49.3–50.45 E. Data © OpenStreetMap contributors, available under the [Open Database Licence](https://www.openstreetmap.org/copyright).

| File | Contents |
|---|---|
| `external/osm/osm_bus_routes_tags.json` | Tags of 249 bus route relations (only route M5 has an interval tag) |
| `external/osm/osm_education.json` | Schools, colleges, universities, kindergartens |
| `external/osm/osm_health.json` | Hospitals and clinics |
| `external/osm/osm_shopping.json` | Malls, supermarkets, department stores, markets |
| `external/osm/osm_offices.json` | Offices, town halls, courthouses |
| `external/osm/osm_transport.json` | Railway and bus stations |

## Searched for and not found

No public source gives route headways or timetables, vehicle positions, or ticket
validations by stop. Checked: the AYNA map API, opendata.az (69 transport datasets),
OpenStreetMap, the BakuBus and AYNA websites, and news reports. Until AYNA or the
operators share them, `busnet.toml` holds the assumptions that stand in for them.
