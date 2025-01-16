from torch_geometric.data import Dataset
import xml.etree.ElementTree as ET
from torch_geometric.data import Data
import torch

#TODO create class for matsim link to handle the link attrbutes

class MatsimXMLData(Dataset):
    def __init__(self, network_xml_path, charger_xml_path, transform=None):
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
        self.parse_matsim_network()

    def len(self):
        return len(self.data_list)

    def get(self, idx):
        return self.data_list[idx]
    
    def parse_matsim_network(self):
        tree = ET.parse(self.network_xml_path)
        root = tree.getroot()
        link_ids = []
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

        create_edge_attr_mapping = True
    
        for link in root.findall(".//link"):
            link_id = link.get("id")
            link_ids.append(link_id)
            from_node = link.get("from")
            to_node = link.get("to")
            from_idx = self.node_mapping[from_node]
            to_idx = self.node_mapping[to_node]
            edge_index.append([from_idx, to_idx])
            curr_link_attr = []
            attrib_id = 0

            for key, value in link.items():
                if value.isnumeric():
                    curr_link_attr.append(torch.tensor(float(value), dtype=torch.float))
                    if create_edge_attr_mapping:
                        self.edge_attr_mapping[attrib_id] = key
                        attrib_id += 1
            create_edge_attr_mapping = False
            edge_attr.append(curr_link_attr)

        self.graph.x = torch.tensor(node_ids).view(-1, 1)
        self.graph.pos = torch.tensor(node_pos)
        self.graph.edge_index = torch.tensor(edge_index).t()
        self.graph.edge_attr = torch.tensor(edge_attr)

    def get_graph(self):
        return self.graph


    
if __name__ == "__main__":
    network_xml_path = "/home/isaacp/repos/EvMatsim/contribs/ev/scenarios/utahev/utahevnetwork.xml"
    charger_xml_path = "/home/isaacp/repos/EvMatsim/contribs/ev/scenarios/utahev/utahevchargers.xml"
    dataset = MatsimXMLData(network_xml_path, charger_xml_path)
    print(dataset.node_mapping)