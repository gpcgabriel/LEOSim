from leosim.components import User,Application, FixedDurationAccessModel,Topology, NetworkLink, Satellite, mesh_network
from json import load
from random import choices
from time import sleep
import requests

N2YO_API_KEY = "API_KEY"
REFERENCE_POINT = (-15.669171, -48.013922, 0)
MAX_RANGE = 1500

def create_user(
        coordinates : tuple,
        connection_range : int = MAX_RANGE
    ) -> User:
    
    user = User(
        coordinates=coordinates,
        max_connection_range=connection_range
    )
        
    user.mobility_model = None
    user.mobility_model_parameters = {}
    
    return user

def create_application_to_user(
        user : User,
        cpu_demand : int = 0,
        memory_demand : int = 0,
        storage_demand : int = 0,
        state : int = 0,
        sla : int = 0,
        access_class: type = FixedDurationAccessModel
    ):
    
    app = Application(
        cpu_demand=cpu_demand,
        memory_demand=memory_demand,
        storage_demand=storage_demand,
        state=state,
        sla=sla,
    )
    
    values = [ j for j in range(3, 20)]
    
    access_model = FixedDurationAccessModel(
        user=user,
        application=app,
        start=1,
        duration_values=choices(values, k=5),
        interval_values=choices(values, k=5),
        connection_duration_values=choices(values, k=5),
        connection_interval_values=choices(values, k=5)
    )
    
    user.connection_to_application(application=app, access_model=access_model)
     
def create_link(
        v1 : object, 
        v2 : object,
        delay : int = 1,
        bandwidth : int = NetworkLink.default_bandwidth,
        topology : object = None
    ):
    
    link = NetworkLink()
    
    link['topology'] = topology
    link['nodes'] = [v1, v2]
    link['bandwidth'] = bandwidth
    link['delay'] = delay
    link['type'] = 'static'
    
    topology.add_edge(v1, v2)
        
    topology._adj[v1][v2] = link
    topology._adj[v2][v1] = link
  
def get_satellites_from_api( coordinates, sat_range, api_category: int = 52) -> dict:
    API_URL = f"https://api.n2yo.com/rest/v1/satellite/above/{coordinates[0]}/{coordinates[1]}/{coordinates[2] if len(coordinates) > 2 else 0}/{sat_range}/{api_category}/&apiKey={N2YO_API_KEY}"
    try:
        response = requests.get(url=API_URL)
    except:
        print("Unable to grab satellites from API")
        return
    
    return response.json()["above"]

def load_satellites_from_api(
        max_steps : int = 10,
        interval : int = 30,
        sat_range : int = 1000,
        api_category: int = 52, 
        max_satellites: int = 100
    ) -> None:
    sats = {}
    
    for i in range(max_steps):
        current_step = get_satellites_from_api(REFERENCE_POINT, sat_range=sat_range, api_category=api_category)
        
        for sat in current_step:
            id = sat['satid']
            coordinates = (sat['satlat'], sat['satlng'], sat['satalt'])
            
            if id in sats:
                satellite = sats[id]
                
                satellite.coordinates_trace.append(coordinates)
                
            elif Satellite.count() < max_satellites:
                satellite = Satellite(
                    name=f"SATELLITE-{id}",
                    coordinates=coordinates,
                    max_connection_range=MAX_RANGE,
                    is_gateway=True
                )
                
                # satellite.mobility_model = coordinates_history
                satellite.coordinates_trace.extend([None for _ in range(i)] + [coordinates])
                
                sats[id] = satellite
                
        for satellite in Satellite.all():
            if len(satellite.coordinates_trace) < i:
                satellite.coordinates_trace.append(None)
                
                   
        sleep(interval)
        
    for sat in Satellite.all():
        sat.coordinates = sat.coordinates_trace[0] 

def load_satellites_from_file(
        filename : str = "satellites.json",
        max_steps : int = 10,
        max_satellites: int = 100
    ) -> None:
    sats = {}
    
    with open(filename, 'r', encoding='UTF-8') as file:
        data = load(file)
        
    for i, current_step in enumerate(data[: max_steps if max_steps - 1 < len(data) else None]):
        for sat in current_step:
            id = sat['satid']
            coordinates = (sat['satlat'], sat['satlng'], sat['satalt'])            
            if id in sats:
                satellite = sats[id]
                
                satellite.coordinates_trace.append(coordinates)
                
            elif Satellite.count() < max_satellites:
                satellite = Satellite(
                    name=f"SATELLITE-{id}",
                    coordinates=coordinates,
                    max_connection_range=MAX_RANGE,
                    is_gateway=True
                )
                
                # satellite.mobility_model = coordinates_history
                satellite.coordinates_trace.extend([None for _ in range(i)] + [coordinates])
                
                sats[id] = satellite
                
        for satellite in Satellite.all():
            if len(satellite.coordinates_trace) < i:
                satellite.coordinates_trace.append(None)

    for sat in Satellite.all():
        sat.coordinates = sat.coordinates_trace[0]         
       
def create_satellite_topology(
        topology : Topology,
        max_steps : int = 10,
        interval : int = 30,
        sat_range : int = 1000,
        max_satellites: int = 100, 
        filename : str = ""
    ):
    
    if filename:
        load_satellites_from_file(
            filename=filename,
            max_steps=max_steps,
            max_satellites=max_satellites
        )
    else:
        load_satellites_from_api(
            max_steps=max_steps, 
            interval=interval, 
            sat_range=sat_range, 
            max_satellites=max_satellites
        )

    topology.add_nodes_from(Satellite.all())
    
    mesh_network(topology)