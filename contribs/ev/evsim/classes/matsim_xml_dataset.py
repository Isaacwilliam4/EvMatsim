from torch_geometric.data import Dataset
from torch_geometric.transforms import LineGraph
import xml.etree.ElementTree as ET
from torch_geometric.data import Data
import torch
from pathlib import Path
from evsim.util import *
import shutil
from bidict import bidict
from evsim.classes.chargers import *
from evsim.scripts.create_population import *
import pandas
import os
#TODO create class for matsim link to handle the link attrbutes

class MatsimXMLDataset(Dataset):
    def __init__(self, config_path:Path, time_string:str, charger_list:list[Charger], num_agents:int=10000, initial_soc:float=0.5):
        super().__init__(transform=None)

        tmp_dir = Path("/tmp/" + time_string)
        output_path = Path(tmp_dir / "output")

        shutil.copytree(config_path.parent, tmp_dir)

        self.config_path = Path(tmp_dir / config_path.name)

        network_file_name, \
        plans_file_name, \
        vehicles_file_name, \
        chargers_file_name = setup_config(self.config_path, str(output_path))
        
        self.charger_xml_path = Path(tmp_dir / chargers_file_name)
        self.network_xml_path = Path(tmp_dir / network_file_name)
        self.plan_xml_path = Path(tmp_dir / plans_file_name)
        self.vehicle_xml_path = Path(tmp_dir / vehicles_file_name)

        self.node_mapping: bidict[str,int] = bidict()#: Store mapping of node IDs to indices in the graph
        
        self.edge_mapping: bidict[str,int] = bidict()#: (key:edge id, value: index in edge list)
        self.edge_attr_mapping: bidict[str,int] = bidict()#: key: edge attribute name, value: index in edge attribute list
        self.graph: Data = Data()
        self.charger_list = charger_list
        self.num_charger_types = len(self.charger_list)
        self.max_charger_cost = 0
        self.linegraph_transform = LineGraph()
        if num_agents:
            create_population_and_plans_xml_counts(self.network_xml_path, self.plan_xml_path,\
                                                self.vehicle_xml_path, num_agents=num_agents, initial_soc=initial_soc)
        self.create_edge_attr_mapping()
        self.parse_matsim_network()
        self.parse_charger_network_get_charger_cost()

        # preserve the mins and maxes for reward calculations later
        self.max_mins = torch.stack([torch.min(self.graph.edge_attr[:,:3], dim=0).values, torch.max(self.graph.edge_attr[:,:3], dim=0).values])

        self.graph.edge_attr[:,:3] = self._min_max_normalize(self.graph.edge_attr[:,:3])
        self.state = self.graph.edge_attr

    def len(self):
        return len(self.data_list)

    def get(self, idx):
        return self.data_list[idx]
    
    def _min_max_normalize(self, tensor, reverse=False):
        if reverse:
            return tensor * (self.max_mins[1] - self.max_mins[0]) + self.max_mins[0]
        return (tensor - self.max_mins[0]) / (self.max_mins[1] - self.max_mins[0])
    
    def create_edge_attr_mapping(self):
        self.edge_attr_mapping = {'length': 0, 'freespeed': 1, 'capacity': 2}
        edge_attr_idx = len(self.edge_attr_mapping)
        for charger in self.charger_list:
            self.edge_attr_mapping[charger.type] = edge_attr_idx
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
                    if key == 'length':
                        """
                        add the cost of either the static charger or the dynamic charger times the length of the link
                        which we conver to km from m
                        """
                        link_len_km = float(link.get(key))*.001
                        self.max_charger_cost += max(StaticCharger.price, DynamicCharger.price*link_len_km)
                    curr_link_attr[value] = float(link.get(key))

            edge_attr.append(curr_link_attr)

        self.graph.x = torch.tensor(node_ids).view(-1, 1)
        self.graph.pos = torch.tensor(node_pos)
        self.graph.edge_index = torch.tensor(edge_index).t()
        self.graph.edge_attr = torch.stack(edge_attr)
        self.linegraph = self.linegraph_transform(self.graph)


    def parse_charger_network_get_charger_cost(self):
        cost = 0
        tree = ET.parse(self.charger_xml_path)
        root = tree.getroot()

        # reset the values of the charger placements TODO: make this dynamic to edge attributes
        self.graph.edge_attr[:,3:] = torch.zeros(self.graph.edge_attr.shape[0], self.graph.edge_attr[:,3:].shape[1])

        for charger in root.findall(".//charger"):
            link_id = charger.get("link")
            charger_type = charger.get("type") 
            if charger_type is None:
                charger_type = StaticCharger.type
            
            if charger_type == StaticCharger.type:
                cost += StaticCharger.price
            elif charger_type == DynamicCharger.type:
                link_idx = self.edge_mapping[link_id]
                link_len_km = self.graph.edge_attr[link_idx][self.edge_attr_mapping['length']] * .001
                cost += DynamicCharger.price * link_len_km

            self.graph.edge_attr[self.edge_mapping[link_id]][self.edge_attr_mapping[charger_type]] = 1

        # update the rest of the links to have no charger
        tree = ET.parse(self.network_xml_path)
        root = tree.getroot()
        for link in root.findall(".//link"):
            link_id = link.get("id")

            if not (self.graph.edge_attr[self.edge_mapping[link_id]][self.edge_attr_mapping['default']] == 1 or\
            self.graph.edge_attr[self.edge_mapping[link_id]][self.edge_attr_mapping['dynamic']] == 1):
                self.graph.edge_attr[self.edge_mapping[link_id]][self.edge_attr_mapping['none']] = 1
    
        return cost
    
    def get_graph(self):
        return self.graph