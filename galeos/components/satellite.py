# Simulator components
from ..component_manager import ComponentManager
from .user import User

class Satellite(ComponentManager):
    """ 
        Class representing satellites in the aerial part of the topology.
        They are capable of connecting to GroundStations, Users, or other Satellites.
        Additionally, they can be linked to a process unit to enable data processing.
    """
    _instances = []
    _object_count = 0
  
    def __init__(
            self, 
            id: int = 0,
            name: str = "",
            coordinates : tuple = None,
            wireless_delay : int = 0,
            max_connection_range : int = 300,
            is_gateway : bool = False
        ) -> object: 
        self.__class__._instances.append(self)
        self.__class__._object_count += 1
        
        if id == 0:
            id = self.__class__._object_count
        self.id = id

        self.name = name if name else str(self)

        self.process_unit = None
        self.active = True
        self.wireless_delay = wireless_delay
        self.is_gateway = is_gateway
        self.users = []
        self.max_connection_range = max_connection_range
        self.power = 0
        self.min_power = 0

        # Satellite coordinates
        self.coordinates = coordinates
        self.coordinates_trace = []
        
        # Satellite models
        self.mobility_model = None
        self.mobility_model_parameters = {}
        
        self.power_generation_model = None
        self.power_generation_model_parameters = {}
        
        self.power_consumption_model = None
        self.power_consumption_model_parameters = {}
        
        self.failure_model = None
        self.failure_occurred = False
        self.failure_model_parameters = {}
        
    def collect_metrics(self) -> dict:
        metrics = {
            "ID" : self.id,
            "Coordinates" : self.coordinates,
            "Power" : self.power,
            "Active" : self.active,
            "Is Gateway" : self.is_gateway
        }
        
        return metrics
    
    def step(self) -> None:
        # Prepares to check which users will be within range in the next step
        self.users = []

        # Activates the mobility model if necessary
        if len(self.coordinates_trace) <= self.model.scheduler.steps:
            self.mobility_model(self)
            
        # Updates the coordinates
        if self.coordinates != self.coordinates_trace[self.model.scheduler.steps]:
            self.coordinates = self.coordinates_trace[self.model.scheduler.steps]
        
        # Updates the coordinates of the attached ProcessUnit (if any)
        if self.process_unit:
            self.process_unit.coordinates = self.coordinates
            
        """ 
            If coordinates is None, it means the satellite is at a point where it cannot interact with other components.
            Therefore, if a process unit is linked to the satellite, it will be marked as unavailable.
        """
        if self.coordinates is None:
            self.active = False

            if self.process_unit:
                process_unit = self.process_unit
                process_unit.available = False
            return

        # If the other models are implemented, they will be activated
        if self.failure_model:
            self.failure_occurred = self.failure_model(self)

            if self.failure_occurred:
                self.active = False

                for user in User.all():
                    if self in user.network_access_points:
                        user.network_access_points.remove(self)

                if self.process_unit:
                    self.process_unit.available = False

                if self.model.topology.has_node(self):
                    for neighbor in list(self.model.topology.neighbors(self)):
                        self.model.topology.remove_edge(self, neighbor)
                return

            else:
                self.active = True
                if self.process_unit:
                    self.process_unit.available = True
        
        if self.power_generation_model:
            self.power_generation_model(self)
        
        if self.power_consumption_model:
            self.power_consumption_model(self)
        
        # If operational, the satellite will continue providing connection to users
        if self.active:
            for user in User.all():
                if self.model.topology.within_range(self, user):
                    user.connect_to_access_point(self)

    def export(self):
        """ Method that generates a representation of the object in dictionary format to save current context
        """  
        component = {
            "id" : self.id,
            "coordinates" : self.coordinates,
            "coordinates_trace" : self.coordinates_trace,
            "active" : self.active,
            "power" : self.power,
            "min_power" : self.min_power,
            "wireless_delay" : self.wireless_delay,
            "is_gateway" : self.is_gateway,
            "max_connection_range" : self.max_connection_range,
            "mobility_model_parameters" : self.mobility_model_parameters,
            "power_consumption_model_parameters" : self.power_consumption_model_parameters,
            "power_generate_model_parameters" : self.power_generation_model_parameters,
            "failure_model_parameters" : self.failure_model_parameters,
            "relationships" : {
                "mobility_model" : self.mobility_model.__name__ if self.mobility_model else None,
                "power_consumption_model" : self.power_consumption_model.__name__ if self.power_consumption_model else None,
                "power_generate_model" : self.power_generation_model.__name__ if self.power_generation_model else None,
                "failure_model_parameters" : self.failure_model.__name__ if self.failure_model else None,
                "process_unit" : {
                    "id" : self.process_unit.id,
                    "class" : type(self.process_unit).__name__
                } if self.process_unit else None,
            }
        }
        
        return component