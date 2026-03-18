from ..component_manager import ComponentManager
from .network_flow import NetworkFlow
from .network_link import NetworkLink
from .process_unit import ProcessUnit
from geopy.distance import geodesic
from .satellite import Satellite
from .user import User
import networkx as nx
import math
from typing import List, Any, Optional, Tuple

class Topology(ComponentManager, nx.Graph):
    """Manages the network graph and connectivity logic of the simulation.

    Inherits from networkx.Graph to provide graph theory operations while 
    integrating with the simulator's component management. It handles 
    dynamic link removal, path delay calculations, and flow rerouting.

    Attributes:
        _instances (list): List of all active Topology instances.
        _object_count (int): Counter for generating unique identifiers.
        id (int): Unique identifier for the topology instance.
    """
    _instances = []
    _object_count = 0

    def __init__(self, obj_id: int = 0, existing_graph: nx.Graph = None) -> None:
        """Initializes a Topology instance.

        Args:
            obj_id (int): Unique ID. If 0, it is automatically assigned.
            existing_graph (nx.Graph, optional): An existing NetworkX graph 
                to initialize the topology data.
        """
        self.__class__._instances.append(self)
        self.__class__._object_count += 1
        
        # Note: logic preserved from original (using 'id' check)
        if id == 0:
            obj_id = self.__class__._object_count
        self.id = obj_id

        if existing_graph is None:
            nx.Graph.__init__(self)
        else:
            nx.Graph.__init__(self, incoming_graph_data=existing_graph)
         
    def step(self) -> None:
        """Executes the topology events for the current simulation step.
        
        This includes removing invalid links, running management algorithms, 
        updating delays, rerouting flows, and scheduling.
        """
        self.remove_invalid_connections()
        self.model.topology_management_algorithm(
            topology=self, 
            **self.model.topology_management_parameters
        )
        self.update_delay()
        self.reroute_flows()
        self.flow_schedule()

    def update_delay(self) -> None:
        """Updates the delay attribute for all edges based on node coordinates."""
        for u, v, data in self.edges(data=True):
            link = data
            if isinstance(link, NetworkLink) and u.coordinates and v.coordinates:
                link['delay'] = link.get_delay()

    def flow_schedule(self) -> None:
        """Placeholder for bandwidth allocation or flow scheduling logic."""
        pass
    
    def reroute_flows(self) -> None:
        """Performs routing for flows whose current paths have become invalid.
        
        Checks connectivity for all active flows and finds new shortest paths 
        based on delay if the existing path is broken.
        """
        for flow in NetworkFlow.all():
            if flow.status == 'finished':
                continue
            
            path = flow.path
            need_to_reroute = False
            
            if path == []:
                need_to_reroute = True
                
            elif flow.metadata.get('type', 'default') == 'request_response' and path[0] not in flow.source.network_access_points:
                need_to_reroute = True
            
            else:
                for i in range(len(path)-1):
                    if not self.has_edge(path[i], path[i+1]):
                        need_to_reroute = True
                        break
        
            if need_to_reroute:
                if flow.metadata.get('type', 'default') == 'request_response':
                    user = flow.source
                    connection_paths = []

                    # Checks all user access points to determine if the application is reachable.
                    for access_point in user.network_access_points:
                        if nx.has_path(G=self, source=access_point, target=flow.target):
                            new_path = nx.shortest_path(
                                G=self.model.topology,
                                source=access_point, 
                                target=flow.target,
                                weight='delay'
                                )
                            connection_paths.append(new_path)
                    
                    path = min(connection_paths, key=lambda p: len(p), default=[])
                
                elif nx.has_path(G=self, source=flow.source, target=flow.target):
                    path = nx.shortest_path(
                        G=self,
                        source=flow.source,
                        target=flow.target,
                        weight='delay'
                    )
                else:
                    path = []
                    
                if path == []:
                    flow.status = 'waiting'
                else:
                    flow.status = 'active'

                flow.last_path = flow.path 
                flow.path = path 

                # Cleanup flows from previous links
                for i in range(len(flow.last_path)-1):
                    link = self[flow.last_path[i]].get(flow.last_path[i+1])
                    if link is None:
                        continue
                    if flow in link['flows']:
                        link['flows'].remove(flow)

                flow.bandwidth = {}

                # Register flow on new links
                for i in range(len(path)-1):
                    link = self[flow.path[i]][flow.path[i+1]]
                    link['flows'].append(flow)
                    flow.bandwidth[link.id] = 0
                               
    def remove_invalid_connections(self) -> None:
        """Reevaluates link existence and removes edges exceeding range limits."""
        for satellite in Satellite.all():
            link_to_removed = []

            for neighbor in self[satellite]:
                link = self[satellite][neighbor]

                if isinstance(neighbor, ProcessUnit):
                    continue

                if not Topology.within_range(satellite, neighbor) or not satellite.active:
                    if link in NetworkLink.all():
                        NetworkLink.remove(link)
                    
                    link_to_removed.append((satellite, neighbor))
            
            for nodes in link_to_removed:
                self.remove_edge(nodes[0], nodes[1])

    def get_path_delay(self, path: List[Any]) -> float:
        """Calculates the total propagation delay of a given path.

        Args:
            path (list): List of nodes representing the path.

        Returns:
            float: Total delay including the initial wireless delay.
        """
        path_delay = nx.classes.function.path_weight(G=self, path=path, weight="delay")    
        path_delay += path[0].wireless_delay
        return path_delay

    def get_flow_delay(self, flow: Any) -> float:
        """Calculates the current delay of a specific network flow.

        Args:
            flow (NetworkFlow): The flow instance to evaluate.

        Returns:
            float: Calculated delay. Returns infinity if the flow is waiting.
        """
        if flow.status == 'waiting':
            path_delay = float('inf')
        else:
            path_delay = nx.classes.function.path_weight(G=self, path=flow.path, weight="delay")    
        
            if isinstance(flow.source, User):
                path_delay += flow.path[0].wireless_delay
        return path_delay
    
    @staticmethod               
    def within_range(object_1: Any, object_2: Any) -> bool:
        """Evaluates if the distance between two components is within communication range.

        Args:
            object_1 (object): First simulation component.
            object_2 (object): Second simulation component.

        Returns:
            bool: True if components are within the minimum range of the pair.
        """
        if object_1.coordinates is None or object_2.coordinates is None:
            return False
        
        distance_nodes = [object_1.max_connection_range, object_2.max_connection_range]
        ground_distance = geodesic(object_1.coordinates[:2], object_2.coordinates[:2]).kilometers 
        air_distance = (object_1.coordinates[2] - object_2.coordinates[2])/1000

        return min(distance_nodes) > math.sqrt(ground_distance**2 + air_distance**2)
    
    @staticmethod               
    def calculate_distance(object_1: Any, object_2: Any) -> float:
        """Calculates the 3D Euclidean distance between two components.

        Args:
            object_1 (object): First simulation component.
            object_2 (object): Second simulation component.

        Returns:
            float: Distance in kilometers. Returns infinity if coordinates are missing.
        """
        if object_1.coordinates is None or object_2.coordinates is None:
            return float('inf')
        
        ground_distance = geodesic(object_1.coordinates[:2], object_2.coordinates[:2]).kilometers 
        air_distance = (object_1.coordinates[2] - object_2.coordinates[2])/1000

        return math.sqrt(ground_distance**2 + air_distance**2)