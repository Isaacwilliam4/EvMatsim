import xml.etree.ElementTree as ET
import torch
import shutil
from torch_geometric.data import Dataset
from torch_geometric.transforms import LineGraph
from torch_geometric.data import Data
from pathlib import Path
from evsim.scripts.util import setup_config
from bidict import bidict
from evsim.scripts.create_population_ev import create_population_and_plans_xml_counts


class StatFlowMatsimXMLDataset(Dataset):
    """
    A dataset class for parsing MATSim XML files and creating a graph
    representation using PyTorch Geometric.
    """

    def __init__(
        self,
        config_path: Path,
        time_string: str,
        num_agents: int = 10000,
        initial_soc: float = 0.5,
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

        self.max_agents = 10000
        self.node_id_idx = 0
        self.node_stop_probability_idx = slice(1, 25)
        self.node_quantity_idx = slice(25, 49)

        self.edge_length_idx = 0
        self.edge_freespeed_idx = 1
        self.edge_capacity_idx = 2
        self.edge_take_prob_idx = slice(3, 27)


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
        self.consumption_map_path = Path(tmp_dir / "consumption_map.csv")


        self.node_mapping: bidict[str, int] = (
            bidict()
        )  #: Store mapping of node IDs to indices in the graph

        self.edge_mapping: bidict[str, int] = (
            bidict()
        )  #: (key:edge id, value: index in edge list)
        self.edge_attr_mapping: bidict[str, int] = (
            bidict()
        )  #: key: edge attribute name, value: index in edge attribute list
        self.graph: Data = Data()
        self.linegraph_transform = LineGraph()
        self.create_edge_attr_mapping()
        self.parse_matsim_network()

    def len(self):
        """
        Returns the length of the dataset.

        Returns:
            int: Length of the dataset.
        """
        return len(self.data_list)

    def get(self, idx):
        """
        Retrieves the data object at the specified index.

        Args:
            idx (int): Index of the data object.

        Returns:
            Data: The data object at the specified index.
        """
        return self.data_list[idx]

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
        x_min = tensor.min(dim=0).values
        x_max = tensor.max(dim=0).values
        return (tensor - x_min) / (x_max - x_min)

    def create_edge_attr_mapping(self):
        """
        Creates a mapping of edge attributes to their indices.
        """
        self.edge_attr_mapping = {"length": 0, "freespeed": 1, "capacity": 2}

    def parse_matsim_network(self):
        """
        Parses the MATSim network XML file and creates a graph representation.
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

        num_nodes = len(node_ids)
        node_ids = torch.tensor(node_ids).view(-1, 1)
        node_probs = torch.rand((num_nodes, 24), dtype=torch.float)
        node_quantity = torch.softmax(torch.rand_like(node_probs, dtype=torch.float), dim=0)
        """
        self.graph.x.shape = (num_nodes, 49), 
        [:,0] = node ids, 
        [:,1-24] = node stop probabilities for every hour of the day, 
        [:,25-49] = node quantities for every hour of the day
        """
        self.graph.x = torch.cat([node_ids, node_probs, node_quantity], dim=1)
        edge_attr = torch.stack(edge_attr)
        edge_take_probabilities = torch.rand((len(edge_attr[:,0]), 24), dtype=torch.float)
        self.graph.pos = torch.tensor(node_pos)
        self.graph.edge_index = torch.tensor(edge_index).t()
        """ 
        self.graph.edge_attr.shape = (num_edges, 27)
        [:,0] = edge length,
        [:,1] = edge freespeed,
        [:,2] = edge capacity,
        [:,3-27] = edge take probabilities for every hour of the day
        """
        self.graph.edge_attr = torch.cat((edge_attr, edge_take_probabilities), dim=1)
        self.linegraph: Data = self.linegraph_transform(self.graph)

        self.graph.edge_attr[:,:3] = self._min_max_normalize(
            self.graph.edge_attr[:,:3]
        )
        self.state = self.graph.edge_attr


    def get_graph(self):
        """
        Returns the graph representation of the MATSim network.

        Returns:
            Data: The graph representation.
        """
        return self.graph
