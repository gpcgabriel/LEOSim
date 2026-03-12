from ..process_unit import ProcessUnit
from ..satellite import Satellite
from ..user import User
import networkx as nx

def has_path(topology, origin, target):
    for access_point in origin.network_access_points:
        if nx.has_path(G=topology, source=access_point, target=target):
            return True
    
    return False

def simple_allocation(model, parameters):
    def is_better(other, current_unit):
        return ( 
            (other.cpu - other.cpu_demand) < (current_unit.cpu - current_unit.cpu_demand) and
            (other.memory - other.memory_demand) < (current_unit.memory - current_unit.memory_demand) and
            (other.storage - other.storage_demand) < (current_unit.storage - current_unit.storage_demand)
        )
        
    applications_to_be_allocated = []

    # Select which applications need provisioning
    for user in User.all():
        for access_model in user.applications_access_models:
            if access_model.request_provisioning:
                if not access_model.application.available:
                    applications_to_be_allocated.append(access_model)
                else:
                    process_unit = access_model.application.process_unit
                    # If not directly connected to a network access point
                    if not any(
                        process_unit in model.topology.neighbors(access_point)  for access_point in user.network_access_points
                    ) or user.network_access_points == []:
                        access_model.application.deprovision()
                        applications_to_be_allocated.append(access_model)

            elif access_model.application.available:
                access_model.application.deprovision()

    # Iterate over provisioning demands
    for access_model in applications_to_be_allocated:
        process_units = []

        # Look for ProcessUnits directly connected to network access points
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

        selected = process_units[0]

        for process_unit in process_units:
            if is_better(process_unit, selected):
                selected = process_unit

        if selected != access_model.application.process_unit:
            access_model.application.provision(selected)