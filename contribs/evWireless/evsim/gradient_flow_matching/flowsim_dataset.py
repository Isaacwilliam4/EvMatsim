import xml.etree.ElementTree as ET
import torch
from torch_geometric.data import Data
from pathlib import Path
from bidict import bidict
import numpy as np
from sklearn.cluster import KMeans
import os
import random
from tqdm import tqdm
from evsim.gradient_flow_matching.cython.get_TAM import get_TAM
from sklearn.metrics import pairwise_distances_argmin

class FlowSimDataset:
    """
    A dataset class for parsing MATSim XML files and creating a graph
    representation using PyTorch Geometric.
    """

    def __init__(
        self,
        output_path: str,
        network_path: str,
        counts_path: str,
        num_clusters: int
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

        self.output_path = output_path
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

        self.edge_index = self.target_graph.edge_index.t().numpy().astype(np.int32)
        self.centroid_idx = pairwise_distances_argmin(self.kmeans.cluster_centers_, self.target_graph.pos.numpy()).astype(np.int32)

        # traffic assignment matrix (TAM)
        self.build_TAM()

    def len(self):
        """
        Returns the length of the dataset.

        Returns:
            int: Length of the dataset.
        """
        return len(self.data_list)
    
    def build_TAM(self):
        tam_path = Path(self.output_path, f"{self.network_path.stem}_TAM_nclusters_{self.num_clusters}.npz")
        if not tam_path.exists():
            self.TAM = get_TAM(self.centroid_idx,
                            self.edge_index,
                            self.target_graph.num_nodes,
                            self.target_graph.num_edges,
                            self.num_clusters)
            np.savez(tam_path, TAM=self.TAM)
        else:
            self.TAM = np.load(tam_path)['TAM']

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


    def save_clusters(self, filepath:Path):
        if not os.path.exists(filepath.parent):
            os.makedirs(filepath.parent)
        with open(filepath, "w") as f:
            for cluster_id, nodes in self.clusters.items():
                f.write(f"{cluster_id}:")
                for node_idx in nodes:
                    f.write(f"{self.node_mapping.inverse[node_idx]},")
                f.write('\n')

    def save_plans_from_flow_res(self, flows:torch.Tensor, filepath:Path):
        """Generates MATSIM xml plans from the optimized flow tensor

        Args:
            flows (torch.Tensor): shape (n_clusters, n_clusters, 24)
            filepath (Path): path to save plans to 
        """

        if not os.path.exists(filepath.parent):
            os.makedirs(filepath.parent)

        
        plans = ET.Element("plans", attrib={"xml:lang": "de-CH"})
        person_ids = []
        person_count = 1

        pbar = tqdm(range(flows.numel()), desc="Saving XML file")

        for cluster1 in range(flows.shape[0]):
            for cluster2 in range(flows.shape[1]):
                for hour in range(flows.shape[2]):
                    pbar.update(1)
                    count = flows[cluster1, cluster2, hour].to(torch.int64)
                    for _ in range(count):
                        origin_node_idx = random.choice(self.clusters[cluster1]) 
                        dest_node_idx = random.choice(self.clusters[cluster2]) 
                        origin_node_id = self.node_mapping.inverse[origin_node_idx]
                        dest_node_id = self.node_mapping.inverse[dest_node_idx]
                        origin_node = self.node_coords[origin_node_id]
                        dest_node = self.node_coords[dest_node_id]
                        start_time = hour
                        end_time = (start_time + 8) % 24
                        person = ET.SubElement(plans, "person", id=str(person_count))
                        person_ids.append(person_count)
                        person_count += 1
                        plan = ET.SubElement(person, "plan", selected="yes")

                        minute = random.randint(0,59)
                        minute_str = "0" + str(minute) if minute < 10 else str(minute)
                        start_time_str = (
                            f"0{start_time}:{minute_str}:00" if start_time < 10 else f"{start_time}:{minute_str}:00"
                        )
                        end_time_str = (
                            f"0{end_time}:{minute_str}:00" if end_time < 10 else f"{end_time}:{minute_str}:00"
                        )
                        ET.SubElement(
                            plan,
                            "act",
                            type="h",
                            x=str(origin_node[0]),
                            y=str(origin_node[1]),
                            end_time=start_time_str,
                        )
                        ET.SubElement(plan, "leg", mode="car")
                        ET.SubElement(
                            plan,
                            "act",
                            type="h",
                            x=str(dest_node[0]),
                            y=str(dest_node[1]),
                            start_time=start_time_str,
                            end_time=end_time_str,
                        )

        tree = ET.ElementTree(plans)
        with open(filepath, "wb") as f:
            f.write(b'<?xml version="1.0" ?>\n')
            f.write(
                b'<!DOCTYPE plans SYSTEM "http://www.matsim.org/files/dtd/plans_v4.dtd">\n'
            )
            tree.write(f)