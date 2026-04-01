from ..component_manager import ComponentManager
from geopy.distance import geodesic
from typing import Dict, Any, List, Tuple, Union

class NetworkLink(ComponentManager, dict):
    """Represents a network connection between two nodes in the topology.

    Since NetworkX stores edges as dictionaries, this class inherits from the 
    built-in dict class to maintain compatibility while providing additional 
    simulation logic and metric collection.

    Attributes:
        _instances (list): List of all active NetworkLink instances.
        _object_count (int): Counter for generating unique link IDs.
        default_bandwidth (int): Default bandwidth value in MB/s (100,000).
    """
    _instances = []
    _object_count = 0
    
    default_bandwidth = 100_000  # MB/s
    default_delay = 10 # ms
    _dynamic = False
    
    def __init__(
            self,
            id: int = 0
        ):
        """Initializes a NetworkLink instance with default edge attributes.

        Args:
            id (int): Unique identifier. If 0, an ID is automatically assigned.
        """
        
        self.__class__._instances.append(self)
        self.__class__._object_count += 1
        
        if id == 0: 
            id = self.__class__._object_count
        self["id"] = id
        self["topology"] = None
        self["nodes"] = []
        self["delay"] = 0
        self["bandwidth"] = 0
        self["flows"] = []
        self["active"] = True
        self['type'] = 'default'
         
    def collect_metrics(self) -> dict:
        """Collects the current state metrics of the network link.

        Returns:
            dict: Dictionary containing ID, node identifiers, delay, 
                activity status, bandwidth, and link type.
        """
        metrics = {
            "ID": self['id'],
            "Nodes": [str(node) for node in self['nodes']],
            "Delay": self['delay'],
            "Active": self['active'],
            "Bandwidth": self['bandwidth'],
            "Type": self['type']
        }
        
        return metrics  
     
    def export(self) -> dict: 
        """Generates a dictionary representation for saving the current context.

        Returns:
            dict: Serialized link data including relationships with topology, 
                active flows, and connected nodes.
        """ 
        component = {
            "id": self['id'],
            "delay": self['delay'],
            'active': self['active'],
            'bandwidth': self['bandwidth'],
            'type': self['type'],
            'relationships': {
                "topology": {"class": type(self.topology).__name__, "id": self.topology.id},
                "flows": [{"class": type(flow).__class__, "id": flow.id} for flow in self['flows']],
                "nodes": [{"class": type(node).__name__, "id": node.id} for node in self.nodes]
            }
        }
        
        return component 
        
    def get_delay(self) -> float:
        """Calculates propagation delay based on geographical distance.

        Args:
            
        Returns:
            float: Calculated delay in milliseconds.
        """
        # Latency (ms) ≈ Distance (km) / 300
        # 
        # 1 ms ≈ 300 km

        coord1 = self['nodes'][0].coordinates
        coord2 = self['nodes'][1].coordinates
        
        lat1 = coord1[0]
        lon1 = coord1[1]
        lat2 = coord2[0]
        lon2 = coord2[1]

        delay = geodesic((lat1,lon1), (lat2,lon2)).km / 300.0

        return delay
        
    def __getattr__(self, attribute_name: str):  
        """Provides access to dictionary keys via attribute notation.

        Args:
            attribute_name (str): Name of the attribute/key to retrieve.

        Returns:
            Any: Value associated with the key.

        Raises:
            AttributeError: If the key does not exist in the dictionary.
        """
        if attribute_name in self:
            return self[attribute_name]
        else:
            raise AttributeError(f"Object {self} has no such attribute '{attribute_name}'.")

    def __setattr__(self, attribute_name: str, value: object):
        """Allows setting dictionary keys via attribute notation.

        Args:
            attribute_name (str): Name of the attribute/key to set.
            value (object): Value to assign to the key.
        """
        self[attribute_name] = value
