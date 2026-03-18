# Simulator components
import json
import random
import os
import datetime
from typing import Callable, List, Dict, Any, Optional

from .components import *
from .scheduler import *

class Simulator(ComponentManager):
    """Orchestrates the internal operations of the simulation tool.

    This class manages agent scheduling, initialization, data collection, 
    and storage processes. It acts as the central controller for the 
    simulation lifecycle.

    Attributes:
        _instances (list): List of active Simulator instances.
        _object_count (int): Counter for the number of created objects.
        time_units (list): Supported time units for conversion.
    """

    _instances = []
    _object_count = 0
    
    time_units = ["seconds", "minutes", "hours"]
    
    def __init__(
        self,
        id: int = 0,
        stopping_criterion: Optional[Callable] = None,
        resource_management_algorithm: Optional[Callable] = None,
        resource_management_algorithm_parameters: Dict[str, Any] = {},
        topology_management_algorithm: Callable = default_topology_management,
        topology_management_algorithm_parameters: Dict[str, Any] = {},
        user_defined_functions: List[Callable] = [],
        scheduler: Callable = Scheduler, 
        dump_interval: int = 100,
        logs_directory: str = "logs",
        ignore_list: List[Any] = [], 
        clean_data_in_memory: bool = False,
        tick_duration: int = 1,
        time_unit: str = 'seconds',
        scenario: str = 'hybrid',
        repetition: int = 1,
        topology_name: Optional[str] = None
    ) -> None:
        """Initializes a new Simulator instance.

        Args:
            id (int): Unique identifier for the simulator. Defaults to 0.
            stopping_criterion (Callable): Binary function that returns True 
                when the simulation should terminate.
            resource_management_algorithm (Callable): Function implementing 
                provisioning and migration policies.
            resource_management_algorithm_parameters (dict): Parameters 
                passed to the resource management function.
            topology_management_algorithm (Callable): Function implementing 
                link addition and removal logic.
            topology_management_algorithm_parameters (dict): Parameters 
                passed to the topology management function.
            user_defined_functions (list): List of user functions to be 
                injected into the global namespace.
            scheduler (Class): Scheduler class used for component execution.
            dump_interval (int): Tick interval for writing logs to disk.
            logs_directory (str): Path where log files will be stored.
            ignore_list (list): List of agent classes to exclude from metrics.
            clean_data_in_memory (bool): If True, clears metric lists after 
                each disk dump.
            tick_duration (int): Duration value for time conversion.
            time_unit (str): Unit of time (e.g., 'seconds', 'hours').
            scenario (str): Scenario label for experiment differentiation.
            repetition (int): Repetition index for the current simulation.
            topology_name (str): Name or type of the network topology.
        """
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
        self.agent_metrics = {}
        self.ignore_list = ignore_list

        # Convert time unit using timedelta for standardization
        self.tick_duration = datetime.timedelta(**{time_unit: tick_duration}).total_seconds()
        
        for function in user_defined_functions:
            globals()[function.__name__] = function
        
        ComponentManager.model = self

        self.scenario = scenario
        self.repetition = repetition
        self.topology_name = topology_name

    def initialize(self, dataset: str) -> None:
        """Initializes agents and their relationships from a JSON dataset.

        Args:
            dataset (str): File path to the JSON configuration file.
            
        Raises:
            FileNotFoundError: If the dataset path is invalid.
            json.JSONDecodeError: If the file is not a valid JSON.
        """
        # Clear previous component states
        for component_class in ComponentManager.__subclasses__():
            if component_class.__name__ != "Simulator":
                globals()[component_class.__name__].clear()
        
        with open(dataset, 'r', encoding='UTF-8') as file:
            dataset_data = json.load(file)
            
        created_components = []
        
        # Instantiate objects based on the dataset schema
        for class_name, components in dataset_data.items():
            for component in components:
                obj = globals()[class_name]()
                obj.set_attributes(**component)
                obj.relationships = component["relationships"]
                created_components.append(obj)
                
        # Resolve inter-object relationships
        for obj in created_components:
            for key, value in obj.relationships.items():
                # Global function reference
                if isinstance(value, str) and globals().get(value): 
                    setattr(obj, key, globals()[value])
                    
                # Single object relationship
                elif isinstance(value, dict) and "class" in value and "id" in value: 
                    object_relation = globals()[value['class']].find_by("id", value['id'])
                    setattr(obj, key, object_relation)
                   
                # Global dictionary mapping
                elif isinstance(value, dict) and all((globals().get(v) for v in value.values())): 
                    object_relation = {k: globals().get(v) for k, v in value.items()}
                    setattr(obj, key, object_relation)

                # List of object references
                elif isinstance(value, list) and all(('id' in c and 'class' in c for c in value)): 
                    components_list = [
                        globals()[comp['class']].find_by('id', comp['id']) for comp in value 
                    ]
                    setattr(obj, key, components_list)

                elif value is None: 
                    setattr(obj, key, None)

        # Add network nodes to the topology manager
        for agent in GroundStation.all() + Satellite.all() + ProcessUnit.all():
            self.topology.add_node(agent)
        
        # Establish network links
        for link in NetworkLink.all():            
            self.topology.add_edge(link["nodes"][0], link['nodes'][1])
            self.topology._adj[link["nodes"][0]][link["nodes"][1]] = link
            self.topology._adj[link["nodes"][1]][link["nodes"][0]] = link

    def initialize_logs(self) -> None:
        """Sets up the directory and data structures for metric logging."""
        os.makedirs(self.logs_directory, exist_ok=True)

        for component_class in ComponentManager.__subclasses__():
            if component_class not in self.ignore_list + [self.__class__]:
                if component_class.__name__ not in self.agent_metrics:
                    self.agent_metrics[component_class.__name__] = []
                    
    def step(self) -> None:
        """Executes a single simulation tick.

        Updates the scheduler, topology management, and resource allocation.
        """
        self.scheduler.step()
        self.topology_management_algorithm(
            topology=self.topology, 
            **self.topology_management_parameters
        )
        self.resource_management_algorithm(
            self, 
            self.resource_management_algorithm_parameters
        )
            
    def monitor(self) -> None:
        """Collects metrics from all tracked components.

        Triggered every step. If the dump interval is reached, it invokes 
        the data persistence method.
        """
        for component_class in ComponentManager.__subclasses__():
            if component_class not in self.ignore_list + [self.__class__]:
                metrics = {
                    'Step': self.scheduler.steps,
                    'metrics': component_class.collect_class_metrics()
                }
                
                if not metrics['metrics']:
                    continue
                
                self.agent_metrics[component_class.__name__].append(metrics)
        
        if self.scheduler.steps == self.last_dump + self.dump_interval:
            self.dump_data()
            self.last_dump = self.scheduler.steps
                                  
    def dump_data(self) -> None:
        """Writes accumulated metrics to JSONL files on disk.

        If `clean_data_in_memory` is True, the internal buffer is cleared 
        after a successful write.
        """
        if not os.path.exists(self.logs_directory):
            os.makedirs(self.logs_directory)  
        
        for agent_class, data in self.agent_metrics.items():
            filename = f"{self.logs_directory}/{agent_class}.jsonl"

            with open(filename, mode="a", encoding="utf-8") as file:
                for metric in data:
                    file.write(json.dumps(metric) + "\n") 

            if self.clean_data_in_memory:
                self.agent_metrics[agent_class] = []
            
    def run(self) -> None:
        """Starts the main simulation execution loop.

        Runs until the `stopping_criterion` evaluates to True. Performs 
        initial monitoring and a final data dump after termination.
        """
        self.running = True
        self.initialize_logs()
        self.monitor()
            
        while self.running:
            print(f"Step {self.scheduler.steps + 1}")
            self.step()
            self.monitor()
            
            # Stop if criterion is met
            if self.stopping_criterion(self):
                self.running = False
        
        self.dump_data()