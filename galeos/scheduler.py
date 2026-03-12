from .components.application import*
from .components.ground_station import*
from .components.topology import*
from .components.user import*


class Scheduler:
    """ Class responsible for scaling simulator components
    """
    def __init__(self, model : object):
        self.model = model
        self.steps = 0
    
    def step(self):
        """ Method that performs the scheduling of components in standard order
        """
        for application in Application.all():
            application.step()
            
        for user in User.all():
            for access_model in user.applications_access_models:
                access_model.update_access()
            
        for flow in NetworkFlow.all():
            flow.step()
        
        for user in User.all():
            user.step()
            
        for satellite in Satellite.all():
            satellite.step()
        
        for ground_station in GroundStation.all():
            ground_station.step()
        
        
        self.model.topology.step()
            
        for process_unit in ProcessUnit.all():
            process_unit.step()
        
        self.steps += 1