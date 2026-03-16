from ..components.ground_station import GroundStation
from geopy.distance import geodesic, great_circle
from random import choice 

def random_mobility_model(user : object):
    parameters = user.mobility_model_parameters
    station = choice(GroundStation.all())
    
    total_distance = geodesic(user.coordinates[:2], station.coordinates[:2]).kilometers
    
    num_steps = int(total_distance // parameters.get("step_km", 0.5))
    
    points = []
    for i in range(1, num_steps + 1):
        fraction = i / (num_steps + 1)
        
        point = great_circle(kilometers=fraction * total_distance).destination(
            user.coordinates, 
            great_circle(user.coordinates[:2], station.coordinate[:2]).bearing
            )
        
        points.extend([(point.latitude, point.longitude) for _ in range(parameters.get("steps_to_move", 1))])
    
    user.coordinates_trace.extend(point)
