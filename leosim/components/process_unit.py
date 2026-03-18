from ..component_manager import ComponentManager
from typing import List, Dict, Any, Optional, Tuple

class ProcessUnit(ComponentManager):
    """Represents an infrastructure component with computational capabilities.

    This class models hardware such as datacenters or edge servers. It 
    interacts with other elements through the Topology component, 
    requiring proper integration into the simulation's network structure.

    Attributes:
        _instances (list): List of all active ProcessUnit instances.
        _object_count (int): Counter for generating unique identifiers.
        id (int): Unique identifier for the process unit.
        model_name (str): Name or label of the hardware model.
        coordinates (tuple): Geographical position (lat, lon, alt).
        cpu (int): Total CPU capacity.
        memory (int): Total RAM capacity.
        storage (int): Total storage capacity.
        power (float): Current power state or generation.
        cpu_demand (int): Currently allocated CPU resources.
        memory_demand (int): Currently allocated RAM resources.
        storage_demand (int): Currently allocated storage resources.
        architecture (dict): Hardware architectural specifications.
        applications (List[object]): Applications currently hosted on this unit.
        available (bool): Status indicating if the unit is functional.
    """
    _instances = []
    _object_count = 0
   
    def __init__(
            self,
            id: int = 0,
            cpu: int = 0,
            memory: int = 0,
            storage: int = 0,
            coordinates: Optional[Tuple[float, float, float]] = None,
            model_name: str = "",
            architecture: Dict[str, Any] = {}
        ):
        """Initializes a ProcessUnit instance.

        Args:
            id (int): Unique ID. If 0, it is automatically assigned.
            cpu (int): CPU capacity units.
            memory (int): Memory capacity units.
            storage (int): Storage capacity units.
            coordinates (tuple, optional): Latitude, longitude, and altitude.
            model_name (str): Label for the hardware model.
            architecture (dict): Specific hardware architectural demands.
        """     
        self.__class__._instances.append(self)
        self.__class__._object_count += 1
        
        if id == 0:
            id = self.__class__._object_count
        self.id = id 
        
        self.model_name = model_name
        self.coordinates = coordinates
        
        # Total computational capacity
        self.cpu = cpu
        self.memory = memory
        self.storage = storage
        self.power = 0
        
        # Current demands
        self.cpu_demand = 0
        self.memory_demand = 0
        self.storage_demand = 0
        
        # Architectural specifications
        self.architecture = architecture
        
        # Possible integration with relevant models
        self.power_generation_model = None
        self.power_generation_model_parameters = {}
        
        self.power_consumption_model = None
        self.power_consumption_model_parameters = {}
        
        self.failure_model = None
        self.failure_model_parameters = {}
        
        # Applications currently allocated in the unit
        self.applications = []
                
        # Process Unit availability status
        self.available = True

    def collect_metrics(self) -> dict:
        """Collects telemetry data from the specific process unit instance.

        Returns:
            dict: Current resource capacity, demands, and operational status.
        """
        metrics = {
            "ID": self.id,
            "Coordinates": self.coordinates,
            "CPU": self.cpu,
            "Memory": self.memory,
            "Storage": self.storage,
            "CPU Demand": self.cpu_demand,
            "Memory Demand": self.memory_demand,
            "Storage Demand": self.storage_demand,
            "Power": self.power,
            "Available": self.available,
            "Architecture": self.architecture
        }
        
        return metrics
    
    def step(self) -> None:
        """Activates the component and ensures its operation during the simulation.

        Updates the status of allocated applications. If the unit becomes 
        unavailable, hosted applications are deprovisioned.
        """
        # Updates the status of applications already allocated and which became 
        # unavailable for various reasons
        for app in self.applications:
            if app.process_unit and not app.process_unit.available:
                app.available = False
                app.deprovision()
      
    def export(self) -> dict:
        """Generates a dictionary representation for saving the current context.

        Returns:
            dict: Serialized object state including hardware specs and 
                application relationships.
        """
        component = {
            "id": self.id,
            "cpu": self.cpu,
            "memory": self.memory,
            "storage": self.storage,
            "power": self.power,
            "model_name": self.model_name,
            "architecture": self.architecture,
            "coordinates": self.coordinates,
            "available": self.available,
            "power_generation_model_parameters": self.power_generation_model_parameters,
            "power_consumption_model_parameters": self.power_consumption_model_parameters,
            "relationships": {
                "power_generation_model": self.power_generation_model.__name__ if self.power_generation_model else None,
                "power_consumption_model": self.power_consumption_model.__name__ if self.power_consumption_model else None,
                "failure_model": self.failure_model.__name__ if self.failure_model else None,
                "applications": [
                    {
                        "class": type(app).__name__,
                        "id": app.id
                    } for app in self.applications
                ]
            }
        } 
        
        return component
    
    def has_capacity_to_host(self, application: object) -> bool:
        """Checks if there are enough available resources to host an application.

        Args:
            application (object): The application instance requesting resources.

        Returns:
            bool: True if CPU, memory, and storage demands can be met.
        """
        cpu_demand = self.cpu_demand + application.cpu_demand
        memory_demand = self.memory_demand + application.memory_demand
        storage_demand = self.storage_demand + application.storage_demand
        
        return self.cpu >= cpu_demand and self.memory >= memory_demand and self.storage >= storage_demand