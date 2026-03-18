# Simulator components
from ..component_manager import ComponentManager
from typing import List, Dict, Any, Optional

class Application(ComponentManager):
    """Represents an application with specific resource demands.

    An Application is a unit of workload that can be requested by users,
    provisioned on processing units, and migrated between hosts during 
    the simulation.

    Attributes:
        _instances (list): List of all created Application instances.
        _object_count (int): Counter for generating unique IDs.
        id (int): Unique identifier for the application.
        cpu_demand (int): CPU resource requirement.
        memory_demand (int): RAM resource requirement.
        storage_demand (int): Disk space resource requirement.
        dependency_labels (List[str]): Required software environment labels (e.g., 'docker').
        architectural_demands (dict): Specific hardware requirements (e.g., 'GPU').
        state (int): Current internal state/data size of the application.
        sla (int): Service Level Agreement threshold.
        user (object): Reference to the user who owns this application.
        process_unit (object): The host where the application is currently allocated.
        migrations (list): History of migration events and their status.
        available (bool): Whether the application is currently functional.
        being_provisioned (bool): Whether the application is in a setup/migration state.
        completed (bool): Whether the application lifecycle has ended.
    """

    _instances = []
    _object_count = 0
    
    def __init__(
        self,
        id: int = 0,
        cpu_demand: Optional[int] = None,
        memory_demand: Optional[int] = None,
        storage_demand: Optional[int] = None,
        dependency_labels: List[str] = [],
        architectural_demands: Dict[str, Any] = {},
        state: int = 0,
        sla: int = 0,
    ) -> None:
        """Initializes an Application instance.

        Args:
            id (int): Unique ID. If 0, an ID is automatically assigned.
            cpu_demand (int, optional): CPU units required.
            memory_demand (int, optional): Memory units required.
            storage_demand (int, optional): Storage units required.
            dependency_labels (List[str]): List of software dependency tags.
            architectural_demands (dict): Specific hardware constraints.
            state (int):  State size.
            sla (int): SLA value.
        """
        self.__class__._instances.append(self)
        self.__class__._object_count += 1
        
        if id == 0:
            id = self.__class__._object_count
        self.id = id 
        
        self.cpu_demand = cpu_demand
        self.memory_demand = memory_demand
        self.storage_demand = storage_demand
        self.state = state
        self.sla = sla
        self.dependency_labels = dependency_labels
        self.architectural_demands = architectural_demands
        
        self.user = None
        self.process_unit = None
        self.migrations = []
        self.available = False  
        self._available = False
        self.being_provisioned = False
        self.completed = False
                          
    def collect_metrics(self) -> Dict[str, Any]:
        """Collects telemetry data from this specific application instance.

        Returns:
            dict: A dictionary containing IDs, demands, current state, 
                hosting information, and migration status.
        """
        last_migration = self.migrations[-1].copy() if self.migrations else None
        
        if last_migration:
            # Conversion to string for serializable disk storage
            last_migration['origin'] = str(last_migration['origin'])
            last_migration['target'] = str(last_migration['target'])
            
        metrics = {
            "ID": self.id,
            "CPU Demand": self.cpu_demand,
            "Memory Demand": self.memory_demand,
            "Storage Demand": self.storage_demand,
            "State": self.state,
            "SLA": self.sla,
            "Process Unit": str(self.process_unit) if self.process_unit else None,
            "Available": self.available,
            "Being Provisioned": self.being_provisioned,
            "Last Migration": last_migration
        }
        
        return metrics
    
    def step(self) -> None:
        """Updates the component state for the current simulation tick.

        This method manages the migration lifecycle (waiting, downloading, 
        state transfer, and finishing) and ensures resource consistency 
        between processing units.
        """
        if len(self.migrations) > 0 and self.migrations[-1]['end'] is None:
            migr = self.migrations[-1]
            # TODO: Implement a formal dependency management system.
            # The logic below is a placeholder for future state-machine updates.
            dependencies_on_process_unit = []
            
            # Currently, migrations are instantaneous in terms of data transfer.
            if migr["status"] == 'waiting':
                if len(dependencies_on_process_unit) > 0 or len(dependencies_on_process_unit) == len(self.dependency_labels):
                    migr['status'] = 'download_dependencies'

            # Transition directly to the next stage as dependency simulation is pending.
            if migr['status'] == 'download_dependencies' and len(dependencies_on_process_unit) == len(self.dependency_labels):
                # Release resources from the source processing unit if migrating.
                if self.process_unit:
                    self.process_unit.cpu_demand -= self.cpu_demand
                    self.process_unit.memory_demand -= self.memory_demand
                    self.process_unit.storage_demand -= self.storage_demand

                if self.process_unit is None or self.state == 0:
                    migr['status'] = "finished"
                else:
                    # TODO: Implement complex state migration logic.
                    migr['status'] = 'application_state_migration'
                
            # Log time spent in each migration phase.
            if migr['status'] == 'waiting':
                migr['waiting_time'] += 1
            elif migr['status'] == 'download_dependencies':
                migr['download_time'] += 1
            elif migr['status'] == 'application_state_migration':
                migr['application_state_migration_time'] += 1
            elif migr['status'] == "finished":
                # Terminate migration and update host references.
                migr["end"] = self.model.scheduler.steps + 1
                
                if self.process_unit:
                    self.process_unit.applications.remove(self)
                
                self.process_unit = migr['target']
                self.process_unit.applications.append(self)

                self.being_provisioned = False
                self.available = True    

        # Update availability flags based on host status.
        if self.process_unit and not self.process_unit.available:
            self.available = False
        elif self.process_unit and not self.available:
            self.available = True
        elif self.process_unit is None and self.available:
            self.available = False
            
        self._available = self.available

    def export(self) -> dict:
        """Generates a dictionary representation for context saving.

        Returns:
            dict: The serialized state of the application including 
                relationships with users and processing units.
        """
        component = {
            "id": self.id,
            "cpu_demand": self.cpu_demand,
            "memory_demand": self.memory_demand,
            "storage_demand": self.storage_demand,
            "state": self.state,
            "sla": self.sla,
            "dependency_labels": self.dependency_labels,
            "architectural_demands": self.architectural_demands,
            "relationships": {
                "user": {"id": self.user.id, "class": type(self.user).__name__} if self.user else None,
                "process_unit": {"id": self.process_unit.id, "class": type(self.process_unit).__name__} if self.process_unit else None,
            }
        }
        return component
    
    def provision(self, process_unit: Any) -> None:
        """Starts the provisioning process on a target processing unit.

        Args:
            process_unit (object): The target host where the application 
                will be provisioned.
        """
        if self.completed:
            return

        self.being_provisioned = True
        
        # Immediate resource reservation on target host.
        process_unit.cpu_demand += self.cpu_demand
        process_unit.memory_demand += self.memory_demand
        process_unit.storage_demand += self.storage_demand
        
        self.migrations.append({
            "status": "waiting",
            "origin": self.process_unit,
            "target": process_unit,
            "start": self.model.scheduler.steps + 1,
            "end": None,
            "waiting_time": 0,
            "download_time": 0,
            "application_state_migration_time": 0
        })

    def deprovision(self) -> None:
        """Ends the provisioning and releases resources from the current host.

        Resets availability and clears the reference to the processing unit.
        """
        self.available = False
        process_unit = self.process_unit

        if process_unit:
            process_unit.cpu_demand -= self.cpu_demand
            process_unit.memory_demand -= self.memory_demand
            process_unit.storage_demand -= self.storage_demand

            process_unit.applications.remove(self)
            
        self.process_unit = None