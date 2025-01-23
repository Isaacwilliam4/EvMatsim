from torch_geometric.data import Dataset
import xml.etree.ElementTree as ET
from torch_geometric.data import Data
import torch

#TODO create class for matsim link to handle the link attrbutes

class MatsimXMLDataset(Dataset):
    def __init__(self, network_xml_path, charger_xml_path, charger_dict, transform=None):
        super().__init__(transform=transform)
        self.network_xml_path = network_xml_path
        self.charger_xml_path = charger_xml_path
        self.data_list = []  # Store Data objects
        
        self.node_mapping = {}#: Store mapping of node IDs to indices in the graph
        
        self.edge_mapping = {}#: (key:edge id, value: index in edge list)
        self.edge_attr_mapping = {}
        self.graph = Data()
        self.charger_dict = charger_dict
        self.num_charger_types = len(charger_dict)
        self.create_edge_attr_mapping()
        self.parse_matsim_network()
        self.parse_charger_network()

    def len(self):
        return len(self.data_list)

    def get(self, idx):
        return self.data_list[idx]
    
    def create_edge_attr_mapping(self):
        self.edge_attr_mapping = {'length': 0, 'freespeed': 1, 'capacity': 2, 'permlanes': 3, 'oneway': 4}
        edge_attr_idx = len(self.edge_attr_mapping)
        for key in self.charger_dict:
            self.edge_attr_mapping[key] = edge_attr_idx
            edge_attr_idx += 1
    
    def parse_matsim_network(self):
        """Parse the matsim network provided via the self.network_xml_path and creates a
        torch_geometric.data.Data object with the network information. Then assigns the 
        Data object to self.graph.
        """
        tree = ET.parse(self.network_xml_path)
        root = tree.getroot()
        matsim_node_ids = []
        node_ids = []
        node_pos = []
        edge_index = []
        edge_attr = []

        for i, node in enumerate(root.findall(".//node")):
            node_id = node.get("id")
            matsim_node_ids.append(node_id)
            node_pos.append([float(node.get("x")), float(node.get("y"))])
            self.node_mapping[node_id] = i
            node_ids.append(i)


        tot_attr = len(self.edge_attr_mapping)

        for i, link in enumerate(root.findall(".//link")):
            from_node = link.get("from")
            to_node = link.get("to")
            from_idx = self.node_mapping[from_node]
            to_idx = self.node_mapping[to_node]
            edge_index.append([from_idx, to_idx])
            curr_link_attr = torch.zeros(tot_attr)
            self.edge_mapping[link.get("id")] = i

            for key, value in self.edge_attr_mapping.items():
                if key in link.attrib:
                    curr_link_attr[value] = float(link.get(key))

            edge_attr.append(curr_link_attr)

        self.graph.x = torch.tensor(node_ids).view(-1, 1)
        self.graph.pos = torch.tensor(node_pos)
        self.graph.edge_index = torch.tensor(edge_index).t()
        self.graph.edge_attr = torch.stack(edge_attr)

    def parse_charger_network(self):
        tree = ET.parse(self.charger_xml_path)
        root = tree.getroot()

        for charger in root.findall(".//charger"):
            link_id = charger.get("link")
            charger_type = charger.get("type") 
            if charger_type is None:
                charger_type = "default"
             
            self.graph.edge_attr[self.edge_mapping[link_id]][self.edge_attr_mapping[charger_type]] = 1

        # update the rest of the links to have no charger
        tree = ET.parse(self.network_xml_path)
        root = tree.getroot()
        for link in root.findall(".//link"):
            link_id = link.get("id")

            if not (self.graph.edge_attr[self.edge_mapping[link_id]][self.edge_attr_mapping['default']] == 1 or\
            self.graph.edge_attr[self.edge_mapping[link_id]][self.edge_attr_mapping['dynamic']] == 1):
                self.graph.edge_attr[self.edge_mapping[link_id]][self.edge_attr_mapping['none']] = 1
        

    def get_graph(self):
        return self.graph


    
if __name__ == "__main__":
    network_xml_path = "/home/isaacp/repos/EvMatsim/contribs/ev/script_scenarios/utahevscenario/utahevnetwork.xml"
    charger_xml_path = "/home/isaacp/repos/EvMatsim/contribs/ev/script_scenarios/utahevscenario/utahevchargers.xml"
    charger_dict = {
        "none": 0,
        # in matsim the default charger is a static charger we could update this dictionary
        # to include different charger types along with charger cost and other attributes
        # the graph uses this dictionary to map the charger type to an integer
        "default": 1,
        "dynamic": 2
    }
    dataset = MatsimXMLDataset(network_xml_path, charger_xml_path, charger_dict)
    graph : Data = dataset.get_graph()
    torch.save(graph, '/home/isaacp/repos/EvMatsim/contribs/ev/data/utah_graph.pt')
    print(graph)