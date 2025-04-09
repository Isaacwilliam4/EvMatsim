import xml.etree.ElementTree as ET
import shutil
from pathlib import Path
from evsim.scripts.util import setup_config
from bidict import bidict
from sklearn.cluster import KMeans
import numpy as np

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
        super().__init__(transform=None)
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
        self.flow_tensor = np.random.rand((self.num_clusters, self.num_clusters, 24))

    def parse_matsim_network(self):
        """
        Parses the MATSim network XML file and creates a clusters nodes based on kmeans.
        """
        tree = ET.parse(self.network_xml_path)
        root = tree.getroot()
        node_coords = []

        for idx, node in enumerate(root.findall(".//node")):
            node_id = node.get("id")
            self.node_mapping[node_id] = idx
            curr_x = float(node.get("x"))
            curr_y = float(node.get("y"))
            node_coords.append([curr_x, curr_y])
        
        kmeans = KMeans(n_clusters=self.num_clusters)
        kmeans.fit(np.array(node_coords))

        for idx, label in enumerate(kmeans.labels_):
            cluster_id = label
            if cluster_id not in self.clusters:
                self.clusters[cluster_id] = []
            self.clusters[cluster_id].append(idx)

        self.clusters = {k: v for k,v in sorted(self.clusters.items(), key=lambda x: x[0])}

    def save_clusters(self, filepath):

        with open(filepath, "w") as f:
            for cluster_id, nodes in self.clusters.items():
                f.write(f"{cluster_id}:")
                for node_idx in nodes:
                    f.write(f"{self.node_mapping.inverse[node_idx]},")
                f.write('\n')

