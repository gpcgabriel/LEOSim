from ..component_manager import ComponentManager
from .network_link import NetworkLink
from .satellite import Satellite
from .user import User

class GroundStation(ComponentManager):
    """ 
        Class that represents ground stations capable of providing wireless connection, both to satellites and to terrestrial users.
        It is responsible for connecting the terrestrial network and the LEO satellite network.
        Additionally, it plays a direct role in the Topology component, requiring GroundStation components to be added to the
        Topology structure to ensure the simulator works properly.
    """
    _instances = []
    _object_count = 0
    
    def __init__(
            self,
            id : int = 0,
            coordinates : tuple = None,
            wireless_delay : int = 0, 
            max_connection_range : int = 2000
        ):
        
        self.__class__._instances.append(self)
        self.__class__._object_count += 1
        
        if id == 0:
            id = self.__class__._object_count
        self.id = id
        
        # Its coordinates are fixed
        self.coordinates = coordinates
        
        self.wireless_delay = wireless_delay
        self.max_connection_range = max_connection_range
        
        # List of currently connected users
        self.users = []

    def export(self):
        """ Method that generates a representation of the object in dictionary format to save current context
        """
        component = {
            "id" : self.id,
            "coordinates" : self.coordinates,
            "wireless_delay" : self.wireless_delay,
            "max_connection_range" : self.max_connection_range,
            "relationships" : {
                "users" : [
                    {
                        "id" : user.id,
                        "class" : type(user).__name__
                    } for user in self.users
                ]
            }
        }
        
        return component

    def step(self):
        """ Method responsible for activating the component and ensuring its correct operation throughout the simulation
        """
        topology = self.model.topology
        
        self.connection_to_satellites()
          
        self.users = []          
        for user in User.all():
            if topology.within_range(self, user):
                user.connect_to_access_point(self)

    def connection_to_satellites(self):
        """ Method that establishes connection between this component and satellites within range that can act as gateways to the LEO network
        """
        topology = self.model.topology
        
        for satellite in Satellite.all():
            if satellite.coordinates is None:
                # Satellite is not currently represented
                continue
            
            if topology.within_range(self, satellite) and satellite.is_gateway:
                if self.model.topology.has_edge(self, satellite):
                    continue
                
                # Create a new Link object
                link = NetworkLink()
                
                link['topology'] = topology
                link['nodes'] = [satellite, self]
                link['bandwidth'] = NetworkLink.default_bandwidth
                link['delay'] = NetworkLink.get_delay(satellite.coordinates, self.coordinates)
                link['type'] = 'dynamic'
                
                topology.add_edge(satellite, self)
        
                topology._adj[satellite][self] = link
                topology._adj[self][satellite] = link