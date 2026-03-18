# Simulator components
from ..component_manager import ComponentManager
from .network_link import NetworkLink
from .satellite import Satellite
from .user import User
from typing import List, Tuple, Optional, Dict, Any

class GroundStation(ComponentManager):
    """Represents a ground station providing wireless connectivity.

    Ground stations bridge the terrestrial network and the LEO (Low Earth Orbit) 
    satellite network. They provide connection points for both satellites 
    and terrestrial users. They are integrated into the simulation Topology 
    to manage link establishment.

    Attributes:
        _instances (list): List of all active GroundStation instances.
        _object_count (int): Counter for generating unique IDs.
        id (int): Unique identifier for the ground station.
        coordinates (tuple): Fixed geographical position (lat, lon, alt).
        wireless_delay (int): Inherent delay of the wireless interface.
        max_connection_range (int): Maximum distance for establishing a link.
        users (List[User]): List of users currently connected to this station.
    """

    _instances = []
    _object_count = 0
    
    def __init__(
        self,
        id: int = 0,
        coordinates: Optional[Tuple[float, float, float]] = None,
        wireless_delay: int = 0, 
        max_connection_range: int = 2000
    ) -> None:
        """Initializes a GroundStation instance.

        Args:
            id (int): Unique ID. If 0, it's automatically assigned.
            coordinates (tuple, optional): Fixed coordinates of the station.
            wireless_delay (int): Latency value for the wireless connection.
            max_connection_range (int): Range limit for wireless signals.
        """
        self.__class__._instances.append(self)
        self.__class__._object_count += 1
        
        if id == 0:
            id = self.__class__._object_count
        self.id = id
        
        # Ground station coordinates are stationary
        self.coordinates = coordinates
        
        # Values used for network link construction
        self.wireless_delay = wireless_delay
        self.max_connection_range = max_connection_range
        
        # Track currently associated users
        self.users: List[User] = []

    def export(self) -> Dict[str, Any]:
        """Generates a dictionary representation of the ground station state.

        Returns:
            dict: Serialized object data including user relationships 
                for persistence or logging.
        """
        component = {
            "id": self.id,
            "coordinates": self.coordinates,
            "wireless_delay": self.wireless_delay,
            "max_connection_range": self.max_connection_range,
            "relationships": {
                "users": [
                    {
                        "id": user.id,
                        "class": type(user).__name__
                    } for user in self.users
                ]
            }
        }
        return component

    def step(self) -> None:
        """Executes the ground station's logic for the current simulation tick.

        Manages satellite handovers and establishes connections with all 
        terrestrial users within range.
        """
        topology = self.model.topology
        
        # Handle orbital network connections
        self.connection_to_satellites()
          
        # Connect to all users within signal range
        self.users = []          
        for user in User.all():
            if topology.within_range(self, user):
                user.connect_to_access_point(self)

    def connection_to_satellites(self) -> None:
        """Establishes links with satellites acting as network gateways.

        Iterates through available satellites and creates a NetworkLink 
        if the satellite is within range and is configured as a gateway.
        """
        topology = self.model.topology
        
        for satellite in Satellite.all():
            if satellite.coordinates is None:
                # Skip if the satellite position is not currently updated
                continue
            
            # Check if satellite is within range and acts as a network access point
            if topology.within_range(self, satellite) and satellite.is_gateway:
                # Skip if the network link already exists
                if self.model.topology.has_edge(self, satellite):
                    continue
                
                # Instantiate and configure a new dynamic NetworkLink
                link = NetworkLink()
                
                link['topology'] = topology
                link['nodes'] = [satellite, self]
                link['bandwidth'] = NetworkLink.default_bandwidth
                link['delay'] = link.get_delay()
                link['type'] = 'dynamic'
                
                # Update the simulation topology with the new edge
                topology.add_edge(satellite, self)
                topology._adj[satellite][self] = link
                topology._adj[self][satellite] = link