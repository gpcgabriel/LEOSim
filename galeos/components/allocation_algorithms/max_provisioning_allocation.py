from ..process_unit import ProcessUnit
from ..satellite import Satellite
from ..user import User

import networkx as nx

def has_path(topology, origin, target):
    """Verifica se existe caminho entre o usuário e a unidade de processamento."""
    for access_point in origin.network_access_points:
        if nx.has_path(G=topology, source=access_point, target=target):
            return True
    return False

def max_provisioning_allocation(model, parameters):
    """
    Ordena a lista de aplicações para que as aplicações que "pesam" menos sejam processadas primeiro. Isso evita que uma única aplicação gigante consuma recursos que poderiam sustentar cinco aplicações pequenas.

    Ao escolher a unidade de processamento, ele utiliza o Best-Fit para minimizar o desperdício de recursos.

    Se uma aplicação perde a conexão direta mas ainda pode ser provisionada via rede terrestre ou outro satélite, o algoritmo a inclui na tentativa de realocação em vez de simplesmente descartá-la.
    """
    
    applications_to_be_allocated = []

    # 1. Identificação das aplicações que precisam de provisionamento
    for user in User.all():
        for access_model in user.applications_access_models:
            # Se a aplicação não precisa mais e está disponível, desprovisiona
            if not access_model.request_provisioning and access_model.application.available:
                access_model.application.deprovision()

            # Se precisa e não está disponível, vai para a fila
            elif access_model.request_provisioning and not access_model.application.available:
                applications_to_be_allocated.append(access_model)
            
            # Se já está disponível, verifica se ainda há conectividade direta
            elif access_model.request_provisioning and access_model.application.available:
                process_unit = access_model.application.process_unit
                if not any(
                    (process_unit in model.topology.neighbors(access_point) for access_point in user.network_access_points)
                ) or user.network_access_points == []:
                    # Se perdeu a conexão direta, tenta realocar para manter o maior número possível
                    applications_to_be_allocated.append(access_model)

    # 2. ESTRATÉGIA DE MAXIMIZAÇÃO: Ordenar aplicações pela menor demanda de recursos total
    # Aplicações "leves" primeiro garantem que mais aplicações caibam no sistema.
    applications_to_be_allocated.sort(key=lambda am: (
        am.application.cpu_demand + 
        am.application.memory_demand + 
        am.application.storage_demand
    ))

    # 3. Iteração sobre as demandas ordenadas
    for access_model in applications_to_be_allocated:
        possible_units = []

        # Coleta todas as unidades de processamento em satélites ao alcance direto
        for access_point in access_model.user.network_access_points:
            if isinstance(access_point, Satellite) and getattr(access_point, 'process_unit', None):
                pu = access_point.process_unit
                if pu.has_capacity_to_host(access_model.application) and pu.available:
                    possible_units.append(pu)

        # Coleta todas as unidades de processamento terrestres (Ground Network) com caminho disponível
        for pu in ProcessUnit.all():
            # Evita duplicar se o satélite já foi adicionado acima
            if pu not in possible_units:
                if pu.has_capacity_to_host(access_model.application) and pu.available:
                    if has_path(model.topology, access_model.user, pu):
                        possible_units.append(pu)

        # 4. Seleção: Para maximizar o número, pegamos a primeira unidade capaz (First Fit)
        # após termos priorizado as aplicações menores.
        if possible_units:
            # Selecionamos a unidade que terá o melhor encaixe (Best Fit) para preservar recursos
            # para as próximas aplicações da fila.
            target_unit = min(possible_units, key=lambda u: (
                (u.cpu - access_model.application.cpu_demand) +
                (u.memory - access_model.application.memory_demand) +
                (u.storage - access_model.application.storage_demand)
            ))
            
            if target_unit != access_model.application.process_unit:
                access_model.application.provision(target_unit)
        else:
            # Se não há onde alocar, e ela estava ativa, removemos para liberar espaço
            if access_model.application.available:
                access_model.application.deprovision()