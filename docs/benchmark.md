# The search on benchmark networks

Baku has no answer key. Nobody knows the best network for the city, so a search that
shortens the modelled trip by a minute could be finding real improvements or ones the
model invents. Before trusting the search on 3,456 stops I wanted to see it work where
the answers are known. The literature on designing bus routes by computer has such
places: a handful of small networks on which researchers have published their best route
sets and their scores for more than a decade. `python3 benchmark.py` runs the test in
about three minutes and writes `output/benchmark/` ([outputs.md](outputs.md#outputbenchmark--the-search-on-the-benchmark-networks)).

## The networks and their rules

Mandl's network has 15 nodes and comes from a Swiss town (Mandl, 1980). Mumford (2013)
built four larger ones, Mumford0 to Mumford3, with 30, 70, 110 and 127 nodes. Each
comes with the minutes it takes to drive every link, the trips between every pair of
nodes, and the number of routes to run. For each network Mumford published the route set
her evolutionary algorithm found best for passengers and the one best for the operator,
with their scores; her supplement holds the networks, those route sets and the score
table ([data.md](data.md#benchmark-networks-dataexternalutrp)). Two later studies publish
the route sets behind their scores as well: Hüsselmann, van Vuuren and Andersen (2024),
whose two algorithms, a dominance-based simulated annealing they call DBMOSA and NSGA-II,
each give a set best for passengers and a set best for the operator on every network, and
Jiao (2026), whose preprint reports the lowest average travel times so far and archives
the sets ([data.md](data.md#route-sets-published-later-husselmann2024-jiao2026)). That
makes 35 published route sets to start from.

A route set is scored the way that literature scores it
([methodology.md](methodology.md#12-the-benchmark-networks)). Every route runs both
ways, and each trip takes its quickest path, counting 5 minutes for every change of
route. The average travel time of all trips, ATT, is the passengers' score; the minutes
it takes to drive every route once, the route time, is the operator's; and the shares of
trips with no change, one, two or more say how direct the network is. Unlike the Baku
model there is no walking and no waiting, and so no frequencies.

The rules are what make results comparable. The number of routes is fixed (6 on Mandl's
network, 12, 15, 56 and 60 on Mumford's); every route must have between a minimum and a
maximum number of nodes (Mumford, 2013, Table II), follow the links and visit no node
twice; every node must be on some route; and every node must be reachable from every
other. The nodes are the network itself, so a search that removes one is solving a
different problem.

Under those rules only one of the redesign's five kinds of change
([redesign.md](redesign.md#the-changes-it-tries)) survives. Merging a near-duplicate
route and dropping a lightly used one both lower the number of routes,
and the search never adds a route back. Stop balancing removes nodes. Moving buses needs
frequencies. Straightening a detour survives: it replaces a stretch of a route by the
quickest path between the stretch's ends, the route keeps its place in the count, and
any node it leaves behind must still be on another route.

## The scoring is the literature's

Scored here, all ten of Mumford's published route sets give exactly the values of her
Table IV, each of the six measures to the second decimal (`output/benchmark/published.csv`).
Hüsselmann's sixteen Mumford sets give exactly the six scores in their files, to the
fourth decimal, and Jiao's five sets exactly the author's ATT; Hüsselmann's four Mandl
sets differ by up to 0.03 minutes, because the Mandl demand matrix in their code differs
from Mumford's file for one pair of nodes. This checks the benchmark scoring, not the Baku travel
model, which scores trips differently; what it shows is that the comparisons below are
made on the literature's own terms.

## What straightening does to the published route sets

I started from each published route set and ran the straightening the way
`redesign.py` runs it, with the one difference the data forces: a detour is a stretch
whose time along the route is longer than the quickest path between its ends along the
network's links, where in Baku a detour is measured against the straight line. Stretches
are at most 12 nodes apart and no more than 40% of the route; the 80 that save the most
route time are tried one at a time; those that lower ATT are applied in order of their
gain, each scored again on the routes as they are by then; and a change is kept only if
ATT falls by more than 0.005 minutes. Then I ran it again with the passes repeated until
one keeps nothing, which `redesign.py` does not do.

On the four Mumford networks, straightening improves the route sets that were best for
passengers on both scores at once (ATT in minutes, then route time in minutes):

| Network | Published (Mumford, 2013) | One pass, as in the redesign | Passes repeated |
|---|---|---|---|
| Mumford0 | 16.05, 759 | 15.87, 704 (4 changes) | 15.86, 692 (5 changes) |
| Mumford1 | 24.79, 2,038 | 24.35, 1,909 (7) | 24.20, 1,800 (12) |
| Mumford2 | 28.65, 5,632 | 28.27, 5,267 (12) | 28.07, 4,944 (26) |
| Mumford3 | 31.44, 6,665 | 30.87, 6,047 (17) | 30.63, 5,768 (28) |

One pass cuts ATT by 1.2 to 1.8% and route time by 6.3 to 9.3%; repeated passes by 1.2
to 2.6% and 8.8 to 13.5%. Fewer trips need three or more changes: on Mumford3, 0.95%
after one pass against 2.81%. Every improved set keeps every rule, and a second scorer
that I wrote separately, with a change arc between every pair of routes at a node instead
of a node for changing, gives the same ATT, route time and shares from the route set
files in `output/benchmark/route_sets/`, which are in the format of Mumford's supplement.

On Mandl's network, and on every route set that was best for the operator, straightening
finds nothing. The operator's sets have routes as short as the rules allow: on Mumford1
to Mumford3, 30 of the 31 tries and 78 of the 80 would leave a route with fewer nodes
than the minimum, and on Mandl's and Mumford0's networks most tries would leave a node on
no route or cut the network in two. The few tries that keep the rules do not lower ATT,
and neither do the seven that keep them on Mandl's best set for passengers.

## The later route sets

Mumford's sets are from 2013, and the sharper question is whether straightening finds
anything in the best sets published since. I ran the same two searches on the 25 sets
of Hüsselmann et al. (2024) and Jiao (2026). They change four, each by one stretch, and
repeating the passes adds nothing (ATT in minutes, then route time; nodes numbered from
1 as in Mumford's files):

| Route set | Published | After straightening | The one change |
|---|---|---|---|
| Mumford1, DBMOSA, passengers | 22.3111, 1,359 | 22.3048, 1,343 | route 2: 65-52-35-26-13-42-46 becomes 65-59-46, 16 minutes shorter |
| Mumford1, NSGA-II, passengers | 21.9443, 1,851 | 21.9387, 1,848 | route 10: 33-19-39-37 becomes 33-55-37, 3 minutes |
| Mumford2, DBMOSA, passengers | 25.6481, 3,583 | 25.6421, 3,576 | route 15: 76-51-96-18-28-102-95 becomes 76-18-28-95, 7 minutes |
| Mumford3, DBMOSA, operator | 32.3302, 2,682 | 32.3107, 2,681 | route 44: 61-74-49-98-12-78 becomes 61-74-49-1-78, 1 minute |

Each of the four improves the published set on both scores, by 0.02 to 0.06% of ATT and
0.04 to 1.2% of route time, and keeps every rule. The other 21 sets, among them all five
of Jiao's and both sets best for passengers on Mumford3, straightening leaves as they
are. On the passengers' sets most tries keep the rules and none of them lowers ATT: a
stretch that is longer than the quickest path between its ends is there because it
carries trips, and cutting it costs those trips more than it saves the rest. On the
operator's sets, as on Mumford's, nearly every try would break a rule: on Mumford1 to
Mumford3 by leaving a route with fewer nodes than the minimum, on Mandl's and Mumford0's
by leaving a node on no route or cutting the network in two. The sets straightening
changes are in
`output/benchmark/route_sets/`, in Mumford's format.

So the later sets hold almost no detours. Mumford's sets of 2013 held stretches her
evolutionary algorithm had not removed, and straightening finds them; the sets of 2024
and 2026 reach far lower travel times by building different routes, not by carrying
shorter ones, and the one kind of change the search can make under the rules is already
made in them. Jiao's certified lower bounds say how much any method has left to find:
0.3% of ATT on Mumford0 and 1.3% on Mumford1, 2.0% on Mumford2 and 2.8% on Mumford3.

## What this shows, and what it does not

It shows that the search finds real improvements in a network it did not design,
judged by the literature's own scores and rules, when the network has detours left in
it. It does not show that the search designs good networks. Methods published since
reach much lower ATT on the same networks, and on every Mumford network at least one of
them beats Mumford's improved sets on both scores:

| Network | Mumford's set, passes repeated | Lowest ATT in a journal (method) | Jiao (2026), preprint | Certified lower bound (Jiao, 2026) |
|---|---|---|---|---|
| Mumford0 | 15.86, 692 | 14.09, 722 (Ahmed et al., 2019) | 13.80, 747 | 13.76 |
| Mumford1 | 24.20, 1,800 | 21.69, 1,956 (Ahmed et al., 2019) | 21.21, 1,976 | 20.93 |
| Mumford2 | 28.07, 4,944 | 24.92, 5,655 (RC-EA, Holliday et al., 2025) | 24.00, 5,493 | 23.51 |
| Mumford3 | 30.63, 5,768 | 27.60, 6,896 (RC-EA, Holliday et al., 2025) | 26.74, 6,652 | 25.99 |

The journal results are the passenger-best route sets that Table 3 of Holliday,
El-Geneidy and Dudek (2025) collects; I read the accepted manuscript, arXiv:2404.05894.
Those methods build routes from shortest paths, lengthen them and move nodes within and
between routes, and judge every move by the travel time over the demand; Jiao's search
goes lower still and proves how little is left. Straightening can only shorten a route
that exists, so it cannot reach them, and in their own route sets it finds next to
nothing to shorten. That is also its role in Baku: it improves today's network rather
than designing a new one. The conclusion is the one I draw for Baku: the search finds
improvements, not the best network.

Two smaller lessons. On Mumford1 to Mumford3, repeating the passes adds 34 to 53% to
the gain in ATT and 45 to 88% to the saving in route time, so a single pass leaves gains
behind; `redesign.py` makes one pass, and repeating it there would be cheap to try. And
the benchmark says nothing about the parts of the Baku result that carry most of the
uncertainty: waiting times from estimated headways, walking, and a demand model that
ranks routes at 0.58 against counted boardings. Those cannot be tested on a network
whose demand is given.

## References

- Ahmed, L., Mumford, C. & Kheiri, A. (2019). Solving urban transit route design problem
  using selection hyper-heuristics. European Journal of Operational Research 274(2):
  545–559.
- Holliday, A., El-Geneidy, A. & Dudek, G. (2025). Learning heuristics for transit
  network design and improvement with deep reinforcement learning. Transportmetrica B
  13(1)
  ([doi](https://doi.org/10.1080/21680566.2025.2561863); accepted manuscript
  [arXiv:2404.05894](https://arxiv.org/abs/2404.05894)).
- Hüsselmann, G., van Vuuren, J. H. & Andersen, S. J. (2024). An improved solution
  methodology for the urban transit routing problem. Computers & Operations Research
  163: 106481 ([doi](https://doi.org/10.1016/j.cor.2023.106481)); route sets at
  [github.com/GHuss7/UTRP-Improvements-Article-Results](https://github.com/GHuss7/UTRP-Improvements-Article-Results).
- Jiao, T. (2026). Certified bounds and exact search for transit route network design.
  Preprint, version 2 of 22 October 2026, with code, route sets and certificates on
  Zenodo ([doi](https://doi.org/10.5281/zenodo.23759374); all versions
  [10.5281/zenodo.23523785](https://doi.org/10.5281/zenodo.23523785)).
- John, M. P., Mumford, C. L. & Lewis, R. (2014). An improved multi-objective algorithm
  for the urban transit routing problem. In Evolutionary Computation in Combinatorial
  Optimisation (EvoCOP 2014), 49–60. Springer. Its Table 1 gives the same rules as
  Mumford (2013).
- Mandl, C. E. (1980). Evaluation and optimization of urban public transportation
  networks. European Journal of Operational Research 5(6): 396–404
  ([doi](https://doi.org/10.1016/0377-2217(80)90126-5)).
- Mumford, C. L. (2013). New heuristic and evolutionary operators for the multi-objective
  urban transit routing problem. 2013 IEEE Congress on Evolutionary Computation, 939–946
  ([doi](https://doi.org/10.1109/CEC.2013.6557668)).
