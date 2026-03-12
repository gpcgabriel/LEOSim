# Simulator components
from ..component_manager import ComponentManager
from typing import List

class Application(ComponentManager):
    """
        Class that represents an application which has resource demands and can be requested repeatedly by a user
    """
    _instances = []
    _object_count = 0
    
    def __init__(
            self,
            id : int = 0,
            cpu_demand : int = None,
            memory_demand : int = None,
            storage_demand : int = None,
            dependency_labels : List[str] = [],
            architectural_demands : dict = {},
            state : int = 0,
            sla : int = 0,
        ):
        
        # Adding the object to the instance list
        self.__class__._instances.append(self)
        self.__class__._object_count += 1
        
        if id == 0:
            id = self.__class__._object_count
        self.id = id 
        
        # Sets demands
        self.cpu_demand = cpu_demand
        self.memory_demand = memory_demand
        self.storage_demand = storage_demand
        
        # Set state
        self.state = state
        
        # Set SLA
        self.sla = sla
        
        # Set dependency labels (e.g. containers, libraries, etc.) required to provision the application 
        self.dependency_labels = dependency_labels
        
        # Set architectural dependencies (e.g. GPU) required to provision the application
        self.architectural_demands = architectural_demands
        
        self.user = None
        self.process_unit = None
        
        self.migrations = []
        self.available = False  
        self._available = False
        self.being_provisioned = False
        self.completed = False
                          
    def collect_metrics(self) -> dict:
        """ 
            Method that collects data from a specific instance
            Can be modified for customized data collection
        """
        last_migration = self.migrations[-1].copy() if self.migrations else None
        
        if last_migration:
            # Necessary conversion to save to disk
            last_migration['origin'] = str(last_migration['origin'])
            last_migration['target'] = str(last_migration['target'])
            
        metrics = {
            "ID" : self.id,
            "CPU Demand" : self.cpu_demand,
            "Memory Demand" : self.memory_demand,
            "Storage Demand" : self.storage_demand,
            "State" : self.state,
            "SLA" : self.sla,
            "Process Unit" : str(self.process_unit) if self.process_unit else None,
            "Available" : self.available,
            "Being Provisioned" : self.being_provisioned,
            "Last Migration" : last_migration
        }
        
        return metrics
    
    def step(self):
        """ 
            Method responsible for activating the component and ensuring its correct operation throughout the simulation
            Can be modified to implement custom strategies for the migration process
        """
        if len(self.migrations) and self.migrations[-1]['end'] == None:
            migr = self.migrations[-1]
            # TODO: Implement a dependency system and manage the time in each state
            # The code below was developed with future implementations in mind
            # both by the current project developers and potential contributors
            dependencies_on_process_unit = []
            
            # Every migration currently occurs in the same step it is requested, and there is no simulation of data being transferred
            if migr["status"] == 'waiting':
                if len(dependencies_on_process_unit) > 0 or len(dependencies_on_process_unit) == len(self.dependency_labels):
                    migr['status'] = 'download_dependencies'
                    
            if migr['status'] == 'download_dependencies' and len(dependencies_on_process_unit) == len(self.dependency_labels):
                if self.process_unit:
                    self.process_unit.cpu_demand -= self.cpu_demand
                    self.process_unit.memory_demand -= self.memory_demand
                    self.process_unit.storage_demand -= self.storage_demand

                if self.process_unit is None or self.state == 0:
                    migr['status'] = "finished"
                else:
                    # TODO: Implement state migration
                    # Initial structure for future work
                    migr['status'] = 'application_state_migration'
                
            if migr['status'] == 'waiting':
                migr['waiting_time'] += 1
                
            elif migr['status'] == 'download_dependencies':
                migr['download_time'] += 1
                
            elif migr['status'] == 'application_state_migration':
                migr['application_state_migration_time'] += 1
                
            elif migr['status'] == "finished":
                if migr["status"] == "finished":
                    migr["end"] = self.model.scheduler.steps + 1
                    
                    if self.process_unit:
                        self.process_unit.applications.remove(self)
                    
                    self.process_unit = migr['target']
                    self.process_unit.applications.append(self)
                    self.being_provisioned = False
                    self.available = True    

        if self.process_unit and not self.process_unit.available:
            self.available = False
            
        elif self.process_unit and not self.available:
            self.available = True

        elif self.process_unit is None and self.available:
            self.available = False
            
        self._available = self.available

    def export(self):
        """ Method that generates a representation of the object in dictionary format to save current context
        """
        component = {
            "id" : self.id,
            "cpu_demand" : self.cpu_demand,
            "memory_demand" : self.memory_demand,
            "storage_demand" : self.storage_demand,
            "state" : self.state,
            "sla" : self.sla,
            "dependency_labels" : self.dependency_labels,
            "architectural_demands" : self.architectural_demands,
            "relationships" :{
                "user" : {"id" : self.user.id, "class" : type(self.user).__name__} if self.user else None,
                "process_unit" : {"id" : self.process_unit.id, "class" : type(self.process_unit).__name__} if self.process_unit else None,
            }
        }

        return component
    
    def provision(self, process_unit : object):
        """ Method that starts the migration of an application
        """
        # If application ending, do not allow provisioning
        if self.completed:
            return

        # Enables the flag that the service is being provisioned
        self.being_provisioned = True
        
        # Updates the resource usage of the target server
        process_unit.cpu_demand += self.cpu_demand
        process_unit.memory_demand += self.memory_demand
        process_unit.storage_demand += self.storage_demand
        
        self.migrations.append({
            "status" : "waiting",
            "origin" : self.process_unit,
            "target" : process_unit,
            "start" : self.model.scheduler.steps + 1,
            "end" : None,
            "waiting_time" : 0,
            "download_time" : 0,
            "application_state_migration_time" : 0
        })

    def deprovision(self):
        """ 
            Method that ends the provisioning of an application
            In a situation where an already allocated application becomes unavailable or needs to be provisioned on another ProcessUnit,
            this function must be called to ensure all involved components are updated
        """
        self.available = False
        process_unit = self.process_unit

        if process_unit:
            process_unit.cpu_demand -= self.cpu_demand
            process_unit.memory_demand -= self.memory_demand
            process_unit.storage_demand -= self.storage_demand

        self.process_unit = None
        
        if self in self.__class__._instances:
            self.__class__._instances.remove(self)
        
        self.completed = True