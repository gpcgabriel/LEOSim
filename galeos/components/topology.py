from ..component_manager import ComponentManager
from .network_flow import NetworkFlow
from .network_link import NetworkLink
from .process_unit import ProcessUnit
from geopy.distance import geodesic
from .satellite import Satellite
from .user import User
import networkx as nx
import math

class Topology(ComponentManager, nx.Graph):
    _instances = []
    _object_count = 0

    def __init__(self, obj_id: int = 0, existing_graph: nx.Graph = None) -> object:
        self.__class__._instances.append(self)
        self.__class__._object_count += 1
        
        if id == 0:
            obj_id = self.__class__._object_count
        self.id = obj_id

        if existing_graph is None:
            nx.Graph.__init__(self)
        else:
            nx.Graph.__init__(self, incoming_graph_data=existing_graph)
         
    def step(self):
        """ Method that executes the object's events
        """
        self.remove_invalid_connections()
        self.model.topology_management_algorithm(topology=self, **self.model.topology_management_parameters)
        self.update_delay()
        self.reroute_flows()
        self.flow_schedule()

    def update_delay(self):
        for u, v, data in self.edges(data=True):
            link = data
            if isinstance(link, NetworkLink) and u.coordinates and v.coordinates:
                link['delay'] = NetworkLink.get_delay(u.coordinates, v.coordinates)

    def flow_schedule(self):
        pass
    
    def reroute_flows(self):
        """ Method that performs the routing of flows whose paths are now invalid
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

                    
                    # Checks all the user's access points and determines if access to the application is possible.
                    for access_point in user.network_access_points:
                        if nx.has_path(G=self, source=access_point, target=flow.target):
                            path = nx.shortest_path(
                                G=self.model.topology,
                                source=access_point, 
                                target=flow.target,
                                weight='delay'
                                )
                                
                            connection_paths.append(path)
                    
                    path = min(connection_paths, key=lambda path: len(path), default=[])
                

                elif nx.has_path(G=self, source=flow.source, target=flow.target):
                    path  = nx.shortest_path(
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

                for i in range(len(flow.last_path)-1):
                    link = self[flow.last_path[i]].get(flow.last_path[i+1])

                    if link is None:
                        continue
                    if flow in link['flows']:
                        link['flows'].remove(flow)

                flow.bandwidth = {}

                for i in range(len(path)-1):
                    link = self[flow.path[i]][flow.path[i+1]]

                    link['flows'].append(flow)
                    flow.bandwidth[link.id] = 0
                               
    def remove_invalid_connections(self):
        """ Method that reevaluates the existence of links, removing them if they are at a 
        greater distance than supported
        """
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

    def get_path_delay(self, path):
        path_delay = nx.classes.function.path_weight(G=self, path=path, weight="delay")    
        path_delay += path[0].wireless_delay

        return path_delay

    def get_flow_delay(self, flow) -> int:
        if flow.status == 'waiting':
            path_delay = float('inf')
        else:
            path_delay = nx.classes.function.path_weight(G=self, path=flow.path, weight="delay")    
        
            if isinstance(flow.source, User):
                path_delay += flow.path[0].wireless_delay
        return path_delay
    
    @staticmethod               
    def within_range(object_1 : object, object_2 : object):
        """ Method that evaluates whether the distance between two components is within the communication range.
            TODO : Need to develop verification to differentiate the range of different types of links
        """
        if object_1.coordinates is None or object_2.coordinates is None:
            return False
        
        distance_nodes = [object_1.max_connection_range, object_2.max_connection_range]
        ground_distance = geodesic(object_1.coordinates[:2], object_2.coordinates[:2]).kilometers 
        air_distance = (object_1.coordinates[2] - object_2.coordinates[2])/1000

        return min(distance_nodes) > math.sqrt(ground_distance**2 + air_distance**2)
    
    @staticmethod               
    def calculate_distance(object_1 : object, object_2 : object):
        """ Method that calculates the distance between two components.  
        """
        if object_1.coordinates is None or object_2.coordinates is None:
            return float('inf')
        
        ground_distance = geodesic(object_1.coordinates[:2], object_2.coordinates[:2]).kilometers 
        air_distance = (object_1.coordinates[2] - object_2.coordinates[2])/1000

        return math.sqrt(ground_distance**2 + air_distance**2)  