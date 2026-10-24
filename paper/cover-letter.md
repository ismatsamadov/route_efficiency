# Cover letter

Ismat Samadov, Independent researcher, Baku, Azerbaijan. ORCID 0009-0007-7919-4950.
E-mail: ismetsemedov@gmail.com.

To the Editor-in-Chief, Public Transport

Dear Editor,

I submit the manuscript "How efficient are Baku's bus routes? An open-data measurement
and a fleet-neutral redesign" for consideration in Public Transport as a Case Study and
Application.

Baku, a city of 2.4 million, is redesigning its network of about 200 bus routes, but no
evaluation of the network has been published and the data that one would normally rest
on (timetables, vehicle positions, where riders travel) is not public. The paper asks
how much can be measured, and how far a redesign can be tested, from public data alone,
and answers with three results. First, the inherited network is measured from the
agency's public map after its undocumented defects are repaired: only 29 of 201 routes
are direct, 271 detours add 939 km to one trip in each direction of every route, and
66% of residents live within 400 m of a stop. Second, a door-to-door travel model built
from public data ranks routes against observed boardings at a Spearman correlation of
0.58, and the paper states that agreement rather than assuming the model is right.
Third, a fleet-neutral greedy search, which applies the changes used by network
redesigns elsewhere, shortens the average trip by about a minute or gives today's
modelled travel times with about 12% fewer buses; the gain holds on 10 independent trip
samples and under 14 alternative assumptions, including a run without the least certain
kind of change.

The paper suits the journal's interest in case studies and applications of
computer-aided methods in public transport planning: the travel model, the search and
the robustness checks are all implemented in a standard-library Python pipeline, and
today's network and the redesign are written as GTFS feeds. Every input and every
result are released with a DOI (10.5281/zenodo.23604370), so the measurements can be
regenerated and the method applied to other cities that publish only a map, once a
reader for their map format is written. The manuscript is about 6,600 words with four
tables and four figures.

The manuscript is not under consideration elsewhere and has not been published before.
A preprint was submitted to engrXiv on 24 October 2026 (submission 8632) and its DOI
will be given on the title page once assigned. I have no competing interests and
received no funding. I am the sole author, writing as an independent researcher; the
use of an AI writing tool is declared in the manuscript. The earlier, unreviewed GitHub
report on the same data that the manuscript cites and supersedes is my own.

Yours sincerely,

Ismat Samadov
