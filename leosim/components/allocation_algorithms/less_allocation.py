from ..process_unit import ProcessUnit
from ..satellite import Satellite
from ..user import User

import networkx as nx

def has_path(topology, origin, target):
    for access_point in origin.network_access_points:
        if nx.has_path(G=topology, source=access_point, target=target):
            return True
    
    return False

def less_distance_allocation(model, parameters):     
    applications_to_be_allocated = []
    
    # Select which applications require provisioning
    for user in User.all():
        for access_model in user.applications_access_models:
            if not access_model.request_provisioning and access_model.application.available:
                access_model.application.deprovision()

            elif access_model.request_provisioning and not access_model.application.available:
                applications_to_be_allocated.append(access_model)
                
            elif access_model.request_provisioning:
                process_unit = access_model.application.process_unit
                # If not directly connected to a network access point
                if not any(
                    ( process_unit in model.topology.neighbors(access_point)  for access_point in user.network_access_points)
                ) or user.network_access_points == []:
                    applications_to_be_allocated.append(access_model)

    # Iterate over provisioning demands
    for access_model in applications_to_be_allocated:
        process_units = []
        # Search for ProcessUnits directly connected to network access points
        for access_point in access_model.user.network_access_points:
            if isinstance(access_point, Satellite) and getattr(access_point, 'process_unit') is not None:
                process_unit = access_point.process_unit

                if process_unit.has_capacity_to_host(access_model.application) and process_unit.available:
                    process_units.append(process_unit)

        # Try to allocate in the ground network
        if process_units == []:   
            process_units = []
            for unit in ProcessUnit.all():
                # Check if communication with this server is possible
                if unit.has_capacity_to_host(access_model.application) and unit.available and has_path(model.topology, access_model.user, unit):
                    process_units.append(unit)

        if process_units == []:
            if access_model.application.available:
                access_model.application.deprovision()
            continue

        if process_units:
            target = min(process_units, key=lambda u: model.topology.calculate_distance(u, access_model.user))

            if target != access_model.application.process_unit:
                access_model.application.provision(target)
