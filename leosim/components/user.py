from ..component_manager import ComponentManager
from typing import List, Dict, Any, Optional, Tuple, Callable

class User(ComponentManager):
    """Represents a network user within the simulation.

    A User can own multiple applications, move according to a mobility model, 
    and connect to various network access points (Ground Stations or Satellites). 
    It tracks application access patterns, including provisioning requests 
    and connectivity metrics.

    Attributes:
        _instances (list): List of all active User instances.
        _object_count (int): Counter for generating unique identifiers.
        id (int): Unique identifier for the user.
        applications (list): List of applications belonging to the user.
        coordinates (tuple): Current geographical position (lat, lon, alt).
        coordinates_trace (list): Pre-calculated movement path.
        mobility_model (callable): Function defining user movement.
        mobility_model_parameters (dict): Parameters for the mobility model.
        applications_access_models (list): Models defining how the user 
            interacts with their applications.
        network_access_points (list): Access points currently within range.
        max_connection_range (int): Maximum signal reach for the user.
    """
    _instances = []
    _object_count = 0
    
    def __init__(
            self,
            id: int = 0,
            coordinates: Optional[Tuple[float, float, float]] = None,
            max_connection_range: int = 300
        ) -> None:
        """Initializes a User instance.

        Args:
            id (int): Unique ID. If 0, it is automatically assigned.
            coordinates (tuple, optional): Initial position coordinates.
            max_connection_range (int): Signal range limit in kilometers.
        """
        
        # Adding the object to the instance list
        self.__class__._instances.append(self) 
        self.__class__._object_count += 1
        
        if id == 0:
            id = self.__class__._object_count
        self.id = id
        
        # User applications
        self.applications = []
        
        # User coordinates
        self.coordinates = coordinates
        self.coordinates_trace = []
        
        # User mobility model
        self.mobility_model = None
        self.mobility_model_parameters = {}
        
        # User application access model
        self.applications_access_models = []
        
        self.network_access_points = []

        self.max_connection_range = max_connection_range
    
    def step(self) -> None:
        """Executes user logic for the current simulation tick.

        Updates application access states (provisioning, active flows, 
        waiting times) and moves the user according to the mobility trace.
        """
        for access_model in self.applications_access_models:
            app = access_model.application    
            current_access = access_model.history[-1] 

            # If the application requests provisioning, update the metrics.   
            if access_model.request_provisioning:
                if app.available:
                    current_access['is_provisioned'] = True
                    current_access['provisioned_time'] += 1

                    if current_access['making_request'].get(str(access_model.model.scheduler.steps)):

                        if access_model.flow and access_model.flow.status == 'active':
                            current_access['access_time'] += 1

                        else:
                            current_access['connection_failure_time'] += 1
                else:                    
                    current_access['is_provisioned'] = False
                    current_access['waiting_provisioning'] += 1

            elif access_model.flow is not None:
                access_model.flow.status = 'finished'
                access_model.flow.end = access_model.model.scheduler.steps

                access_model.flow = None

            # Sets the flag value according to the model
            if current_access['start'] == access_model.model.scheduler.steps + 1:
                access_model.request_provisioning = True

            elif current_access['end'] == access_model.model.scheduler.steps + 1:
                access_model.request_provisioning = False

                if access_model.flow is not None:
                    access_model.flow.status = "finished"

                access_model.flow = None

                # Gets the next access according to the model since the current one has ended.
                access_model.get_next_access(current_access['next_access'])
                
        # Mobility update
        if len(self.coordinates_trace) <= self.model.scheduler.steps:
            self.mobility_model(self)
            
        if self.coordinates != self.coordinates_trace[self.model.scheduler.steps]:
            self.coordinates = self.coordinates_trace[self.model.scheduler.steps]
                            
        self.network_access_points = []
                
    def collect_metrics(self) -> Dict[str, Any]:
        """Collects telemetry data from the user and their application accesses.

        Returns:
            dict: Contains user ID, coordinates, access details for each 
                application access model, and current access points.
        """     
        topology = ComponentManager.model.topology
        
        accesses = []
        
        for access_model in self.applications_access_models:
            last_access = access_model.history[-1].copy()
            making_request = last_access['making_request'].get(str(self.model.scheduler.steps), False)

            last_access.pop('making_request')
            flow = access_model.flow
            
            delay = float('inf') 

            if flow and flow.status != 'waiting':
                delay = topology.get_path_delay(flow.path)
                delay += flow.path[0].wireless_delay
            
            accesses.append({
                "Application ID" : access_model.application.id,
                "Request Provisioning" : access_model.request_provisioning,
                "Is Provisioned" : last_access['is_provisioned'],
                "Provisioning" : access_model.application._available,
                "Making Request" : making_request,
                "Connectivity" :  True if access_model.flow and access_model.flow.path != [] else False,
                "Path" : [str(node) for node in access_model.flow.path] if access_model.flow else [], 
                "Delay" : delay
            })
        
        metrics = {
            "ID" : self.id,
            "Coordinates" : self.coordinates,
            "Access to Applications" : accesses,
            "Network Access Points" : [ str(access_point) for access_point in self.network_access_points]
        }    
        
        return metrics  
                       
    def export(self) -> Dict[str, Any]:
        """Generates a dictionary representation of the user for context saving.

        Returns:
            dict: Serialized user state including model parameters and 
                object relationships.
        """
        attributes = {
            "id" : self.id,
            "coordinates" : self.coordinates,
            "coordinates_trace" : self.coordinates_trace,
            "mobility_model_parameters" : self.mobility_model_parameters ,
            "relationships" : {
                "mobility_model" : self.mobility_model.__name__ if self.mobility_model else None,
                "applications_access_models" : [{"class" : type(access_model).__name__, 'id' : access_model.id} for access_model in self.applications_access_models],
                "applications" : [{"class" : type(app).__name__, 'id' : app.id} for app in self.applications] 
            }
        }

        return attributes
        
    def set_mobility_model(self, model: Callable, parameters: Dict[str, Any]) -> None:
        """Assigns a mobility model to the user.

        Args:
            model (callable): Function that updates coordinates_trace.
            parameters (dict): Configuration for the mobility model.
        """
        self.mobility_model = model
        self.mobility_model_parameters = parameters
             
    def connection_to_application(self, application: Any, access_model: Any) -> None:
        """Links the user to an application through an access model.

        Args:
            application (object): The application instance to be accessed.
            access_model (object): The model defining access frequency/behavior.
        """
        access_model.application = application
        access_model.user = self
        
        application.user = self
        
        self.applications_access_models.append(access_model)

    def connect_to_access_point(self, access_point: Any) -> None:
        """Registers a connection with a network access point.

        Args:
            access_point (object): The Station or Satellite within range.
        """
        self.network_access_points.append(access_point)
        access_point.users.append(self)