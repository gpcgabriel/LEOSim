from leosim.components import User, GroundStation, ProcessUnit, Satellite
from random import randint
from time import sleep
import networkx as nx
import argparse
import requests
import json

next_id = 0

def create_satellite(name, coordinates, relationship: dict={}):
    global next_id
    next_id += 1
    return {
        "id": next_id,
        "name": name,
        "coordinates": coordinates,
        "relationship": relationship,
        "mobility_model": {
            "name": "",
            "parameters": {}
        }
    }

def create_application(name, cpu, memory, storage, relationship, sla=None, dependencies=[], architectural_demands=[]):
        global next_id
        next_id += 1
        return {
            "id": next_id,
            "name": name,
            "cpu_demand": cpu,
            "memory_demand": memory,
            "storage_demand": storage,
            "sla": sla,
            "dependencies": dependencies, 
            "architectural_demands": architectural_demands,
            "relationship": relationship
        }

def coordinates_generate_nearby(coordinates, max_distance):
    return [coordinates[0] + randint(-max_distance, max_distance), coordinates[1] + randint(-max_distance, max_distance)]

def create_empty_function(name):
    def func():
        pass
    func.__name__ = name
    return func

class DatasetGenerator:
    ground_stations = []
    satellites = []
    users = []
    servers = []
    n2yo_api_key = "API_KEY"

    @classmethod
    def ground_station(cls, filepath: str):
        G = nx.read_gml(filepath)

        for i, node in enumerate(G.nodes()):
            
            if not G.nodes[node].get("Country"):
                continue

            cls.ground_stations.append(GroundStation(coordinates=(G.nodes[node]["Latitude"], G.nodes[node]["Longitude"])))    
        return cls.ground_stations

    @classmethod
    def user(cls, max_users: int, max_distance_from_ground_station: int, min_users: int=0, max_users_per_ground_station: int=None, min_users_per_ground_station: int=0):

        if min_users_per_ground_station * cls.ground_stations in range(min_users, max_users):
            min_users = min_users_per_ground_station * cls.ground_stations
        number_of_users = randint(min_users, max_users)

        # Fulfill the minimum number of users per ground station
        for ground_station in cls.ground_stations:
            cls.users.extend([ User(coordinates=coordinates_generate_nearby(ground_station.coordinates, max_distance_from_ground_station)) for _ in range(min_users_per_ground_station) ])

        number_of_users -= len(cls.users)
        
        # Creating users close to a random ground station
        while number_of_users > 0:
            ground_station = cls.ground_stations[randint(0, len(cls.ground_stations)-1)]
            number_of_new_users = randint(0, number_of_users)

            cls.users.extend([ User(coordinates=coordinates_generate_nearby(ground_station.coordinates, max_distance_from_ground_station)) for _ in range(number_of_new_users) ])
            number_of_users -= number_of_new_users

        return cls.users

    @classmethod
    def server(cls, min_process_units: int, max_distance_from_ground_station: int, max_process_units: int, min_process_units_per_ground_station: int, max_process_units_per_ground_station: int):

        if min_process_units_per_ground_station * len(cls.ground_stations) in range(min_process_units, max_process_units):
            min_process_units = min_process_units_per_ground_station * len(cls.ground_stations)

        number_of_process_units = randint(min_process_units, max_process_units)

        # Fulfill the minimum number of servers per ground station
        for ground_station in cls.ground_stations:
            cls.servers.extend([ ProcessUnit(cpu=100, memory=100, storage=100, coordinates=coordinates_generate_nearby(ground_station.coordinates, max_distance=max_distance_from_ground_station)) for _ in range(min_process_units_per_ground_station) ])
                
            number_of_process_units -= min_process_units_per_ground_station
        
        # Creating servers close to a random ground station
        for _ in range(number_of_process_units):
            ground_station = cls.ground_stations[randint(0, len(cls.ground_stations)-1)]
            number_of_new_process_units = randint(0, number_of_process_units)

            cls.servers.extend([ ProcessUnit(cpu=100, memory=100, storage=100, coordinates=coordinates_generate_nearby(ground_station.coordinates, max_distance=max_distance_from_ground_station)) for _ in range(min_process_units_per_ground_station) ])
            number_of_process_units -= 1

        return cls.servers

    @classmethod
    def get_satellites_from_api(cls, coordinates, sat_range, api_category: int=52, max_satellites: int=None) -> dict:
        API_URL = f"https://api.n2yo.com/rest/v1/satellite/above/{coordinates[0]}/{coordinates[1]}/{coordinates[2] if len(coordinates) > 2 else 0}/{sat_range}/{api_category}/&apiKey={cls.n2yo_api_key}"
        try:
            response = requests.get(url=API_URL)
        except:
            print("Unable to grab satellites from API")
            return
        for satellite in response.json()["above"][:max_satellites]:
            cls.satellites.append(Satellite(name=satellite["satname"], coordinates=(satellite["satlat"], satellite["satlng"])))
        return cls.satellites
    
    @classmethod
    def get_real_satellites_trajectory(cls, coordinates, sat_range, executions, collect_sleep_time=60, api_category: int=52, max_satellites: int=None):
        data = []
        satellites = []

        for i in range(executions):
            data.append({sat.name: sat for sat in cls.get_satellites_from_api(coordinates, sat_range, api_category)})
            sleep(collect_sleep_time)
            
            for sat in data[i].values():
                if sat.id not in [s.id for s in satellites]:
                    satellites.append(sat)

        satellites = satellites[:max_satellites]

        for sat in satellites:
            sat.mobility_model = create_empty_function("coordinates_history")
            sat.mobility_model_parameters = {"next_coordinates": []}  
            for i, step in enumerate(data):
                sat.mobility_model_parameters["next_coordinates"].append(None)
                if step.get(sat.name):
                    sat.mobility_model_parameters["next_coordinates"][i] = step[sat.name].coordinates
        
        return satellites

    @classmethod
    def get_real_satellite_estimated_trajectory(cls, coordinates, sat_range, executions, collect_sleep_time=60, api_category: int=52, max_satellites: int=None):
        for _ in range(executions):
            satellites = { sat.name: sat for sat in cls.get_satellites_from_api(coordinates, sat_range) }
            cls.satellites = []
            sleep(collect_sleep_time)
            for satellite in cls.get_satellites_from_api(coordinates, sat_range):
                if satellites.get(satellite.name):
                    first_coordinate = satellites[satellite.name].coordinates
                    second_coordinate = satellite.coordinates

                    satellites[satellite.name].coordinates = second_coordinate

                    satellites[satellite.name].mobility_model = create_empty_function("linear_estimation")
                    satellites[satellite.name].mobility_model_parameters = {"last_coordinate": first_coordinate}
                
                cls.satellites = [ sat for sat in satellites.values() if sat.mobility_model ]
        
    @classmethod
    def export(cls, filepath: str=None):
        data = {}
        for att in cls.__dict__:
            if att.startswith("__") or not isinstance(cls.__dict__[att], list):
                continue

            data[att] = []
            for obj in cls.__dict__[att]:
                data[att].append(obj.export())

        if filepath:
            if not filepath.endswith(".json"):
                filepath += ".json"

            # Saves all class attributes in a file
            with open(filepath, "w") as json_file:
                json.dump(data, json_file, indent=4)
        return data

def parse_args():
    parser = argparse.ArgumentParser(description="Dataset Generator for Ground Stations")
    parser.add_argument("-g", "--ground-stations", type=str, required=True, help="Path to the GML file containing ground stations")
    parser.add_argument("-o", "--output", type=str, required=True, help="Path to the output file")
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    ground_stations = DatasetGenerator.ground_station(args.ground_stations)
    users = DatasetGenerator.user(max_users=1000, max_distance_from_ground_station=1000, min_users=100, max_users_per_ground_station=100, min_users_per_ground_station=10)
    servers = DatasetGenerator.server(min_process_units=100, max_distance_from_ground_station=1000, max_process_units=1000, min_process_units_per_ground_station=10, max_process_units_per_ground_station=100)
    satellites = DatasetGenerator.get_real_satellites_trajectory(coordinates=ground_stations[0].coordinates, sat_range=100, executions=5, collect_sleep_time=5)

    DatasetGenerator.export(args.output)
