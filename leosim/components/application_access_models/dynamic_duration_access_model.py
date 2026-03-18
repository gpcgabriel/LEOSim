from ...component_manager import ComponentManager
from ..network_flow import NetworkFlow
from itertools import cycle
import networkx as nx
from typing import List, Dict, Any, Optional

class DynamicDurationAccessModel(ComponentManager):
    """Models how a User accesses an application over time with elastic duration.

    This model defines patterns of provisioning requests where the end of the 
    access is dynamic, occurring only after the required provisioning time 
    has been effectively met, regardless of simulation clock elapsed.

    Attributes:
        _instances (list): List of all active model instances.
        _object_count (int): Counter for generating unique identifiers.
        id (int): Unique identifier for the access model.
        duration_values (list): Cycle of total required provisioning durations.
        interval_values (list): Cycle of idle intervals between accesses.
        connection_duration_values (list): Cycle of active request bursts.
        connection_interval_values (list): Cycle of idle times between bursts.
        history (list): Log of access events, metrics, and elastic timing.
        request_provisioning (bool): Flag for active provisioning intent.
        flow (NetworkFlow): The current network flow for this access.
        user (object): The User instance performing the access.
        application (object): The Application instance being accessed.
    """
    _instances = []
    _object_count = 0
    
    def __init__(
            self,
            user: Optional[Any] = None,
            application: Optional[Any] = None,
            start: int = 1,
            duration_values: List[int] = [],
            connection_duration_values: List[int] = [],
            interval_values: List[int] = [],
            connection_interval_values: List[int] = []
        ) -> None:
        """Initializes a DynamicDurationAccessModel instance."""
        self.__class__._instances.append(self)
        self.__class__._object_count += 1

        self.id = self.__class__._object_count
        
        self.duration_values = duration_values
        self.interval_values = interval_values
        self.connection_duration_values = connection_duration_values
        self.connection_interval_values = connection_interval_values
        
        self.history = []
        self.request_provisioning = False
        self.flow = None
        
        self.user = user
        self.application = application

        if application and user:
            self.get_next_access(start)
        
    def export(self) -> Dict[str, Any]:
        """Generates a dictionary representation for context saving."""
        component = {
            "id": self.id,
            "history": self.history,
            "request_provisioning": self.request_provisioning,
            "duration_values": self.duration_values,
            "interval_values": self.interval_values,
            "connection_duration_values": self.connection_duration_values,
            "connection_interval_values": self.connection_interval_values,
            "relationships": {
                "user": {'id': self.user.id, 'class': type(self.user).__name__} if self.user else None,
                "application": {"id": self.application.id, "class": type(self.application).__name__} if self.application else None,
                "flow": {"id": self.flow.id, "class": type(self.flow).__name__} if self.flow else None,
            }
        }
        return component
        
    def get_next_access(self, start: int) -> None:
        """Calculates the burst sequence for the next elastic access window."""
        if not hasattr(self, 'duration_generator'):
            setattr(self, 'duration_generator', cycle(self.duration_values))
            
        if not hasattr(self, 'connection_duration_generator'):
            setattr(self, 'connection_duration_generator', cycle(self.connection_duration_values))
        
        if not hasattr(self, 'interval_generator'):
            setattr(self, 'interval_generator', cycle(self.interval_values))
            
        if not hasattr(self, 'connection_interval_generator'):
            setattr(self, 'connection_interval_generator', cycle(self.connection_interval_values))
            
        interval = next(self.interval_generator)
        duration = next(self.duration_generator)
        
        connection_duration = next(self.connection_duration_generator)
        connection_interval = next(self.connection_interval_generator)
        
        making_request_times = {}
        request_time = start
        end_time = start + duration
        
        while request_time < end_time:
            time_remaining = end_time - request_time
            time = min(connection_duration, time_remaining)
            
            for i in range(time):
                making_request_times[str(i + request_time)] = True
                                
            request_time += time + connection_interval
            connection_duration = next(self.connection_duration_generator)
            connection_interval = next(self.connection_interval_generator)
            
        self.history.append({
            'start': start,
            'provisioned_time': 0,
            'is_provisioned': False,
            'required_provisioning_time': duration,
            'end': None, # Remains None until requirements are met
            'waiting_provisioning': 0,
            'access_time': 0,
            'connection_failure_time': 0,
            'making_request': making_request_times,
            'next_access': end_time + interval,
        })   
    
    def update_access(self) -> None:
        """Updates the flow based on current demand and sets elastic end time."""
        user = self.user
        app = self.application    
        current_access = self.history[-1] 
        
        if current_access['making_request'].get(str(self.model.scheduler.steps)):
            if self.flow is not None and self.flow.target != app.process_unit:
                self.flow.status = 'finished'
                self.flow = None

            if app.process_unit is None:
                return
                        
            if self.flow is None:
                connection_paths = []
                for access_point in user.network_access_points:
                    if nx.has_path(G=self.model.topology, source=access_point, target=app.process_unit):
                        path = nx.shortest_path(
                            G=self.model.topology, source=access_point, 
                            target=app.process_unit, weight='delay'
                        )
                        connection_paths.append(path)
                    
                path = min(connection_paths, key=lambda p: len(p), default=[])
                self.flow = NetworkFlow(
                    start=self.model.scheduler.steps + 1,
                    source=user, target=app.process_unit, path=path,
                    data_to_transfer=current_access.get('data_to_transfer', 1),
                    metadata={'type': 'request_response', 'user': user}
                )

        # Elastic closure: end is set only when provisioning quota is reached
        if current_access['provisioned_time'] - 1 == current_access['required_provisioning_time'] and app.available:
            current_access['end'] = self.model.scheduler.steps + 1