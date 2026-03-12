from ..component_manager import ComponentManager

class NetworkFlow(ComponentManager):
    """ 
        Class that represents specific data flows between a source and a destination.
        It can represent communication between user and application.
        Currently does not allocate bandwidth, but this can be implemented using the 'flow_schedule' component in Topology.
    """
    _instances = []
    _object_count = 0
    
    def __init__(
        self,
        id : int = 0,
        status: str = "active",
        source: object = None,
        target: object = None,
        start: int = 0,
        path: list = [],
        data_to_transfer: int = 0,
        metadata: dict = {},
        ):
        
        # Adding the object to the instance list
        self.__class__._instances.append(self) 
        self.__class__._object_count += 1
        
        if id == 0:
            id = self.__class__._object_count
        self.id = id
        
        self.status = status
        
        self.source = source
        self.target = target
        
        self.start = start
        self.end = None
        self.data_to_transfer = data_to_transfer
        self.metadata = metadata
        
        self.path = path
        self.bandwidth = {}
        
        # Attributes to facilitate change management
        self.last_path = path.copy()
        self.last_bandwidth = {}
        
        for i in range(len(path) -1):
            link = self.model.topology[path[i]][path[i+1]]
            
            link['flows'].append(self)
            
            self.bandwidth[link.id] = 0
            self.last_bandwidth[link.id] = 0
    
    def step(self):
        """ Method responsible for activating the component and ensuring its correct operation throughout the simulation
        """
        pass
         
    def export(self) -> dict:
        """ Method that generates a representation of the object in dictionary format to save current context
        """  
        component = {
            "id": self.id,
            "status": self.status,
            "nodes": [{"class": type(node).__name__, "id": node.id} for node in self.nodes],
            "path": self.path,
            "start": self.start,
            "end": self.end,
            "data_to_transfer": self.data_to_transfer,
            "bandwidth": self.bandwidth,
            "metadata": self.metadata,
        }
        
        return component