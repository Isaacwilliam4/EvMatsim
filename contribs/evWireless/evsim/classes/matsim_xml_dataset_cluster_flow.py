import xml.etree.ElementTree as ET
import shutil
import random
import numpy as np
from pathlib import Path
from evsim.scripts.util import setup_config
from bidict import bidict
from sklearn.cluster import KMeans
from evsim.scripts.util import save_xml, get_str
import torch

class ClusterFlowMatsimXMLDataset:
    """
    A dataset class for parsing MATSim XML files and creating a graph
    representation using PyTorch Geometric.
    """

    def __init__(
        self,
        config_path: Path,
        time_string: str,
        num_clusters: int,
    ):
        """
        Initializes the MatsimXMLDataset.

        Args:
            config_path (Path): Path to the MATSim configuration file.
            time_string (str): Unique identifier for temporary directories.
            num_agents (int): Number of agents to create. Default is 10000.
            initial_soc (float): Initial state of charge for agents. Default
                is 0.5.
        """
        # The grid with be split into grid_dim x grid_dim clusters
        self.num_clusters = num_clusters
        self.clusters = {}
        tmp_dir = Path("/tmp/" + time_string)
        output_path = Path(tmp_dir / "output")

        shutil.copytree(config_path.parent, tmp_dir)
        self.config_path = Path(tmp_dir / config_path.name)

        (
            network_file_name,
            plans_file_name,
            vehicles_file_name,
            chargers_file_name,
            counts_file_name
        ) = setup_config(self.config_path, str(output_path))

        self.charger_xml_path = Path(tmp_dir / chargers_file_name) if chargers_file_name else None
        self.network_xml_path = Path(tmp_dir / network_file_name) if network_file_name else None
        self.plan_xml_path = Path(tmp_dir / plans_file_name) if plans_file_name else None
        self.vehicle_xml_path = Path(tmp_dir / vehicles_file_name) if vehicles_file_name else None
        self.counts_xml_path = Path(tmp_dir / counts_file_name) if counts_file_name else None
        self.error_path = Path(tmp_dir / "errors.txt")

        self.node_mapping: bidict[str, int] = (
            bidict()
        )  #: Store mapping of node IDs to indices in the graph

        self.edge_mapping: bidict[str, int] = (
            bidict()
        )  #: (key:edge id, value: index in edge list)
        self.edge_attr_mapping: bidict[str, int] = (
            bidict()
        )  #: key: edge attribute name, value: index in edge attribute list
        self.parse_matsim_network()
        self.flow_tensor = np.random.rand(24, self.num_clusters, self.num_clusters).astype(np.float32)

    def write_to_error_log(self, message: str):
        """
        Writes an error message to the error log.

        Args:
            message (str): The error message to log.
        """
        with open(self.error_path, "a") as f:
            f.write(f"{message}\n")

    def parse_matsim_network(self):
        """
        Parses the MATSim network XML file and creates a clusters nodes based on kmeans.
        """
        tree = ET.parse(self.network_xml_path)
        root = tree.getroot()
        self.node_coords = {}
        node_coords_list = []

        for idx, node in enumerate(root.findall(".//node")):
            node_id = node.get("id")
            self.node_mapping[node_id] = idx
            curr_x = float(node.get("x"))
            curr_y = float(node.get("y"))
            node_coords_list.append([curr_x, curr_y])
            self.node_coords[node_id] = (curr_x, curr_y)
        
        kmeans = KMeans(n_clusters=self.num_clusters)
        kmeans.fit(np.array(node_coords_list))

        for idx, label in enumerate(kmeans.labels_):
            cluster_id = label
            if cluster_id not in self.clusters:
                self.clusters[cluster_id] = []
            self.clusters[cluster_id].append(idx)

        self.clusters = {k: v for k,v in sorted(self.clusters.items(), key=lambda x: x[0])}

    def generate_plans_from_flow_tensor(self):
        plans = ET.Element("plans", attrib={"xml:lang": "de-CH"})
        person_ids = []
        person_count = 1

        for hour in range(self.flow_tensor.shape[0]):
            for cluster1 in range(self.flow_tensor.shape[1]):
                for cluster2 in range(self.flow_tensor.shape[2]):
                    count = int(10**self.flow_tensor[hour][cluster1][cluster2])
                    for _ in range(count):
                        origin_node_idx = random.choice(
                            self.clusters[cluster1]
                        )
                        dest_node_idx = random.choice(
                            self.clusters[cluster2]
                        )
                        origin_node_id = self.node_mapping.inverse[origin_node_idx]
                        dest_node_id = self.node_mapping.inverse[dest_node_idx]
                        origin_node = self.node_coords[origin_node_id]
                        dest_node = self.node_coords[dest_node_id]
                        person = ET.SubElement(plans, "person", id=str(person_count))
                        person_ids.append(person_count)
                        person_count += 1
                        plan = ET.SubElement(person, "plan", selected="yes")
                        start_time = hour
                        end_time = (start_time + 8) % 24
                        start_time_str = (
                            f"0{start_time}:00:00" if start_time < 10 else f"{start_time}:00:00"
                        )
                        end_time_str = (
                            f"0{end_time}:00:00" if end_time < 10 else f"{end_time}:00:00"
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
        with open(self.plan_xml_path, "wb") as f:
            f.write(b'<?xml version="1.0" ?>\n')
            f.write(
                b'<!DOCTYPE plans SYSTEM "http://www.matsim.org/files/dtd/plans_v4.dtd">\n'
            )
            tree.write(f)

    def save_clusters(self, filepath):

        with open(filepath, "w") as f:
            for cluster_id, nodes in self.clusters.items():
                f.write(f"{cluster_id}:")
                for node_idx in nodes:
                    f.write(f"{self.node_mapping.inverse[node_idx]},")
                f.write('\n')

