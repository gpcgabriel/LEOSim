from ..component_manager import ComponentManager

class ProcessUnit(ComponentManager):
    """ 
        Class that represents an infrastructure component with any computational capabilities (e.g. datacenters, edge servers).
        Additionally, it interacts with other components through the Topology component, which means a ProcessUnit must be properly
        integrated into the topology structure.
    """
    _instances = []
    _object_count = 0
   
    def __init__(
            self,
            id : int = 0,
            cpu : int = 0,
            memory : int = 0,
            storage : int = 0,
            coordinates : tuple = None,
            model_name : str = "",
            architecture : dict = {}
        ):     
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
        """ 
            Method that collects data from a specific instance
            Can be modified for customized data collection
        """
        metrics = {
            "ID" : self.id,
            "Coordinates" : self.coordinates,
            "CPU" : self.cpu,
            "Memory" : self.memory,
            "Storage" : self.storage,
            "CPU Demand" : self.cpu_demand,
            "Memory Demand" : self.memory_demand,
            "Storage Demand" : self.storage_demand,
            "Power" : self.power,
            "Available" : self.available,
            "Architecture" : self.architecture
        }
        
        return metrics
    
    def step(self):
        # Method responsible for activating the component and ensuring its correct operation throughout the simulation
        
        # Updates the status of applications already allocated and which became unavailable for various reasons
        for app in self.applications:
            if app.process_unit and not app.process_unit.available:
                app.available = False
                app.deprovision()
      
    def export(self) -> dict:
        """ Method that generates a representation of the object in dictionary format to save current context
        """
        component = {
            "id" : self.id,
            "cpu" : self.cpu,
            "memory" : self.memory,
            "storage" : self.storage,
            "power" : self.power,
            "model_name" : self.model_name,
            "architecture" : self.architecture,
            "coordinates" : self.coordinates,
            "available" : self.available,
            "power_generation_model_parameters" : self.power_generation_model_parameters,
            "power_consumption_model_parameters" :self.power_consumption_model_parameters,
            "relationships" :{
                "power_generation_model" : self.power_generation_model.__name__ if self.power_generation_model else None,
                "power_consumption_model" : self.power_consumption_model.__name__ if self.power_consumption_model else None,
                "failure_model" : self.failure_model.__name__ if self.failure_model else None,
                "applications" : [
                    {
                        "class" : type(app).__name__,
                        "id" : app.id
                    } for app in self.applications
                ]
                
            }
        } 
        
        return component
    
    def has_capacity_to_host(self, application : object) -> None:
        """ Method that checks whether there are enough available resources to host an application
        """
        cpu_demand = self.cpu_demand + application.cpu_demand
        memory_demand = self.memory_demand + application.memory_demand
        storage_demand = self.storage_demand + application.storage_demand
        
        return self.cpu >= cpu_demand and self.memory >= memory_demand and self.storage >= storage_demand