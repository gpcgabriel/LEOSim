from ..process_unit import ProcessUnit
from geopy.distance import geodesic
from ..satellite import Satellite
from ..user import User
import networkx as nx
from math import sqrt

def has_path(topology, origin, target):
    for access_point in origin.network_access_points:
        if nx.has_path(G=topology, source=access_point, target=target):
            return True
    
    return False

def distance(coordinates1: object, coordinates2: object):
    if coordinates1 is None or coordinates2 is None:
        return float('inf')
    
    ground_distance = geodesic(coordinates1[:2], coordinates2[:2]).kilometers 
    air_distance = (coordinates1[2] - coordinates2[2]) / 1000

    return sqrt(ground_distance**2 + air_distance**2)

def get_exposure_time(user, satellite):
    step = user.model.scheduler.steps
    max_distance = min(user.max_connection_range, satellite.max_connection_range)
    count = 0

    satellite.mobility_model(satellite)

    for coordinates in satellite.coordinates_trace[step:]:
        if coordinates is not None:
            if distance(coordinates1=coordinates, coordinates2=user.coordinates) < max_distance:
                count += 1
            else:
                break

    return count

def best_exposure_time(model, _):
    applications_to_be_allocated = []

    # Select applications that require provisioning
    for user in User.all():
        for access_model in user.applications_access_models:
            if not access_model.request_provisioning and access_model.application.available:
                access_model.application.deprovision()

            elif access_model.request_provisioning and not access_model.application.available:
                applications_to_be_allocated.append(access_model)
            else:
                process_unit = access_model.application.process_unit
                # If not directly connected to a network access point
                if not any(
                    (process_unit in model.topology.neighbors(access_point) for access_point in user.network_access_points)
                ) or user.network_access_points == []:
                    applications_to_be_allocated.append(access_model)

    def key(access_model):
        last_access = access_model.history[-1]

        if last_access.get('required_provisioning_time'):
            time = last_access.get('required_provisioning_time') - last_access['provisioned_time']
        else:
            time = last_access['end'] - model.scheduler.steps

        return time
    
    for access_model in sorted(applications_to_be_allocated, key=key):
        selected = None
        time = 0
        # Look for ProcessinfUnits directly connected to network access points
        for access_point in access_model.user.network_access_points:
            if isinstance(access_point, Satellite) and getattr(access_point, 'process_unit') is not None:
                process_unit = access_point.process_unit

                if process_unit.has_capacity_to_host(access_model.application) and process_unit.available:
                    if selected is None:
                        selected = access_point
                        time = get_exposure_time(access_model.user, access_point)
                    elif time < get_exposure_time(access_model.user, access_point):
                        selected = access_point
                        time = get_exposure_time(access_model.user, access_point)

        if selected is not None:
            access_model.application.provision(selected.process_unit)
            continue

        # Try to allocate on ground network
        if selected is None:
            for process_unit in ProcessUnit.all():
                # Check if communication with this process_unit is possible
                if process_unit.has_capacity_to_host(access_model.application) and process_unit.available and has_path(model.topology, access_model.user, process_unit):
                    if process_unit != access_model.application.process_unit:
                        access_model.application.provision(process_unit)
                        break