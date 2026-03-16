def coordinates_history(satellite : object):
    size = satellite.mobility_model_parameters.get("len")
    
    for i in range(size):
        satellite.coordinates_trace.append(satellite.coordinates_trace[i%size])