from ..network_link import NetworkLink
from ..satellite import Satellite

def mesh_network(topology):
    satellites = [ sat for sat in Satellite.all() if sat.coordinates is not None]
    
    for satellite in satellites:
        targets = [
            neighbor for neighbor in satellites 
            if neighbor != satellite and neighbor not in topology[satellite] and topology.within_range(satellite, neighbor)
        ]
        
        for target in targets:
            link = NetworkLink()
            
            link['topology'] = topology
            link['nodes'] = [satellite, target]
            link['bandwidth'] = NetworkLink.default_bandwidth
            link['delay'] = NetworkLink.get_delay(satellite.coordinates, target.coordinates)
            link['type'] = 'dynamic'
            
            topology.add_edge(satellite, target)
            
            topology._adj[satellite][target] = link
            topology._adj[target][satellite] = link

def default_topology_management(topology : object, **parameters):
    mesh_network(topology=topology)