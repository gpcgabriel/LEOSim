from ...component_manager import ComponentManager
from ..network_flow import NetworkFlow
from itertools import cycle
import networkx as nx

class DynamicDurationAccessModel(ComponentManager):
    _instances = []
    _object_count = 0
    
    def __init__(
            self,
            user: object = None,
            application: object = None,
            start: int = 1,
            duration_values: list = [],
            connection_duration_values: list = [],
            interval_values: list = [],
            connection_interval_values: list = []
        ):
        
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
        
    def export(self) -> dict:
        component = {
            "id" : self.id,
            "history" : self.history,
            "request_provisioning" : self.request_provisioning,
            "duration_values" : self.duration_values,
            "interval_values" : self.interval_values,
            "connection_duration_values" : self.connection_duration_values,
            "connection_interval_values" : self.connection_interval_values,
            "relationships" : {
                "user" : {'id' : self.user.id, 'class' : type(self.user).__name__} if self.user else None,
                "application" : {"id" : self.application.id, "class" : type(self.application).__name__} if self.application else None,
                "flow" : {"id" : self.flow.id, "class" : type(self.flow).__name__} if self.flow else None,
            }
        }
        
        return component
        
    def get_next_access(self, start):
        # Inicialização dos geradores
        if not hasattr(self, 'duration_generator'):
            setattr(self, 'duration_generator', cycle(self.duration_values))
            
        if not hasattr(self ,'connection_duration_generator'):
            setattr(self, 'connection_duration_generator', cycle(self.connection_duration_values))
        
        if not hasattr(self,'interval_generator'):
            setattr(self, 'interval_generator', cycle(self.interval_values))
            
        if not hasattr(self, 'connection_interval_generator'):
            setattr(self, 'connection_interval_generator', cycle(self.connection_interval_values))
            
        # Obtenção dos valores
        interval = next(self.interval_generator)
        duration = next(self.duration_generator)
        
        connection_duration = next(self.connection_duration_generator)
        connection_interval = next(self.connection_interval_generator)
        
        making_request_times = {}
        request_time = start
        
        # Define o limite absoluto de término
        end_time = start + duration
        
        while request_time < end_time:
            # CORREÇÃO: Calcula o tempo restante real
            time_remaining = end_time - request_time
            
            # O tempo da rajada é o menor valor entre a duração da conexão e o tempo restante
            time = min(connection_duration, time_remaining)
            
            for i in range(time):
                making_request_times[str(i + request_time)] = True
                                
            request_time += time + connection_interval
            
            connection_duration = next(self.connection_duration_generator)
            connection_interval = next(self.connection_interval_generator)
            
        self.history.append({
            'start': start,
            'provisioned_time': 0,
            'is_provisioned' : False,
            'required_provisioning_time' : duration,
            'end' : None, # Diferença específica do DynamicModel
            'waiting_provisioning': 0,
            'access_time': 0,
            'connection_failure_time': 0,
            'making_request': making_request_times,
            'next_access' : end_time + interval,
        })   
    
    def update_access(self) -> None:
        user = self.user
        app = self.application    
        current_access = self.history[-1] 
        
        if current_access['making_request'].get(str(self.model.scheduler.steps)):
            if self.flow is not None:
                if self.flow.target != app.process_unit:
                    if not self.flow is None:
                        self.flow.status = 'finished'
                        self.flow = None

            if app.process_unit is None:
                return
                        
            if self.flow is None:
                
                connection_paths = []
                
                for access_point in user.network_access_points:
                    if nx.has_path(G=self.model.topology, source=access_point, target=app.process_unit):
                        path = nx.shortest_path(
                            G=self.model.topology,
                            source=access_point, 
                            target=app.process_unit,
                            weight='delay'
                        )
                                
                        connection_paths.append(path)
                    
                path = min(connection_paths, key=lambda path: len(path), default=[])
          
                flow = NetworkFlow(
                    start=self.model.scheduler.steps + 1,
                    source=user,
                    target=app.process_unit,
                    path=path,
                    data_to_transfer=current_access.get('data_to_transfer', 1),
                    metadata={'type' : 'request_response', 'user' : user}
                )
                self.flow = flow

        if current_access['provisioned_time'] - 1 == current_access['required_provisioning_time'] and app.available:
            current_access['end'] = self.model.scheduler.steps + 1