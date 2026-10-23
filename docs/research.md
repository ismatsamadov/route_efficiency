# Research behind the approach

This page summarises the research done in October 2026. It shaped three choices: what to
measure, which assumptions to use, and how to search for a better network.

- Figures for other cities are as their sources report them, and those sources often
  have an interest in the result.
- Figures marked *(unverified)* come from search-engine excerpts, because the source
  page could not be opened.

## 1. What to measure

A bus network serves two groups. Riders want to reach places quickly: a short walk, a
short wait, a direct ride and few changes. Operators want to provide that with as few
bus-hours, kilometres and litres as possible.

| Side | Measure | Used here as |
|---|---|---|
| Riders | Door-to-door time: walk + wait + ride + changes, with a penalty per change | `mean_door_to_door_min`, the redesign's goal |
| Riders | Share of trips possible within 30, 45 or 60 minutes | `share_within_*` |
| Riders | Changes per trip | `transfers` |
| Riders | People within walking distance of a stop | `share_population_covered`, the redesign's coverage guard |
| Operators | Bus-hours and bus-km a day, buses needed | `operations` |
| Operators | Fuel and CO₂ | `fuel_l_per_day`, `co2_t_per_day` |
| Network shape | Directness, detours, overlap, stop spacing | `routes.csv`, `detours.csv`, `duplicates.csv`, `corridors.csv` |

### Fuel or travel time?

Use both, but make one the goal and the other the budget. This is how most redesigns
work.

- **Fix the budget.** Hold the bus-hours, or the fleet, at today's level.
- **Redraw the routes.** Make riders' total door-to-door time as short as possible within
  that budget.
- **Why it works.** A shorter, straighter, less duplicated route frees buses to run more
  often. That cuts waiting, which is the largest part of most short trips.
- **Fuel falls along the way.** Fuel follows kilometres and stops, so the same changes
  save it. Alternatively, the gain can be taken as a smaller fleet for the same travel
  times. `redesign.py` reports both.

Jarrett Walker frames a related trade-off ([Human Transit](https://humantransit.org/basics)).
Running buses where many people will ride (ridership) conflicts with running buses
everywhere someone might need one (coverage). A network should therefore decide
explicitly how to split its budget between the two. Houston chose 80% ridership and 20%
coverage. Here, the redesign's coverage guard plays the coverage role: it limits how
many people may lose their stop.

## 2. Planning guidelines, and how Baku compares

| Topic | Guideline or result elsewhere | Baku now | Source |
|---|---|---|---|
| Walking distance | Stops within 400 m of homes is the usual convention. TransLink (Vancouver) aims for 90% of residents within 450 m. In Montreal, 85% of riders walked 524 m or less | 66% of people within 400 m; 73% within 500 m | [MIT lecture notes, 2017](https://live.ocw.mit.edu/courses/1-258j-public-transportation-systems-spring-2017/3c52a58746ec9861f054c9a6c48d5c56_MIT1_258JS17_lec04and05.pdf); [El-Geneidy et al., 2014](https://www.worldtransitresearch.info/research/5119) |
| Frequency | TCQSM levels: under 10 min (no timetable needed), 10–14, 15–20, 21–30, 31–60, over 60. "Frequent" usually means every 15 minutes or better all day | Not in the data; estimated 10 to 30 minutes | [TCQSM via Sound Transit](https://www.soundtransit.org/sites/default/files/documents/pdf/projects/eastlink/eis_2011/18_apph1_appb_levelofservicedefinitionsusedforeastlinkanalysis.pdf) |
| Directness | Route length at most 1.2–1.3 times the straight line between its ends, loops exempt (Soviet norm, 1981). RIPTA: 1.2× for key routes, 1.5× local, 2.5× community *(unverified)* | 20 of 182 non-loop routes meet 1.3× | [RSFSR order 200 (repealed)](https://zakonbase.ru/content/part/76594); [RIPTA, 2012](https://www.ripta.com/wp-content/uploads/2020/12/coa_tac_presentation_092012_.pdf) |
| Detours | Keep a detour only if (through riders × minutes added) ÷ riders it serves is under 5 minutes (Miami-Dade) or 3 minutes (Denver) | 271 detours; ridership per stop is needed to apply the rule | [Miami-Dade service standards](https://www.miamidade.gov/citt/library/strategic-financial-studies/2013/cost-other-studies/analysis-activity/2006-1ServiceStandardPresentation%20%5BCompatibility%20Mode%5D.pdf) |
| Stop spacing | Average spacing is about 352 m in the USA and 359–403 m elsewhere. Guidelines: TriMet 240–300 m, TransLink at least 250 m, Soviet norm 300–400 m minimum | Median 420 m; 23.9% of gaps under 300 m | [Devunuri, Lehe et al., 2022](https://arxiv.org/abs/2208.04394); [nMotion, 2015](https://www.nmotion.info/wp-content/uploads/2015/09/nMotion-Stop-Consolidation-150902.pdf) |
| Stop balancing results | About 20 s saved per stop removed (WMATA: 10–20 s, *unverified*). TriMet cut running time nearly 6% with no significant ridership loss. TransLink trips became 4–14% faster | 351 stops removable at 250 m, saving an estimated 1.5% of bus-hours | [nMotion, 2015](https://www.nmotion.info/wp-content/uploads/2015/09/nMotion-Stop-Consolidation-150902.pdf); [El-Geneidy et al., TRR 2006](https://www.worldtransitresearch.info/research/475); [TransLink](https://www.translink.ca/plans-and-projects/projects/bus-projects/bus-stop-balancing) |
| Overlap | Sharing over 75% of a route with another is "inappropriate" in Russian planning practice; 50–75% calls for cutting or re-timing one of them *(unverified)*. King County Metro keeps parallel routes about 800 m apart | 38 routes share over 75% of their stops with one other route; 25 over 85% | [Bryansk study, 2022](https://mirtr.elpub.ru/jour/article/download/2337/4107) |
| Route length | No authoritative cap found. Running-time variation grows along a route (Engelstein 1982) | Median 17 km one way | [TRID](https://trid.trb.org/View/188886) |

## 3. What other cities did

Whole-network redesigns follow a similar recipe:

- fewer, straighter routes that run more often;
- overlapping routes merged into frequent trunks;
- stops spaced further apart;
- bus lanes where routes stack up.

How much they gained depends heavily on whether service was added at the same time.

| City | What was done | Reported result | Source |
|---|---|---|---|
| Seoul, 2004 | Rebuilt in one day: trunk and feeder routes, median bus lanes, one integrated fare, operators paid per km (gross-cost contracts) | Median-lane speeds 11 to 22 km/h; passengers +20%; operating cost down by up to 9% | [UN-Habitat case study, 2013](https://unhabitat.org/sites/default/files/2013/06/GRHS.2013.Case_.Study_.Seoul_.Korea_.pdf) |
| Houston, 2015 | Every route redrawn with almost no added budget; service split moved to 80% ridership / 20% coverage; a grid of routes every 15 minutes, 7 days a week | First year: local bus ridership +1.2%; Saturdays +13%, Sundays +34% | [Streetsblog / Kinder Institute, 2016](https://sf.streetsblog.org/2016/08/17/a-year-after-houstons-bus-network-redesign-ridership-is-up); [Human Transit, 2015](https://humantransit.org/2015/02/houstons-reimagined-network-dont-let-us-make-it-look-easy.html) |
| Barcelona, 2012–2018 | Nova Xarxa: 28 straight lines in a grid, every 3 to 8 minutes, stops about 400 m apart; more transfers, little waiting; service was added | Ridership on replaced corridors +6% to +24%; 26% of trips use a transfer | [Badia, Argote-Cabanero and Daganzo, 2016](https://its.berkeley.edu/node/4590); [Human Transit, 2017](https://humantransit.org/2017/04/guest-post-barcelonas-bus-network-better-access-if-you-change-buses.html) |
| Moscow, 2016 | Magistral: 39 central surface routes merged into 17 frequent trunk routes | Surface ridership up about a third in the first year (official figure) | [ITU case study, 2018](https://www.itu.int/en/publications/Documents/tsb/2018-U4SSC-Case-of-Moscow/files/basic-html/page40.html) |
| Auckland, 2016–2018 | New Network: frequent routes every 15 minutes or better, 7am–7pm, 7 days | North Shore went from 78 to 55 routes while weekday trips rose *(unverified)*. Boardings rose faster than journeys because transfers count twice | [Auckland Council, 2018](https://ourauckland.aucklandcouncil.govt.nz/news/2018/10/north-shore-the-final-piece-of-the-new-bus-network/); [Human Transit, 2017](https://humantransit.org/?p=27486) |
| Dublin, 2022– | BusConnects, area by area: frequent spines and orbital routes; service was added | Boardings in redesigned areas +48%, against +8% elsewhere, to the end of 2024 | [BusConnects progress report, 2025](https://busconnects.ie/wp-content/uploads/2025/04/BusConnects-Dublin-Progress-Report-March-2025-WEB.pdf) |
| Tbilisi, 2018–2024 | Minibus-style network replaced by fewer, larger buses; more than 700 new buses, mostly CNG | Bus ridership +30% (operator figure, reported by EBRD) | [EBRD, 2024](https://www.ebrd.com/news/2024/tbilisi-gets-greener-and-more-inclusive.html) |
| Tashkent, 2025 | Large bus purchase; headways cut from 18–20 to 8–10 minutes | 412 million bus passengers in 2025, +26% (official) | [Kun.uz, 2026](https://kun.uz/en/48790711) |

The lessons for Baku:

- Merging duplicate routes and straightening detours pays off only if the freed buses
  run more often on the remaining routes.
- Riders accept a change of bus when the second bus comes soon.
- Results are better when bus lanes and fare integration come with the new network.

## 4. Baku's own programme

| When | What | Source |
|---|---|---|
| December 2023 | AYNA presented its Mobility Transformation Program, with an international consultant. All routes were analysed, and routes are optimised on a digital twin (computer model) of the city. 1.6 million bus trips a day | [Ministry, 2023](https://mincom.gov.az/en/media-en/news/presentation-of-mobility-transformation-program-in-azerbaijan-took-place) |
| November 2024 | Bus lanes and route optimisation raised average bus speed from 18 to 22 km/h; target of a fully electric bus fleet by 2030 | [Report.az, 2024](https://report.az/en/amp/cop29/minister-azerbaijan-plans-to-fully-electrify-its-bus-fleet-by-2030) |
| September 2025 | The consultant found weak links between Baku and Absheron routes, overlapping routes, and 17% of residents with limited bus access. The new network needs about 2,800 buses; gross-cost contracts are planned | [APA, 2025](https://en.apa.az/infrastructure/azerbaijan-to-implement-gross-contract-system-to-ensure-sustainable-public-transport-financing-478431) |
| January 2026 | The new network began launching, with 8 routes. 114 km of bus lanes; about 2,300 buses in daily service; 55% of the fleet electric or CNG | [Ministry, 2026](https://mincom.gov.az/en/media-en/news/roundtable-on-the-2025-state-program-for-the-improvement-of-transport-infrastructure-in-baku-and-surrounding-areas) |

This project works only from public data and points the same way as the consultant's
findings. Its settings use two of these figures: 22 km/h calibrates the speeds, and
2,300 buses is the reference fleet. AYNA's own model has data this project does not have.
Compare results with it wherever possible.

## 5. Designing a network by computer

Choosing a set of bus routes is the **transit network design problem** (TNDP). Choosing
their frequencies as well is the TNDFSP. Both are NP-hard: no computer can try every
possible network, so practical methods search.

- **Objectives.**
  - Riders' time: in-vehicle time, plus waiting, plus a transfer penalty (usually 5
    minutes).
  - Shares of demand served directly, with one change, with two, or not at all.
  - Operator cost: total route length or time, or the fleet.
- **Constraints.**
  - The number of routes.
  - Minimum and maximum route length.
  - All stops covered and connected.
  - The fleet size and a minimum frequency.
  - Vehicle capacity.
- **Benchmarks.** Researchers test their methods on the same small networks: Mandl (15
  nodes) and Mumford0–3 (30–127 nodes). These let an evaluator and an optimiser be
  checked against published results.
- **Methods**, from simple to advanced:
  1. Build a pool of candidate routes, then choose from it, greedily or with integer
     programming.
  2. Improve a network step by step: local search (as here), simulated annealing, tabu
     search.
  3. Evolve many networks at once: genetic algorithms and NSGA-II, which also shows the
     trade-off between rider time and operator cost.
  4. Learn to propose routes. A graph neural network trained by reinforcement learning
     reports the best benchmark results, including up to 19% lower cost on a real
     network in Laval, Canada (Holliday, El-Geneidy & Dudek, 2025). It needs real
     origin-destination data, GPUs and machine-learning experience.

### Why this project uses a greedy local search

The research recommended a path that is transparent and runs on a laptop:

1. Write one fast, trusted evaluator first. Here that is the door-to-door model,
   checked against observed ridership.
2. Start from today's routes.
3. Propose changes that redesigns elsewhere have used.
4. Keep the changes that improve the evaluator's score.

Every kept change can be explained in one sentence, which matters when people have to
approve it. The next steps are listed in [roadmap.md](roadmap.md):

- new candidate routes (k-shortest paths between busy places);
- simulated annealing or NSGA-II instead of the greedy search;
- a simplified network of 500–1,000 nodes, the size published methods handle.

Results will depend more on the quality of the demand data than on the algorithm.

## 6. Demand without origin-destination data

No public data says where Baku's bus riders travel from and to. The options, from what
is possible now to what needs agreements:

- **Gravity model (used here).** Trips between two places grow with the people at one
  end and the attractions at the other, and fall with distance. Population comes from a
  grid; attractions from OpenStreetMap and metro entries. The model is then checked
  against observed boardings. Python packages: AequilibraE, scikit-mobility
  ([JSS, 2022](https://doi.org/10.18637/jss.v103.i04)).
- **Related models.** The radiation model (Simini et al., 2012) and Deep Gravity, which
  learns from OpenStreetMap features (Simini et al., 2021).
- **Smart-card trip chaining.** It infers where each rider got off from where they next
  tapped in. It worked for over 80% of boardings in Santiago (Munizaga & Palma, 2012).
  It needs BakıKart tap records and vehicle GPS from AYNA.
- **Mobile-phone data.** In Abidjan, IBM's AllAboard project (2013) used 2.5 billion
  call records to design two new routes and one extension. It needs an agreement with
  a mobile operator.

## 7. Fuel, energy and emissions

| Topic | Finding | Source |
|---|---|---|
| Diesel, 12 m bus | 43.8 L/100 km on the Braunschweig test cycle (22.6 km/h, 2.65 stops/km); hybrids 30–36 L/100 km | [VTT, 2012](https://sarjaweb.vtt.fi/pdf/technology/2012/T46.pdf) |
| CNG | 32–39% more energy than diesel; tailpipe CO₂-equivalent 5–10% higher | VTT, 2012 |
| Battery-electric | 1.15 kWh/km on average across 79 Dutch buses; more in winter and summer (heating, air conditioning) | [Sustainable Bus, 2020](https://sustainable-bus.com/news/electric-bus-consumption-energy-report-viriciti) |
| Effect of stopping | The same bus used 17.6 MJ/km at 1.46 stops/km, 21.5 at 2.65 and 29.2 at 7.52: about 0.03–0.07 L of diesel per extra stop. In Rzeszów, stops at bus stops took about 26% of fuel | VTT, 2012; [Energies, 2024](https://ideas.repec.org/a/gam/jeners/v17y2024i16p4179-d1461419.html) |
| CO₂ factor | Diesel 74,100 kg CO₂ per TJ, about 2.67 kg per litre; natural gas about 2.69 kg per kg | [IPCC 2006, vol. 2, ch. 1](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_1_Ch1_Introduction.pdf) |

BakuBus runs mostly CNG buses plus a growing electric fleet; no split of the whole
fleet by fuel is published. Per km, diesel and CNG emit roughly the same CO₂. A better
network therefore saves more CO₂ than switching between those two fuels. The model counts
diesel-equivalent litres as a common unit ([configuration.md](configuration.md#fuel-and-emissions-fuel)).

## 8. Tools

| Tool | Use | Licence |
|---|---|---|
| GTFS | The standard format for transit networks; every tool below reads it. `redesign.py` writes it | Open standard |
| [make_gtfs](https://codeberg.org/araichev/make_gtfs) | Builds GTFS from shapes, stops and frequencies | MIT |
| [Conveyal R5](https://github.com/conveyal/r5) and r5py | Travel-time matrices and accessibility before and after a change | MIT |
| OpenTripPlanner 2 | Journey planning on GTFS | LGPL-3 |
| gtfs-kit | Analyses GTFS feeds in Python | MIT |
| MobilityData GTFS validator | Checks a feed for errors | Apache-2.0 |
| AequilibraE | Demand models and transit assignment in Python | Its own licence |
| [pymoo](https://pymoo.org) | NSGA-II and other multi-objective search algorithms | Apache-2.0 |
| [transit_learning](https://github.com/AHolliday/transit_learning) | The learned network-design method of Holliday et al. | GPL-3 |
| Remix (Via), Optibus, PTV Visum, TransCAD | Commercial planning tools | Commercial |

No public GTFS feed exists for Baku: the Mobility Database lists none for Azerbaijan.

## 9. Reading list

In order, for someone new to the field:

1. Jarrett Walker, [Human Transit basics](https://humantransit.org/basics): the
   ridership versus coverage choice and why frequency matters.
2. Durán-Micco & Vansteenwegen, 2022, *A survey on the transit network design and
   frequency setting problem*, Public Transport 14:155–190
   ([link](https://lirias.kuleuven.be/3622915)). The best place to start on methods.
3. Ibarra-Rojas et al., 2015, *Planning, operation, and control of bus transport
   systems: a literature review*, Transportation Research B 77:38–75
   ([doi](https://doi.org/10.1016/j.trb.2015.03.002)).
4. Kepaptsoglou & Karlaftis, 2009, J. Transp. Eng. 135(8):491–505
   ([doi](https://doi.org/10.1061/(ASCE)0733-947X(2009)135:8(491))); Farahani et al.,
   2013, EJOR 229(2):281–302 ([doi](https://doi.org/10.1016/j.ejor.2013.01.001)).
   Two earlier surveys.
5. Mandl, 1980, EJOR 5(6):396–404 ([doi](https://doi.org/10.1016/0377-2217(80)90126-5))
   and Mumford, 2013, IEEE CEC ([doi](https://doi.org/10.1109/CEC.2013.6557668)). The
   standard test networks.
6. Holliday, El-Geneidy & Dudek, 2025, Transportmetrica B
   ([doi](https://doi.org/10.1080/21680566.2025.2561863)). The state of the art with
   learned methods.
7. Badia, Argote-Cabanero & Daganzo, 2016 ([link](https://its.berkeley.edu/node/4590)).
   What happened when Barcelona built a grid.
