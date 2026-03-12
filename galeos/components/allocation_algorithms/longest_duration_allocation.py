from ..process_unit import ProcessUnit
from geopy.distance import geodesic
from ..satellite import Satellite
from ..user import User 
from math import sqrt
import networkx as nx

def has_path(topology, origin, target):
    """Verifica se existe conectividade via rede terrestre."""
    for access_point in origin.network_access_points:
        if nx.has_path(G=topology, source=access_point, target=target):
            return True
    return False

def distance(coordinates1, coordinates2):
    """Calcula a distância 3D entre dois pontos."""
    if coordinates1 is None or coordinates2 is None:
        return float('inf')
    ground_distance = geodesic(coordinates1[:2], coordinates2[:2]).kilometers 
    air_distance = (coordinates1[2] - coordinates2[2]) / 1000
    return sqrt(ground_distance**2 + air_distance**2)

def get_exposure_time(user, satellite):
    """Calcula por quantos passos de simulação o satélite ainda estará visível."""
    step = user.model.scheduler.steps
    max_distance = min(user.max_connection_range, satellite.max_connection_range)
    count = 0
    
    # Simula a trajetória futura para prever a duração da conexão
    for coordinates in satellite.coordinates_trace[step:]:
        if coordinates is not None:
            if distance(coordinates1=coordinates, coordinates2=user.coordinates) < max_distance:
                count += 1
            else:
                break
    return count

def longest_duration_allocation(model, scenario):
    # Algoritmo de alocação com contagem de provisionamentos por step.
    
    # Criamos um dicionário no objeto model para persistir os dados entre os steps
    if not hasattr(model, 'provisioning_history'):
        model.provisioning_history = {}
    
    step_atual_str = str(model.scheduler.steps)
    if step_atual_str not in model.provisioning_history:
        model.provisioning_history[step_atual_str] = 0

    applications_to_be_allocated = []

    # 1. Identificar aplicações que precisam de provisionamento
    for user in User.all():
        for access_model in user.applications_access_models:
            if not access_model.request_provisioning and access_model.application.available:
                access_model.application.deprovision()
            elif access_model.request_provisioning and not access_model.application.available:
                applications_to_be_allocated.append(access_model)
            else:
                process_unit = access_model.application.process_unit
                if not any(
                    (process_unit in model.topology.neighbors(ap) for ap in user.network_access_points)
                ) or user.network_access_points == []:
                    applications_to_be_allocated.append(access_model)

    # 2. Ordenar aplicações
    def get_remaining_time(access_model):
        last_access = access_model.history[-1]
        if last_access.get('required_provisioning_time'):
            return last_access.get('required_provisioning_time') - last_access['provisioned_time']
        return last_access['end'] - model.scheduler.steps
    
    applications_to_be_allocated.sort(key=get_remaining_time, reverse=True)

    # 3. Alocação
    for access_model in applications_to_be_allocated:
        best_target = None
        max_duration = -1
        sat = None

        # Tenta Ground Stations
        if scenario['scenario'] == 'terrestrial' or scenario['scenario'] == 'hybrid':
            for unit in ProcessUnit.all():
                if not isinstance(getattr(unit, 'owner', None), Satellite):
                    if unit.has_capacity_to_host(access_model.application) and unit.available:
                        if has_path(model.topology, access_model.user, unit):
                            best_target = unit
                            max_duration = float('inf')
                            break 
        
        # Tenta Satélites
        if best_target is None:
            for access_point in access_model.user.network_access_points:
                if not model.topology.has_node(access_point):
                    continue
                
                if (isinstance(access_point, Satellite) and access_point.active):
                    pu = getattr(access_point, 'process_unit', None)
                    if pu and pu.available and pu.has_capacity_to_host(access_model.application):
                        duration = get_exposure_time(access_model.user, access_point)
                        if duration > max_duration:
                            max_duration = duration
                            best_target = pu

        # 4. Provisionamento e Contagem
        if best_target is not None:
            app = access_model.application
            
            # Executa o provisionamento
            if best_target != app.process_unit:
                app.provision(best_target)
                
                # Incrementa o contador de provisionamentos
                model.provisioning_history[step_atual_str] += 1