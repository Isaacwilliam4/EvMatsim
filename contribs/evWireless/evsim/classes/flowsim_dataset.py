import xml.etree.ElementTree as ET
import torch
import shutil
from torch_geometric.data import Data
from pathlib import Path
from bidict import bidict
import numpy as np
from sklearn.cluster import KMeans
import networkx as nx

class FlowSimDataset:
    """
    A dataset class for parsing MATSim XML files and creating a graph
    representation using PyTorch Geometric.
    """

    def __init__(
        self,
        network_path: str,
        counts_path: str,
        num_clusters: int,
    ):
        """
        Initializes the MatsimXMLDataset.

        Args:
            config_path (Path): Path to the MATSim configuration file.
            time_string (str): Unique identifier for temporary directories.
            charger_list (list[Charger]): List of charger types.
            num_agents (int): Number of agents to create. Default is 10000.
            initial_soc (float): Initial state of charge for agents. Default
                is 0.5.
        """
        self.network_path = Path(network_path)
        self.sensor_path = Path(counts_path)
        self.plan_output_path = Path()
        self.num_clusters = num_clusters

        self.node_mapping: bidict[str, int] = (
            bidict()
        )  #: Store mapping of node IDs to indices in the graph

        self.edge_mapping: bidict[str, int] = (
            bidict()
        )  #: (key:edge id, value: index in edge list)
        self.edge_attr_mapping: bidict[str, int] = (
            bidict()
        )  #: key: edge attribute name, value: index in edge attribute list
        self.target_graph: Data = Data()
        self.parse_network()
        self.flow_tensor = torch.rand(24, num_clusters, num_clusters)

    def len(self):
        """
        Returns the length of the dataset.

        Returns:
            int: Length of the dataset.
        """
        return len(self.data_list)

    def _min_max_normalize(self, tensor, reverse=False):
        """
        Normalizes or denormalizes a tensor using min-max scaling.

        Args:
            tensor (Tensor): The tensor to normalize or denormalize.
            reverse (bool): Whether to reverse the normalization. Default
                is False.

        Returns:
            Tensor: The normalized or denormalized tensor.
        """
        if reverse:
            return tensor * (self.max_mins[1] - self.max_mins[0]) + self.max_mins[0]
        return (tensor - self.max_mins[0]) / (self.max_mins[1] - self.max_mins[0])

    def parse_network(self):
        """
        Parses the MATSim network XML file and creates a graph representation.
        """
        matsim_node_ids = []
        node_ids = []
        node_pos = []
        edge_index = []
        edge_attr = []
        node_coords_list = []
        self.node_coords = {}
        self.clusters = {}

        network_tree = ET.parse(self.network_path)
        network_root = network_tree.getroot()

        sensor_tree = ET.parse(self.sensor_path)
        sensor_root = sensor_tree.getroot()

        sensor_flows = {}

        for i, sensor in enumerate(sensor_root.findall("count")):
            sensor_id = sensor.get("loc_id")
            vols = []
            for volume in sensor.findall("volume"):
                val = int(volume.attrib["val"])
                vols.append(val)
            sensor_flows[sensor_id] = vols

        for i, node in enumerate(network_root.findall(".//node")):
            node_id = node.get("id")
            matsim_node_ids.append(node_id)
            node_pos.append([float(node.get("x")), float(node.get("y"))])
            self.node_mapping[node_id] = i
            node_ids.append(i)
            curr_x = float(node.get("x"))
            curr_y = float(node.get("y"))
            node_coords_list.append([curr_x, curr_y])
            self.node_coords[node_id] = (curr_x, curr_y)

        for idx, link in enumerate(network_root.findall(".//link")):
            from_node = link.get("from")
            to_node = link.get("to")
            from_idx = self.node_mapping[from_node]
            to_idx = self.node_mapping[to_node]
            edge_index.append([from_idx, to_idx])
            link_id = link.get("id")
            self.edge_mapping[link_id] = idx
            curr_edge_attr = [0 for _ in range(24)]
            if link_id in sensor_flows:
                curr_edge_attr = sensor_flows[link_id]
            edge_attr.append(curr_edge_attr)

        self.target_graph.x = torch.tensor(node_ids).view(-1, 1)
        self.target_graph.pos = torch.tensor(node_pos)
        self.target_graph.edge_index = torch.tensor(edge_index).t()
        self.target_graph.edge_attr = torch.tensor(edge_attr)
        self.state = self.target_graph.edge_attr

        kmeans = KMeans(n_clusters=self.num_clusters)
        kmeans.fit(np.array(node_coords_list))
        self.kmeans = kmeans

        for idx, label in enumerate(kmeans.labels_):
            cluster_id = label
            if cluster_id not in self.clusters:
                self.clusters[cluster_id] = []
            self.clusters[cluster_id].append(idx)

        self.clusters = {k: v for k,v in sorted(self.clusters.items(), key=lambda x: x[0])}
        self.sensor_idxs = [self.edge_mapping[edge_id] for edge_id in sensor_flows.keys()]


    def save_clusters(self, filepath):
        with open(filepath, "w") as f:
            for cluster_id, nodes in self.clusters.items():
                f.write(f"{cluster_id}:")
                for node_idx in nodes:
                    f.write(f"{self.node_mapping.inverse[node_idx]},")
                f.write('\n')



if __name__ == "__main__":
    n_path = "/home/isaacp/repos/EvMatsim/contribs/ev/scenario_examples/tinytown_scenario_example_flow/tiny_town_network.xml"
    c_path = "/home/isaacp/repos/EvMatsim/contribs/ev/scenario_examples/tinytown_scenario_example_flow/tiny_town_counts.xml" 
    flow = FlowSimDataset(n_path, c_path)