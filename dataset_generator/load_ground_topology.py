from galeos.components import GroundStation, NetworkLink, Topology
from .create_components import MAX_RANGE
import networkx as nx

def load_ground_topology_from_gml(
        filepath: str, 
        default_delay : int  = 1
    ) -> Topology:
    
    G = nx.read_gml(filepath)
    
    
    new_labels = {}
    ground_stations = {}
    nodes_to_remove = []
    
    for node in G.nodes():
            
        if not G.nodes[node].get("Country"):
            nodes_to_remove.append(node)
            continue

        station = GroundStation(coordinates=(G.nodes[node]["Latitude"], G.nodes[node]["Longitude"], 0), max_connection_range=MAX_RANGE) 
 
        
        new_label = station
        
        new_labels[node] = new_label
        ground_stations[new_label] = station
    
    G.remove_nodes_from(nodes_to_remove)
    
    G = nx.relabel_nodes(G, new_labels)
    
    topology = Topology(existing_graph=G)

    for node_1, node_2, data in G.edges(data=True):
        if node_1 not in G.nodes() or node_2 not in G.nodes():
            G.remove_edge(node_1, node_2)
            
            continue
        
        
        link_speed = int(data.get('LinkSpeed',0))
        link_speed_unit = data.get('LinkLabel', 'M')
        
        bandwidth = link_speed if link_speed_unit == "M" else link_speed *1000

        link = NetworkLink()
        
        link['topology'] = topology
        link['nodes'] = [node_1, node_2]
        link['bandwidth'] = bandwidth
        link['delay'] = default_delay
        link['type'] = 'static'
        
        topology.add_edge(node_1, node_2, link=link)
        
        topology._adj[node_1][node_2] = link
        topology._adj[node_2][node_1] = link
        
        
    return topology