from leosim import *
from dataset_generator import *
from random import choices, randint, sample

def load_topology(ground_topology: str, leo_topology, max_satellites) -> Topology:
    t = load_ground_topology_from_gml(ground_topology)

    create_satellite_topology(
        topology = t,
        filename = leo_topology,
        max_steps = 180, 
        sat_range = 500,
        max_satellites = max_satellites
    )

    for sat in Satellite.all():
        sat.is_gateway = True

    # To control the number of gateways
    # for sat in sample(Satellite.all(), Satellite.count()):
    #     sat.is_gateway = True

    for station in GroundStation.all():
        for sat in Satellite.all():
            if sat.coordinates is None:
                continue
            
            if t.within_range(station, sat) and sat.is_gateway:
                if t.has_edge(station, sat):
                    continue
                create_link(sat, station, topology=t)
    return t

def create_users(num_users: int) -> None:
    # Collect available coordinates from satellite traces
    coordinates_history = [coor for sat in Satellite.all() for coor in sat.coordinates_trace if coor is not None]

    for coordinates in choices(coordinates_history, k=num_users):
        user = create_user(coordinates)
        user.mobility_model = random_mobility_model

        create_application_to_user(
            user=user,
            cpu_demand=randint(10, 50),
            memory_demand=randint(10, 50),
            access_class=FixedDurationAccessModel
        )

def add_process_unit_to_satellites(topology, num_process_units: int):
    targets = sample(Satellite.all(), min(num_process_units, Satellite.count()))
    
    for satellite in targets:
        unit = ProcessUnit(
            cpu=randint(30, 50),
            memory=randint(30, 50),
            storage=randint(30, 50)
        )
        unit.coordinates = satellite.coordinates
        create_link(unit, satellite, 1, bandwidth=NetworkLink.default_bandwidth, topology=topology)
        satellite.process_unit = unit

def add_process_unit_to_ground_stations(topology, num_process_units: int):
    targets = sample(GroundStation.all(), min(num_process_units, GroundStation.count()))
    
    for station in targets:
        unit = ProcessUnit(
            cpu=randint(50, 100),
            memory=randint(50, 100),
            storage=randint(50, 100)
        )
        unit.coordinates = station.coordinates
        create_link(unit, station, 10, NetworkLink.default_bandwidth, topology=topology)
        station.process_unit = unit

def configure_mobility_models():   
    for sat in Satellite.all():
        sat.mobility_model = coordinates_history 
        sat.mobility_model_parameters = {'len': len(sat.coordinates_trace)}