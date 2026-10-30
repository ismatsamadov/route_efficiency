# The search on benchmark networks

Baku has no answer key. Nobody knows the best network for the city, so a search that
shortens the modelled trip by a minute could be finding real improvements or ones the
model invents. Before trusting the search on 3,456 stops I wanted to see it work where
the answers are known. The literature on designing bus routes by computer has such
places: a handful of small networks on which researchers have published their best route
sets and their scores for more than a decade. `python3 benchmark.py` runs the test in
about two minutes and writes `output/benchmark/` ([outputs.md](outputs.md#outputbenchmark--the-search-on-the-benchmark-networks)).

## The networks and their rules

Mandl's network has 15 nodes and comes from a Swiss town (Mandl, 1980). Mumford (2013)
built four larger ones, Mumford0 to Mumford3, with 30, 70, 110 and 127 nodes. Each
comes with the minutes it takes to drive every link, the trips between every pair of
nodes, and the number of routes to run. For each network Mumford published the route set
her evolutionary algorithm found best for passengers and the one best for the operator,
with their scores; her supplement holds the networks, those route sets and the score
table ([data.md](data.md#benchmark-networks-dataexternalutrp)).

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

Scored here, all ten published route sets give exactly the values of Mumford's Table IV,
each of the six measures to the second decimal (`output/benchmark/published.csv`). This
checks the benchmark scoring, not the Baku travel model, which scores trips differently;
what it shows is that the comparison below is made on the literature's own terms.

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

## What this shows, and what it does not

It shows that the search finds real improvements in a network it did not design,
judged by the literature's own scores and rules. It does not show that the search designs
good networks. Methods published since reach much lower ATT on the same networks, and on
every Mumford network at least one of them beats the improved sets on both scores:

| Network | Passes repeated, here | Lowest ATT reported since (method) | DBMOSA (Hüsselmann et al., 2024) |
|---|---|---|---|
| Mumford0 | 15.86, 692 | 14.09, 722 (Ahmed et al., 2019) | 15.48, 431 |
| Mumford1 | 24.20, 1,800 | 21.69, 1,956 (Ahmed et al., 2019) | 22.31, 1,359 |
| Mumford2 | 28.07, 4,944 | 24.92, 5,655 (RC-EA, Holliday et al., 2025) | 25.65, 3,583 |
| Mumford3 | 30.63, 5,768 | 27.60, 6,896 (RC-EA, Holliday et al., 2025) | 28.22, 4,060 |

The later results are the passenger-best route sets that Table 3 of Holliday, El-Geneidy
and Dudek (2025) collects; I read the accepted manuscript, arXiv:2404.05894. Those
methods build routes from shortest paths, lengthen them and move nodes within and
between routes, and judge every move by the travel time over the demand. Straightening
can only shorten a route that exists, so it cannot reach them, and that is also its
role in Baku: it improves today's network rather than designing a new one. The
conclusion is the one I draw for Baku: the search finds improvements, not the best
network.

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
  163: 106481 ([doi](https://doi.org/10.1016/j.cor.2023.106481)).
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
