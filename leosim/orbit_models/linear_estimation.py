from geopy.distance import geodesic
import math

def linear_estimation(sat):
    last_lat, last_lon = sat["mobility_model_parameters"]["last_coordinate"]
    new_lat, new_lon = sat["coordinates"]

    # Get points distance in miles
    speed_ns = geodesic((last_lat, last_lon), (new_lat, last_lon)).miles
    speed_ew = geodesic((last_lat, last_lon), (last_lat, new_lon)).miles

    # Convert miles to degrees
    speed_ns /= 69
    speed_ew /= (69 * abs(math.cos(math.radians(last_lat))))

    # Update coordinates
    sat["mobility_model_parameters"]["last_coordinate"] = sat["coordinates"].copy()
    new_lat = (new_lat + speed_ns + 85) % 170 - 85
    new_lon = (new_lon + speed_ew + 180) % 360 - 180

    sat["coordinates"] = [new_lat, new_lon]