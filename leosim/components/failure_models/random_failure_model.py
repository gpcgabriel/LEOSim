from random import random

def random_failure_model(satellite, **parameters) -> bool:
    prob = parameters.get("p", 0.1)
                          
    first_step = parameters.get('first_error_step', 0)
    step = satellite.model.scheduler.steps + 1

    if first_step > step:
        return False
    
    return random() < prob

