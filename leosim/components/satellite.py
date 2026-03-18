# Simulator components
from ..component_manager import ComponentManager
from .user import User
from typing import List, Dict, Any, Optional, Tuple

class Satellite(ComponentManager):
    """Represents a satellite in the aerial segment of the topology.

    Satellites facilitate connectivity between GroundStations, Users, and other 
    Satellites. They can be associated with a ProcessUnit for data processing 
    and support dynamic mobility, power, and failure models.

    Attributes:
        _instances (list): List of all active Satellite instances.
        _object_count (int): Counter for generating unique identifiers.
        id (int): Unique identifier for the satellite.
        name (str): Satellite name or label.
        coordinates (tuple): Geographical position (lat, lon, alt).
        wireless_delay (int): Latency inherent to the wireless interface.
        max_connection_range (int): Maximum signal reach in kilometers.
        is_gateway (bool): Whether the satellite acts as an orbital gateway.
        process_unit (object): Attached computational unit for processing.
        active (bool): Operational status of the satellite.
        users (List[User]): Users currently within range or connected.
        power (float): Current energy level.
        min_power (float): Minimum energy threshold for operation.
        coordinates_trace (list): List of pre-calculated positions over time.
    """
    _instances = []
    _object_count = 0
  
    def __init__(
            self, 
            id: int = 0,
            name: str = "",
            coordinates: Optional[Tuple[float, float, float]] = None,
            wireless_delay: int = 0,
            max_connection_range: int = 300,
            is_gateway: bool = False,
        ) -> None: 
        """Initializes a Satellite instance.

        Args:
            id (int): Unique ID. If 0, it is automatically assigned.
            name (str): Label for the satellite.
            coordinates (tuple, optional): Initial position coordinates.
            wireless_delay (int): Wireless communication latency.
            max_connection_range (int): Signal range limit.
            is_gateway (bool): Gateway capability flag.
        """
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
        
    def collect_metrics(self) -> Dict[str, Any]:
        """Collects operational metrics from the satellite.

        Returns:
            dict: Current ID, coordinates, power, activity status, 
                gateway status, and failure status.
        """
        metrics = {
            "ID": self.id,
            "Coordinates": self.coordinates,
            "Power": self.power,
            "Active": self.active,
            "Is Gateway": self.is_gateway,
            "Status": "Available" if not self.failure_occurred else "Failure" 
        }
        
        return metrics
    
    def step(self) -> None:
        """Executes the satellite's logic for the current simulation step.

        Updates mobility, manages attached ProcessUnit status, evaluates 
        failure/power models, and handles user connections.
        """
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
            
        # If coordinates is None, the satellite cannot interact with other components.
        # Therefore, any linked process unit will be marked as unavailable.
        if self.coordinates is None:
            self.active = False

            if self.process_unit:
                process_unit = self.process_unit
                process_unit.available = False
            return

        # Execute failure model if implemented
        if self.failure_model:
            self.failure_occurred = self.failure_model(self)

            if self.failure_occurred:
                self.active = False

                # Remove users from the current list
                for user in User.all():
                    if self in user.network_access_points:
                        user.network_access_points.remove(self)

                # Set ProcessUnit as unavailable
                if self.process_unit:
                    self.process_unit.available = False

                # Remove existing network connections
                if self.model.topology.has_node(self):
                    for neighbor in list(self.model.topology.neighbors(self)):
                        self.model.topology.remove_edge(self, neighbor)
                return

            else:
                self.active = True
                if self.process_unit:
                    self.process_unit.available = True
        
        # Trigger power models if present
        if self.power_generation_model:
            self.power_generation_model(self)
        
        if self.power_consumption_model:
            self.power_consumption_model(self)
        
        # If operational, provide connections to users within range
        if self.active:
            for user in User.all():
                if self.model.topology.within_range(self, user):
                    user.connect_to_access_point(self)

    def export(self) -> Dict[str, Any]:
        """Generates a dictionary representation of the object for context saving.

        Returns:
            dict: Serialized state including coordinates, power levels, 
                model parameters, and object relationships.
        """  
        component = {
            "id": self.id,
            "coordinates": self.coordinates,
            "coordinates_trace": self.coordinates_trace,
            "active": self.active,
            "power": self.power,
            "min_power": self.min_power,
            "wireless_delay": self.wireless_delay,
            "is_gateway": self.is_gateway,
            "max_connection_range": self.max_connection_range,
            "mobility_model_parameters": self.mobility_model_parameters,
            "power_consumption_model_parameters": self.power_consumption_model_parameters,
            "power_generate_model_parameters": self.power_generation_model_parameters,
            "failure_model_parameters": self.failure_model_parameters,
            "relationships": {
                "mobility_model": self.mobility_model.__name__ if self.mobility_model else None,
                "power_consumption_model": self.power_consumption_model.__name__ if self.power_consumption_model else None,
                "power_generate_model": self.power_generation_model.__name__ if self.power_generation_model else None,
                "failure_model": self.failure_model.__name__ if self.failure_model else None,
                "process_unit": {
                    "id": self.process_unit.id,
                    "class": type(self.process_unit).__name__
                } if self.process_unit else None,
            }
        }
        
        return component