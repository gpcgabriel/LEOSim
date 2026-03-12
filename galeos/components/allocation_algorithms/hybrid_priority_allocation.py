from ..satellite import Satellite
from ..process_unit import ProcessUnit
from ..user import User

from math import sqrt
from geopy.distance import geodesic
import networkx as nx

def has_path(topology, origin, target):
    """Verifica se existe conectividade na rede entre a origem e o destino."""
    for access_point in origin.network_access_points:
        if nx.has_path(G=topology, source=access_point, target=target):
            return True
    return False

def distance_3d(coordinates1, coordinates2):
    """Calcula a distância real entre o usuário e o satélite/unidade."""
    if coordinates1 is None or coordinates2 is None:
        return float('inf')
    ground_distance = geodesic(coordinates1[:2], coordinates2[:2]).kilometers 
    air_distance = (coordinates1[2] - coordinates2[2]) / 1000
    return sqrt(ground_distance**2 + air_distance**2)

def get_exposure_time(user, satellite):
    """Calcula o tempo de permanência do satélite no alcance do usuário."""
    step = user.model.scheduler.steps
    max_distance = min(user.max_connection_range, satellite.max_connection_range)
    count = 0
    for coordinates in satellite.coordinates_trace[step:]:
        if coordinates is not None:
            if distance_3d(coordinates, user.coordinates) < max_distance:
                count += 1
            else:
                break
    return count

def hybrid_priority_allocation(model, parameters):
    """
        O algoritmo primeiro tenta aproveitar a borda LEO, alocando no satélite que está em contato direto com o usuário. Para garantir qualidade, ele usa a função get_exposure_time para escolher o satélite que ficará visível por mais tempo.
        Se não houver satélites diretos capazes, ele busca em terra. dist_threshold dita que se uma GroundStation estiver muito longe, o algoritmo entende que o custo de rede (latência/sinal) é alto demais para a alocação.
        Caso as opções ideais falhem, ele adota a estratégia do less_allocation, buscando qualquer unidade disponível (seja outro satélite via múltiplos saltos ou terra) que ofereça a menor distância topológica na rede, minimizando o impacto de muitas migrações ou saltos desnecessários.
    """

    # Parâmetro para definir o que é 'muito longe' ou exigente em terra
    dist_threshold = parameters.get('ground_distance_threshold', 1000) 
    
    applications_to_be_allocated = []

    # Seleção de aplicações que necessitam de alocação ou realocação
    for user in User.all():
        for access_model in user.applications_access_models:
            if not access_model.request_provisioning and access_model.application.available:
                access_model.application.deprovision()
            elif access_model.request_provisioning:
                if not access_model.application.available:
                    applications_to_be_allocated.append(access_model)
                else:
                    # Verifica se a conexão com a unidade atual foi perdida
                    pu = access_model.application.process_unit
                    if not any(pu in model.topology.neighbors(ap) for ap in user.network_access_points):
                        applications_to_be_allocated.append(access_model)

    for access_model in applications_to_be_allocated:
        selected_unit = None
        
        # 1- Priorizar satélites que processarão o serviço diretamente
        # Busca satélites no alcance direto com capacidade disponível
        direct_sats = []
        for ap in access_model.user.network_access_points:
            if isinstance(ap, Satellite) and hasattr(ap, 'process_unit'):
                pu = ap.process_unit
                if pu and pu.has_capacity_to_host(access_model.application) and pu.available:
                    direct_sats.append(ap)
        
        if direct_sats:
            # Seleciona o satélite com melhor tempo de exposição para evitar migrações precoces
            best_sat = max(direct_sats, key=lambda s: get_exposure_time(access_model.user, s))
            selected_unit = best_sat.process_unit

        # 2- Caso o satélite não seja opção, tenta processar em terra (GroundStations)
        if selected_unit is None:
            ground_units = []
            for pu in ProcessUnit.all():
                # Identifica unidades de terra (sem dono satélite) e verifica caminho
                if not isinstance(getattr(pu, 'owner', None), Satellite):
                    if pu.has_capacity_to_host(access_model.application) and pu.available:
                        if has_path(model.topology, access_model.user, pu):
                            dist = model.topology.calculate_distance(pu, access_model.user)
                            # Verifica se o processamento em terra não é 'muito exigente' (distância/sinal)
                            if dist < dist_threshold:
                                ground_units.append((pu, dist))
            
            if ground_units:
                # Escolhe a unidade terrestre mais próxima dentro do limite aceitável
                selected_unit = min(ground_units, key=lambda x: x[1])[0]

        # 3- Se terra for muito exigente ou indisponível, utiliza o menor caminho (Shortest Path)
        # Esta é a estratégia de fallback para garantir o provisionamento
        if selected_unit is None:
            possible_targets = []
            for pu in ProcessUnit.all():
                if pu.has_capacity_to_host(access_model.application) and pu.available:
                    if has_path(model.topology, access_model.user, pu):
                        possible_targets.append(pu)
            
            if possible_targets:
                # Seleção puramente baseada na menor distância topológica
                selected_unit = min(possible_targets, key=lambda u: model.topology.calculate_distance(u, access_model.user))

        # Finaliza o provisionamento na unidade escolhida
        if selected_unit and selected_unit != access_model.application.process_unit:
            access_model.application.provision(selected_unit)