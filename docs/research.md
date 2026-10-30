# Research behind the approach

I did this reading in October 2026 to decide three things: what to measure, which
assumptions to use, and how to search for a better network. Figures for other cities
are as their sources report them, and those sources often have an interest in the
result. I checked every figure against its source on 23 October 2026, twice and
independently; where a page no longer opens, I link an archived copy or the publisher's
record.

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

I use both, but make one the goal and the other the budget, which is how the redesigns
in section 3 worked: hold the bus-hours, or the fleet, at today's level, then redraw the
routes to make riders' total door-to-door time as short as possible within it. It works
because a shorter, straighter, less duplicated route frees buses to run more often, and
that cuts waiting, which for a short trip can outweigh the ride itself. Fuel falls along
the way, since it follows kilometres and stops; alternatively the gain can be taken as a
smaller fleet for the same travel times, and `redesign.py` reports both.

Jarrett Walker frames a related trade-off ([Human Transit](https://humantransit.org/basics-the-ridership-coverage-tradeoff)).
Running buses where many people will ride (ridership) conflicts with running buses
everywhere someone might need one (coverage). A network should therefore decide
explicitly how to split its budget between the two. Houston's board chose 80% ridership
and 20% coverage ([Walker, 2014](https://humantransit.org/2014/05/houston-a-transit-network-reimagined.html)).
In my redesign the coverage guard plays the coverage role: it limits how many people
may lose their stop.

## 2. Planning guidelines, and how Baku compares

| Topic | Guideline or result elsewhere | Baku now | Source |
|---|---|---|---|
| Walking distance | Stops within 400 m (a quarter mile) of homes is the usual convention: the TCQSM defines a bus route's coverage area as everything within 400 m of a stop. TransLink (Vancouver) set a target in its 2004 guidelines of at least 90% of residents and employees in denser areas within a 450 m walk of a stop, about 400 m in a straight line. In Montreal, 85% of home-based walks to a bus were 524 m or shorter | 66% of people within 400 m in a straight line, 45% along mapped streets and paths; 73% and 55% within 500 m | [TCQSM, 2nd ed., part 3](https://onlinepubs.trb.org/onlinepubs/tcrp/docs/tcrp100/Part3.pdf); [MIT lecture notes, 2017](https://live.ocw.mit.edu/courses/1-258j-public-transportation-systems-spring-2017/3c52a58746ec9861f054c9a6c48d5c56_MIT1_258JS17_lec04and05.pdf); [El-Geneidy et al., 2014](https://www.worldtransitresearch.info/research/5119) |
| Frequency | TCQSM levels: under 10 min (passengers do not need a timetable), 10–14 ("frequent service"), 15–20, 21–30, 31–60, over 60. Agencies such as TransLink define a "frequent" network as service every 15 minutes or better throughout the day, every day | Not in the data; estimated 10 to 30 minutes | [TCQSM via Sound Transit](https://www.soundtransit.org/sites/default/files/documents/pdf/projects/eastlink/eis_2011/18_apph1_appb_levelofservicedefinitionsusedforeastlinkanalysis.pdf); [TransLink service guidelines, 2018](https://www.translink.ca/-/media/translink/documents/plans-and-projects/managing-the-transit-network/transit-oriented-communities/transit-services-guidelines-public-summary.pdf) |
| Directness | Route length at most 1.2–1.3 times the straight line between its ends, loops exempt (Soviet norm, 1981). RIPTA's 2012 study showed 1.2× the most direct distance for key routes, 1.5× for local and 2.5× for community routes as example guidelines | 20 of 182 non-loop routes meet 1.3× | [RSFSR order 200 (repealed)](https://zakonbase.ru/content/part/76594); [RIPTA, 2012 (archived copy)](https://web.archive.org/web/20220127223345id_/https://ripta.com/wp-content/uploads/2020/12/coa_tac_presentation_092012_.pdf) |
| Detours | Keep a detour only if (through riders × minutes added) ÷ riders it serves is under 5 minutes (Miami-Dade) or 3 minutes (Denver) | 271 detours; ridership per stop is needed to apply the rule | [Miami-Dade service standards](https://www.miamidade.gov/citt/library/strategic-financial-studies/2013/cost-other-studies/analysis-activity/2006-1ServiceStandardPresentation%20%5BCompatibility%20Mode%5D.pdf) |
| Stop spacing | Average spacing, weighted by how often buses pass, is about 352 m in the USA and 359 m across 38 cities elsewhere (401 and 403 m weighted by segment). Guidelines: TriMet about 240–305 m by density; TransLink 250–400 m on standard routes and 300–800 m on frequent ones; Soviet norm 300–400 m minimum | Median 420 m; 23.9% of gaps under 300 m | [Devunuri, Lehe et al., 2023](https://arxiv.org/abs/2208.04394); [nMotion, 2015](https://www.nmotion.info/wp-content/uploads/2015/09/nMotion-Stop-Consolidation-150902.pdf); [TransLink service guidelines, 2018](https://www.translink.ca/-/media/translink/documents/plans-and-projects/managing-the-transit-network/transit-oriented-communities/transit-services-guidelines-public-summary.pdf) |
| Stop balancing results | About 20 s saved per stop removed; WMATA's stop consolidation programme estimated 10–20 s per stop. TriMet cut running time nearly 6% with no significant ridership loss. TransLink's rebalanced routes saved about 4–14% of travel time across the day | 351 stops removable at 250 m, saving an estimated 1.5% of bus-hours | [nMotion, 2015](https://www.nmotion.info/wp-content/uploads/2015/09/nMotion-Stop-Consolidation-150902.pdf); [WMATA, 2011 (archived copy)](https://web.archive.org/web/20160621185056/http://planitmetro.com/2011/01/03/metrobus-bus-stop-consolidation-program/); [El-Geneidy et al., TRR 2006](https://www.worldtransitresearch.info/research/475); [TransLink](https://www.translink.ca/plans-and-projects/projects/bus-projects/bus-stop-balancing) |
| Overlap | A 2022 study of Bryansk, Russia, calls sharing over 75% of a route's length with another route "inappropriate"; at 50–75% one of the routes should be cancelled or its timetable adjusted. King County Metro's service guidelines say routes should in general be no closer than half a mile (about 800 m) apart | 38 routes share over 75% of their stops with one other route; 25 over 85% | [Sivakov et al., 2022](https://mirtr.elpub.ru/jour/article/view/2337); [King County Metro service guidelines, 2021](https://cdn.kingcounty.gov/-/media/king-county/depts/metro/documents/about/policies/equity/metro-service-guidelines-111721.pdf) |
| Route length | No authoritative cap found. Running-time variation grows with distance from the start of a route (Abkowitz and Engelstein, 1982) | Median 17 km one way | [TRID](https://trid.trb.org/View/188886) |

## 3. What other cities did

The redesigns below followed a similar recipe: fewer, straighter routes that run more
often, overlapping routes merged into frequent trunks, stops spaced further apart, and
bus lanes where routes stack up. How much they gained went with whether service was
added at the same time.

| City | What was done | Reported result | Source |
|---|---|---|---|
| Seoul, 2004 | All bus services reorganised at once on 1 July 2004: trunk and feeder routes, median bus lanes, one integrated fare, operators paid per vehicle-km (gross-cost contracts) | Bus speeds rose from 11 to 22 km/h by 2010, and by 33–100% in the median-lane corridors at the outset; passengers +20%; operating cost down by up to 9% | [UN-Habitat case study, 2013](https://unhabitat.org/sites/default/files/2013/06/GRHS.2013.Case_.Study_.Seoul_.Korea_.pdf) |
| Houston, 2015 | Nearly every route redrawn within about the same operating budget; the resource split moved to 80% ridership / 20% coverage; a grid of 22 routes every 15 minutes or better, 7 days a week, with much more evening and weekend service | First year: local bus ridership +1.2%; Saturdays +13%, Sundays +34%, weekdays −1% | [Streetsblog / Kinder Institute, 2016](https://sf.streetsblog.org/2016/08/17/a-year-after-houstons-bus-network-redesign-ridership-is-up); [Human Transit, 2014](https://humantransit.org/2014/05/houston-a-transit-network-reimagined.html); [Human Transit, 2015](https://humantransit.org/2015/02/houstons-reimagined-network-dont-let-us-make-it-look-easy.html) |
| Barcelona, 2012–2018 | Nova Xarxa: 28 lines in a grid, designed for headways of 3 to 8 minutes and stops about 400 m apart; more transfers, little waiting; service was added | Ridership on replaced corridors +6% to +24%; about 26% of trips involved a transfer by the end of 2015 | [Badia, Argote-Cabanero and Daganzo, 2016](https://its.berkeley.edu/node/4590); [Human Transit, 2017](https://humantransit.org/2017/04/guest-post-barcelonas-bus-network-better-access-if-you-change-buses.html) |
| Moscow, 2016 | Magistral: the first routes consolidated 39 surface routes in the centre into 17 | Surface-transport ridership up by a third in the first year (city figure) | [ITU case study, 2018](https://www.itu.int/en/publications/Documents/tsb/2018-U4SSC-Case-of-Moscow/files/basic-html/page40.html) |
| Auckland, 2016–2018 | New Network: frequent routes every 15 minutes or better, 7am–7pm, 7 days | North Shore went from 78 to 55 routes while weekday trips rose. Boardings rose faster than journeys because transfers count twice | [Auckland Council, 2018](https://ourauckland.aucklandcouncil.govt.nz/news/2018/10/north-shore-the-final-piece-of-the-new-bus-network/); [Human Transit, 2017](https://humantransit.org/?p=27486) |
| Dublin, 2021– | BusConnects, area by area: frequent spines and orbital routes; service was added | Boardings in redesigned areas +48%, against +8% elsewhere, to the end of 2024 | [BusConnects progress report, 2025](https://busconnects.ie/wp-content/uploads/2025/04/BusConnects-Dublin-Progress-Report-March-2025-WEB.pdf); [National Transport Authority, 2025](https://www.nationaltransport.ie/news/busconnects-network-plan-sees-spike-in-passenger-numbers-in-dublin/) |
| Tbilisi, 2016–2024 | Minibus fleet cut back and large buses added: about 860 new buses in 2016–2022, 370 of them CNG, with 18-metre CNG buses arriving from 2024 | Bus ridership +30% (operator figure, reported by EBRD) | [EBRD, 2024](https://www.ebrd.com/news/2024/tbilisi-gets-greener-and-more-inclusive.html); [Bankwatch, 2022](https://bankwatch.org/wp-content/uploads/2022/09/2022-09-29_Tbilisi-urban-public-transit-reform.pdf) |
| Tashkent, 2023–2025 | 1,000 buses bought in 2023, with more on order; headways cut from 18–20 to 8–10 minutes | 412 million bus passengers in 2025, +26% (official) | [Kun.uz, 2026](https://kun.uz/en/48790711) |

What I take from them for Baku: merging duplicate routes and straightening detours pays
off only if the freed buses run more often on the remaining routes; riders accept a
change of bus when the second bus comes soon; and results are better when bus lanes and
fare integration come with the new network.

## 4. Baku's own programme

| When | What | Source |
|---|---|---|
| December 2023 | The Ministry presented the Mobility Transformation Program, which AYNA launched with an international consulting company. All route lines were analysed, and routes are optimised on a digital twin (computer model) of Baku. 1.6 million bus trips a day | [Ministry, 2023](https://mincom.gov.az/en/media-en/news/presentation-of-mobility-transformation-program-in-azerbaijan-took-place) |
| November 2024 | Bus lanes and route optimisation raised the speed of buses in Baku from 18 to 22 km/h; target of a fully electric bus fleet by 2030 | [Report.az, 2024](https://report.az/en/amp/cop29/minister-azerbaijan-plans-to-fully-electrify-its-bus-fleet-by-2030) |
| September 2025 | The consultant found weak links between Baku and Absheron routes, overlapping routes, and 17% of residents with limited bus access. The new network needs about 2,800 buses; gross-cost contracts are planned | [APA, 2025](https://en.apa.az/infrastructure/azerbaijan-to-implement-gross-contract-system-to-ensure-sustainable-public-transport-financing-478431) |
| January 2026 | The new network began launching, with 8 routes. 114 km of bus lanes; about 2,300 buses in daily service; 55% of the fleet described as eco-friendly (395 new electric and CNG buses) | [Ministry, 2026](https://mincom.gov.az/en/media-en/news/roundtable-on-the-2025-state-program-for-the-improvement-of-transport-infrastructure-in-baku-and-surrounding-areas) |

I work only from public data and reach the same conclusions as the consultant. Two of
these figures are in my settings: 22 km/h calibrates the speeds and 2,300 buses is the
reference fleet. AYNA's own model has data I do not have, and I would compare results
with it wherever possible.

## 5. Designing a network by computer

Choosing a set of bus routes is the **transit network design problem** (TNDP). Choosing
their frequencies as well is the TNDFSP. Both are NP-hard (Kepaptsoglou & Karlaftis,
2009): no computer can try every possible network, so practical methods search. The
surveys in section 9 describe the usual formulation:

- **Objectives.**
  - Riders' time: in-vehicle time, plus waiting, plus a transfer penalty (5 minutes in
    the Mandl and Mumford benchmark studies).
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
  checked against published results. My scoring reproduces Mumford's (2013) published
  scores exactly, and the redesign's straightening improves her route sets best for
  passengers on both scores, while methods published since reach far lower travel times
  ([benchmark.md](benchmark.md)).
- **Methods**, from simple to advanced:
  1. Build a pool of candidate routes, then choose from it, greedily or with integer
     programming.
  2. Improve a network step by step: local search (as here), simulated annealing, tabu
     search.
  3. Evolve many networks at once: genetic algorithms and NSGA-II, which also shows the
     trade-off between rider time and operator cost.
  4. Learn to propose routes. A graph neural network trained by reinforcement learning
     reports new best results on the Mumford benchmark and up to 19% lower cost in a
     simulation of the real network of Laval, Canada (Holliday, El-Geneidy & Dudek,
     2025). It needs real origin-destination data, GPUs and machine-learning experience.

### Why I use a greedy local search

I wanted something transparent that runs on a laptop: one fast, trusted evaluator first
(the door-to-door model, checked against observed ridership), then start from today's
routes, propose the changes that redesigns elsewhere have used, and keep the ones that
improve the evaluator's score. Every kept change can be explained in one sentence,
which matters when people have to approve it. The obvious next steps, listed in
[roadmap.md](roadmap.md), are new candidate routes (k-shortest paths between busy
places), simulated annealing or NSGA-II instead of the greedy search, and a simplified
network of 500–1,000 nodes, nearer the sizes published methods have been run on (the
largest standard benchmark, Mumford3, has 127 nodes). My judgement is that the results
will depend more on the quality of the demand data than on the algorithm.

## 6. Demand without origin-destination data

No public data says where Baku's bus riders travel from and to, so I use a gravity
model: trips between two places grow with the people at one end and the attractions at
the other, and fall with distance. Population comes from a grid, attractions from
OpenStreetMap and metro entries, and the model is checked against observed boardings.
The Python packages AequilibraE and scikit-mobility ([JSS, 2022](https://doi.org/10.18637/jss.v103.i04))
do the same job, and the radiation model (Simini et al., 2012) and Deep Gravity, which
learns from OpenStreetMap features (Simini et al., 2021), are the related models.

Two better options need data I cannot get. Smart-card trip chaining infers where each
rider got off from where they next tapped in; it worked for over 80% of boardings in
Santiago (Munizaga & Palma, 2012), and it would need BakıKart tap records and vehicle
GPS, which AYNA does not release. Mobile-phone data is the other: in Abidjan, IBM's AllAboard
project (2013) worked on samples of a 2.5-billion-record call dataset from Orange's
Data for Development challenge, scored 65 candidate routes and recommended four new
ones that cut modelled travel times by about 10%
([Berlingerio et al., 2013](https://perso.uclouvain.be/vincent.blondel/netmob/2013/D4D-book.pdf)).
It needs an agreement with a mobile operator.

## 7. Fuel, energy and emissions

| Topic | Finding | Source |
|---|---|---|
| Diesel, 12 m bus | 43.8 L/100 km on the Braunschweig test cycle (22.6 km/h, 2.65 stops/km); hybrids 30–36 L/100 km | [VTT, 2012](https://sarjaweb.vtt.fi/pdf/technology/2012/T46.pdf) |
| CNG | 32–39% more energy than the diesel average; tailpipe CO₂-equivalent about 4–11% higher, depending on the engine and on whether VTT's text or its charts are read | VTT, 2012 |
| Battery-electric | 1.15 kWh/km on average across 79 Dutch buses; about 14% more in the cold months and 9% more in summer | [Sustainable Bus, 2020](https://sustainable-bus.com/news/electric-bus-consumption-energy-report-viriciti) |
| Effect of stopping | VTT's diesel test bus used 13.5 MJ/km at 1.46 stops/km, 16.4 at 2.65 and 21.6 at 7.52 (its CNG bus 17.6, 21.5 and 29.2). The slope works out at roughly 0.03–0.07 L of diesel per extra stop: our estimate, which also absorbs the lower speeds of the denser cycles. In Rzeszów, stops at bus stops took about 26% of fuel | VTT, 2012; [Energies, 2024](https://ideas.repec.org/a/gam/jeners/v17y2024i16p4179-d1461419.html) |
| CO₂ factor | Diesel 74,100 kg CO₂ per TJ at 43.0 TJ/Gg, i.e. 3.19 kg per kg of fuel or about 2.67 kg per litre at a density of 0.84 kg/L (the density is not from IPCC); natural gas 56,100 kg per TJ at 48.0 TJ/Gg, about 2.69 kg per kg | [IPCC 2006, vol. 2, ch. 1](https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_1_Ch1_Introduction.pdf) |

By January 2026, 55% of the fleet was described as eco-friendly (electric or CNG,
section 4) and no split of the whole fleet by fuel is published. Per km, diesel and CNG
emit roughly the same CO₂. A better
network therefore saves more CO₂ than switching between those two fuels, so I count
diesel-equivalent litres as a common unit ([configuration.md](configuration.md#fuel-and-emissions-fuel)).

## 8. Tools

| Tool | Use | Licence |
|---|---|---|
| GTFS | The standard format for transit networks; the transit tools below read it. `redesign.py` writes it | Open standard |
| [make_gtfs](https://codeberg.org/araichev/make_gtfs) | Builds GTFS from shapes, stops and frequencies | MIT |
| [Conveyal R5](https://github.com/conveyal/r5) and [r5py](https://github.com/r5py/r5py) | Travel-time matrices and accessibility before and after a change | MIT (r5py: MIT or GPL-3) |
| OpenTripPlanner 2 | Journey planning on GTFS | LGPL-3 |
| gtfs-kit | Analyses GTFS feeds in Python | MIT |
| [MobilityData GTFS validator](https://github.com/MobilityData/gtfs-validator) | The canonical check of a feed for errors and warnings; `validate_gtfs.py` runs it on both feeds | Apache-2.0 |
| [gtfstools](https://ipea.github.io/gtfstools/) | Edits and analyses GTFS feeds in R; its `validate_gtfs()` runs the MobilityData validator | MIT |
| AequilibraE | Demand models and transit assignment in Python | Its own licence |
| [pymoo](https://pymoo.org) | NSGA-II and other multi-objective search algorithms | Apache-2.0 |
| [transit_learning](https://github.com/AHolliday/transit_learning) | The learned network-design method of Holliday et al. | GPL-3 |
| Remix (Via), Optibus, PTV Visum, TransCAD | Commercial planning tools | Commercial |

No public GTFS feed exists for Baku: the Mobility Database lists none for Azerbaijan.

## 9. Reading list

In the order I would read them, for someone new to the field:

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
   standard test networks; John, Mumford & Lewis, 2014, EvoCOP, 49–60, and Ahmed,
   Mumford & Kheiri, 2019, EJOR 274(2):545–559, improve on them, and Hüsselmann, van
   Vuuren & Andersen, 2024, Computers & Operations Research 163:106481
   ([doi](https://doi.org/10.1016/j.cor.2023.106481)), finds route sets much cheaper to
   run, and Jiao, 2026, a preprint with code and data on Zenodo
   ([doi](https://doi.org/10.5281/zenodo.23759374)), reaches the lowest average travel
   times so far with certified lower bounds; both publish their route sets, and
   [benchmark.md](benchmark.md) compares them and runs the straightening on them.
6. Holliday, El-Geneidy & Dudek, 2025, Transportmetrica B
   ([doi](https://doi.org/10.1080/21680566.2025.2561863); accepted manuscript
   [arXiv:2404.05894](https://arxiv.org/abs/2404.05894)). The state of the art with
   learned methods; its Table 3 collects the best published results on the benchmark
   networks.
7. Badia, Argote-Cabanero & Daganzo, 2016 ([link](https://its.berkeley.edu/node/4590)).
   What happened when Barcelona built a grid.
