from .components import Satellite, ProcessUnit, User, ComponentManager

from prometheus_client import Gauge

@classmethod
def satellite_collect_class_metrics(cls) -> list:
    class_metrics = {
        "Available" : 0,
        "Power" : 0
    }
    
    for satellite in Satellite.all():
        class_metrics["Available"] += 1 if satellite.active else 0
        class_metrics["Power"] += satellite.power

    for key, bucket in Satellite.buckets.items():
        bucket.set(class_metrics[key])

    return class_metrics


def set_buckets():
    buckets = {
        "Request Provisioning" : Gauge('request_provisioning', "Aplicacoes requisitando provisionamento"),
        "Provisioning" : Gauge('provisioning', "Aplicacoes requisitando provisionamento"),
        "Making Request" : Gauge('making_request', "Usuario buscando conectividade"),
        "Connectivity" : Gauge('connectivity', "Usuario conectados")
    }

    setattr(User, 'buckets', buckets)

    buckets = {
        "Available" : Gauge('available_satellites', 'Satellite availability')
    }

    setattr(Satellite, 'buckets', buckets)

    buckets = {
        'CPU Demand' : Gauge('cpu_usage', 'CPU usage of the satellite'),
        'Memory Demand' : Gauge('memory_usage', 'Memory usage of the satellite'),
        'Storage Demand' : Gauge('storage_usage', 'Storage usage of the satellite'),
    }

    setattr(ProcessUnit, 'buckets', buckets)


@classmethod
def user_collect_class_metrics(cls) -> list:
    metrics = {
        "Request Provisioning" : 0,
        "Making Request" : 0,
        "Connectivity" : 0,
        "Provisioning" : 0
    }

    for user in cls.all():
        user_metrics = user.collect_metrics()

        accesses = user_metrics["Access to Applications"]

        for access in accesses:
            for key in metrics:
                metrics[key] += 1 if access[key] else 0

    for key, bucket in User.buckets.items():
        bucket.set(metrics[key])

    return metrics
 
@classmethod
def process_unit_collect_class_metris(self) -> list:
    class_metrics = {
        "CPU Demand" : 0,
        "Memory Demand" : 0,
        "Storage Demand" : 0,
    }
    
    for process_unit in ProcessUnit.all():
        class_metrics["CPU Demand"] += process_unit.cpu_demand
        class_metrics["Memory Demand"] += process_unit.memory_demand
        class_metrics["Storage Demand"] += process_unit.storage_demand

    for key, bucket in ProcessUnit.buckets.items():
        bucket.set(class_metrics[key])

    return class_metrics



