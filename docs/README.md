# Documentation

This folder explains everything in the repository: where the data comes from, what
every setting means, how each measurement and the redesign search work, what every
output file contains, what the results are, and what I would do next.

## The project in one paragraph

Baku's bus network (208 routes, about 3,500 stops, from AYNA's public map) had never
been measured in public for how well it serves riders, and the data to do it properly
is not public either: no timetables, no vehicle positions, no origin-destination data.
So I measured what the geometry alone can tell: routes that wander, routes that repeat
each other, stops too close together, detours, and people left without a nearby stop.
Then I built a travel model from public population, ridership, metro and OpenStreetMap
data to estimate door-to-door travel times and daily bus operation, with every
assumption in one settings file, and a search that changes the network step by step
with today's fleet, keeping a change only if trips get faster without cutting people
off. The redesign shortens the average trip from 51.8 to 50.9 minutes with the same
buses, or matches today's trip times with about 12% fewer buses and 12% less fuel, and
the gain holds on ten samples of trips and under fourteen other assumptions. I treat its
changes as candidates for review, not a plan; [results.md](results.md#check-these-before-acting)
lists what to check first.

## Where to read

| If you want to... | Read |
|---|---|
| Run the tools and regenerate every result | [getting-started.md](getting-started.md) |
| See the latest findings and the redesign | [results.md](results.md) |
| See how much the results depend on the trip sample and the assumptions | [results.md](results.md#how-robust-the-results-are) |
| Understand the data, its defects, the repairs and the licences | [data.md](data.md) |
| Change an assumption or a data path | [configuration.md](configuration.md) |
| Know exactly how a number is computed | [methodology.md](methodology.md) |
| Understand the redesign algorithm and how to tune it | [redesign.md](redesign.md) |
| Read any output file, column by column | [outputs.md](outputs.md) |
| Change or extend the code | [code.md](code.md) |
| See the research and other cities' experience behind the approach | [research.md](research.md) |
| Know what comes next, the limitations and the open questions | [roadmap.md](roadmap.md) |
| Turn the work into a research paper: outline, venues, format, steps for an independent researcher | [paper.md](paper.md) |
| Read the manuscript draft and its title page | [../paper/manuscript.md](../paper/manuscript.md), [../paper/title-page.md](../paper/title-page.md) |
| Look up a term | [glossary.md](glossary.md) |

## Three commands

```sh
python3 measure.py --scenario stop-balancing --min-gap 250   # measure today's network (about 12 s)
python3 redesign.py                                          # search for a better one (about 2 minutes)
python3 robustness.py                                        # the results under other samples and assumptions (about 15 minutes)
```

All three read `busnet.toml` and the data committed under `data/`, need only Python 3.11
or newer, and give byte-identical results on every run. `python3 -m unittest` runs the
tests.
