"""Every number the metrics assume because the data does not contain it.

The AYNA snapshot has no timetables, frequencies, speeds or ridership, so travel
time and fuel are modelled from these values. Change them here (or pass your own
Assumptions) and every metric follows. When real data arrives (GPS speeds,
headways, ticket validations), replace the matching assumption with it."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Assumptions:
    # Walking
    walk_speed_mps: float = 1.25          # about 4.5 km/h
    walk_detour: float = 1.3              # street distance / straight-line distance
    max_access_walk_m: float = 500        # furthest someone walks to or from a stop
    max_transfer_walk_m: float = 300      # furthest someone walks between stops to change buses
    coverage_radius_m: float = 400        # industry convention for bus stops (TCQSM; TransLink uses 450 m)

    # Waiting and transferring
    headway_min: float = 12               # assumed time between buses on every route
    transfer_penalty_min: float = 5       # extra perceived cost of each change, on top of waiting

    # Riding: moving speed between stops by working zone, plus a fixed loss at every stop.
    # Speeds are calibrated so the network-wide average comes to 22 km/h, the bus speed AYNA
    # reported after bus lanes and route changes (Ministry of Digital Development, Nov 2024).
    cruise_kmh: dict = field(default_factory=lambda: {
        "Şəhərdaxili": 22, "Şəhərdaxili (ekspres)": 29,
        "Şəhərətrafı": 29, "Şəhərətrafı (ekspres)": 36,
        "Qəsəbədaxili": 25, "Qəsəbələrarası": 31, "Şəhərlərarası": 40,
    })
    default_cruise_kmh: float = 25
    stop_loss_s: float = 20               # slowing, serving and accelerating (nMotion 2015; WMATA 10-20 s)

    # Fuel and emissions for a 12 m bus, in diesel-equivalent litres. Together these give
    # 43 L/100 km at 2.65 stops/km, matching the Braunschweig test cycle for diesel buses
    # (43.8 L/100 km, VTT 2012); VTT's measured cost of an extra stop is 0.03-0.07 L.
    # CNG buses use about 35% more energy for similar CO2 per km; electric about 1.15 kWh/km.
    fuel_l_per_km: float = 0.30           # steady driving between stops
    fuel_l_per_stop: float = 0.05         # one stop-start cycle
    co2_kg_per_l: float = 2.67            # diesel, tank-to-wheel (IPCC 2006)

    # Demand model used when there is no origin-destination data
    trip_decay_km: float = 6.0            # trips between places fall off as exp(-distance / this)
    max_trip_min: float = 120             # longer door-to-door times count as "not reachable"

    def cruise_mps(self, zone):
        return self.cruise_kmh.get(zone, self.default_cruise_kmh) / 3.6

    @property
    def wait_s(self):
        return self.headway_min * 60 / 2

    @property
    def transfer_penalty_s(self):
        return self.transfer_penalty_min * 60
