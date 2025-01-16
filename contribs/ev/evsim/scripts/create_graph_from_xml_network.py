from torch_geometric.data import Dataset
import xml.etree.ElementTree as ET
from torch_geometric.data import Data
import torch

#TODO create class for matsim link to handle the link attrbutes

class MatsimXMLData(Dataset):
    def __init__(self, network_xml_path, charger_xml_path, charger_dict, transform=None):
        super().__init__(transform=transform)
        self.network_xml_path = network_xml_path
        self.charger_xml_path = charger_xml_path
        self.data_list = []  # Store Data objects
        # Store mapping of node IDs to indices in the graph
        self.node_mapping = {}
        # Store mapping of edge IDs to indices in the graph
        self.edge_mapping = {}
        self.edge_attr_mapping = {}
        self.graph = Data()
        self.charger_dict = charger_dict
        self.num_charger_types = len(charger_dict)
        self.parse_matsim_network()

    def len(self):
        return len(self.data_list)

    def get(self, idx):
        return self.data_list[idx]
    
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

        for i, node in enumerate(root.findall(".//node")):
            node_id = node.get("id")
            matsim_node_ids.append(node_id)
            node_pos.append([float(node.get("x")), float(node.get("y"))])
            self.node_mapping[node_id] = i
            node_ids.append(i)

        create_edge_attr_mapping = True

        first_link = root.find(".//link")
        link_attr = len(first_link.items())

        for i, key in enumerate(first_link.items()):
            self.edge_attr_mapping[key] = i

        for i, key in enumerate(self.charger_dict.keys()):
            self.edge_attr_mapping[key] = i + len(first_link.items())
    
        for i, link in enumerate(root.findall(".//link")):
            link_id = link.get("id")
            from_node = link.get("from")
            to_node = link.get("to")
            from_idx = self.node_mapping[from_node]
            to_idx = self.node_mapping[to_node]
            edge_index.append([from_idx, to_idx])
            curr_link_attr = []

            for key, value in link.items():
                if value.isnumeric():
                    curr_link_attr.append(torch.tensor(float(value), dtype=torch.float))


        self.graph.x = torch.tensor(node_ids).view(-1, 1)
        self.graph.pos = torch.tensor(node_pos)
        self.graph.edge_index = torch.tensor(edge_index).t()
        self.graph.edge_attr = torch.tensor(edge_attr)

    def parse_charger_network(self):
        tree = ET.parse(self.network_xml_path)
        root = tree.getroot()

        for charger in root.findall(".//charger"):
            link_id = charger.get("link")
            charger_type = charger.get("type")

             
            self.graph.edge_attr[self.edge_mapping[link_id]]
        

    def get_graph(self):
        return self.graph


    
if __name__ == "__main__":
    network_xml_path = "/home/isaacp/repos/EvMatsim/contribs/ev/scenarios/utahev/utahevnetwork.xml"
    charger_xml_path = "/home/isaacp/repos/EvMatsim/contribs/ev/scenarios/utahev/utahevchargers.xml"
    charger_dict = {
        "none": 0,
        # in matsim the default charger is a static charger we could update this dictionary
        # to include different charger types along with charger cost and other attributes
        # the graph uses this dictionary to map the charger type to an integer
        "default": 1,
        "dynamic": 2
    }
    dataset = MatsimXMLData(network_xml_path, charger_xml_path, charger_dict)
    print(dataset.node_mapping)