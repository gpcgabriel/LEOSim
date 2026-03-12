# Simulator components
from .components import*
from .scheduler import*
import json

# Python modules
from typing import Callable
import json
import os
import datetime

class Simulator(ComponentManager):
    _instances = []
    _object_count = 0
    
    time_units = [
        "seconds",
        "minutes",
        "hours"
    ]
    
    def __init__(
        self,
        id : int = 0,
        stopping_criterion : Callable = None,
        resource_management_algorithm : Callable = None,
        resource_management_algorithm_parameters : dict = {},
        topology_management_algorithm : Callable = default_topology_management,
        topology_management_algorithm_parameters : dict = {},
        user_defined_functions : list = [],
        scheduler : Callable = Scheduler, 
        dump_interval : int = 100,
        logs_directory : str = "logs",
        ignore_list : list = [], 
        clean_data_in_memory : bool = False,
        tick_duration : int = 1,
        time_unit : str = 'seconds',
        scenario : str = 'hybrid',
        repetition : int = 1,
        topology_name : str = None
        ) -> object:
        # Method that creates the simulator
        
        self.__class__._instances.append(self)
        self.__class__._object_count += 1
        
        if id == 0:
            id = self.__class__._object_count
        self.id = id 
        
        self.stopping_criterion = stopping_criterion
        self.running = False
        
        self.resource_management_algorithm = resource_management_algorithm
        self.resource_management_algorithm_parameters = resource_management_algorithm_parameters

        self.resource_management_algorithm_parameters['scenario'] = scenario
        
        self.topology_management_algorithm = topology_management_algorithm
        self.topology_management_parameters = topology_management_algorithm_parameters
        
        self.scheduler = scheduler(self)
        self.topology = Topology()
        
        self.logs_directory = logs_directory
        self.dump_interval = dump_interval
        self.last_dump = 0
        self.clean_data_in_memory = clean_data_in_memory
        
        self.tick_duration = datetime.timedelta(**{time_unit : tick_duration}).total_seconds()
        
        self.agent_metrics = {}
        self.ignore_list = ignore_list
        
        for function in user_defined_functions:
            globals()[function.__name__] = function
        
        ComponentManager.model = self

        self.host_metrics = []
        self.scenario = scenario
        self.repetition = repetition
        self.topology_name = topology_name

    def initialize(self, dataset : str):
        for component_class in ComponentManager.__subclasses__():
            if component_class.__name__ != "Simulator":
                globals()[component_class.__name__].clear()
        
        with open(dataset, 'r', encoding='UTF-8') as file:
            dataset = json.load(file)
            
        created_components = []
        
        # Creates objects according to the dataset 
        for class_name, components in dataset.items():
            for component in components:
                obj = globals()[class_name]()
                
                obj.set_attributes(**component)
             
                obj.relationships = component["relationships"]
                
                created_components.append(obj)
                
        # Configures the relationships between objects 
        for obj in created_components:
            for key, value in obj.relationships.items():
                # If it's a function (e.g. mobility model, power consumption model)
                if type(value) == str and globals().get(value): 
                    setattr(obj, key, globals()[value])
                    
                # If it's as object of another class (e.g. applications)
                elif type(value) == dict and "class" in value and "id" in value: 
                    object_relation = globals()[value['class']].find_by("id", value['id'])
                    
                    setattr(obj, key, object_relation)
                   
                # If it is a dictionary and its values ​​are defined globally (e.g. application access dictionary)
                elif type(value) == dict and all(( globals().get(v) for v in value.values())): 
                    object_relation = {
                        k : globals().get(v) for k, v in value.items()
                    }
                    
                    setattr(obj, key, object_relation)


                # If it's a list of objects of another class
                elif type(value) == list and all(('id' in comp and 'class' in comp for comp in value)): 
                    components = [
                        globals()[component['class']].find_by('id', component['id']) for component in value 
                    ]

                    setattr(obj, key, components)

                elif value is None: 
                    setattr(obj, key, None)

        
        for agent in GroundStation.all() + Satellite.all() + ProcessUnit.all():
            self.topology.add_node(agent)
        
        for link in NetworkLink.all():            
            self.topology.add_edge(link["nodes"][0], link['nodes'][1])
            
            self.topology._adj[link["nodes"][0]][link["nodes"][1]] = link
            self.topology._adj[link["nodes"][1]][link["nodes"][0]] = link
                   
    def initialize_logs(self) -> None:
        os.makedirs(self.logs_directory, exist_ok=True)

        for component_class in ComponentManager.__subclasses__():
            if component_class not in self.ignore_list  + [self.__class__]:
                
                if component_class.__name__ not in self.agent_metrics:
                    self.agent_metrics[component_class.__name__] = []
                    
    def modelo_falha_programada(self, satellite):
        pass
         
    def step(self) -> None:
        # Updating satellite networks
        self.scheduler.step()

        self.topology_management_algorithm(topology=self.topology, **self.topology_management_parameters)

        self.resource_management_algorithm(self, self.resource_management_algorithm_parameters)
            
    def monitor(self) ->None:
        # Method that collects from components
        for component_class in ComponentManager.__subclasses__():
            if component_class not in self.ignore_list  + [self.__class__]:
                metrics = {'Step' : self.scheduler.steps,'metrics' : component_class.collect_class_metrics()}
                
                if metrics['metrics'] == []:
                    continue
                else:
                    self.agent_metrics[component_class.__name__].append(metrics)
        
        if self.scheduler.steps == self.last_dump + self.dump_interval:
            self.dump_data()
            self.last_dump = self.scheduler.steps
                                  
    def dump_data(self) -> None:
        if not os.path.exists(f"{self.logs_directory}/"):
            os.makedirs(f"{self.logs_directory}")  
        
        for agent_class, value in self.agent_metrics.items():
            filename = self.logs_directory + f"/{agent_class}.jsonl"

            with open(filename, mode="a", encoding="utf-8") as file:
                for metric in value:
                    file.write(json.dumps(metric) + "\n") 

            if self.clean_data_in_memory:
                self.agent_metrics[agent_class] = []
            
    def run(self) -> dict:
        # Execute the model
        
        for sat in Satellite.all():
            sat.failure_model = self.modelo_falha_programada

        self.running = True
        
        self.initialize_logs()
        
        self.monitor()
            
        while self.running:
            print("Step ", self.scheduler.steps+1)

            self.step()
            self.monitor()
            
            self.running = False if self.stopping_criterion(self) else True
            
        self.dump_data()
