import numpy as np
import torch
from gymnasium.spaces import Box
from harl.envs.flowsim.flowsim_dataset import FlowSimDataset
from datetime import datetime
from pathlib import Path
import random
import xml.etree.ElementTree as ET
import os
from harl.envs.flowsim.cython.reward_core import sample_od_pairs
from harl.envs.flowsim.cython.cy_bfs import bfs

class FlowSimEnv:
    """
    A custom Gymnasium environment for Matsim graph-based simulations.
    """

    def __init__(self, network_path, counts_path, save_dir, num_clusters, seed, t=24, **kwargs):
        """
        Initialize the environment.

        Args:
            network_path (str): Path to the configuration file.
            num_agents (int): Number of agents in the environment.
            save_dir (str): Directory to save outputs.
        """
        # Initialize the dataset with custom variables
        self.t = t
        self.network_path: Path = Path(network_path)
        self.counts_path: Path = Path(counts_path)
        self.num_clusters = num_clusters
        # each agent monitors a single hour for every cluster
        self.n_agents = num_clusters*t

        self.dataset = FlowSimDataset(
            self.network_path,
            self.counts_path, 
            self.num_clusters
        )
        self.reward: float = 0
        self.best_reward = -np.inf
        
        """
        The action represents the log_10 of the quantity of cars leaving every cluster at every hour,
        we limit it to -1 to 2 or 0.1 (0) to 100 cars per cluster per hour.
        """

        self.done: bool = False
        self.best_output_response = None

        self.action_space : Box = self.repeat(
            Box(
                low=-1,
                high=1,
                shape=(self.num_clusters,)
            )
        )

        self.observation_space : Box = self.repeat(
            Box(
                low=-1,
                high=1,
                shape=(self.num_clusters,)
            )
        )

        self.share_observation_space : Box = \
            Box(
                low=-1,
                high=1,
                shape=(self.num_clusters * self.num_clusters * t,)
            )
        

        self.edge_index = self.dataset.target_graph.edge_index.t().numpy().astype(np.int32)
        self.num_nodes = len(self.dataset.target_graph.x)
        # shape (24, n_clusters, n_clusters)
        self.cluster_flow_tensor = np.random.rand(t, self.num_clusters, self.num_clusters)
        # shape (n_edges, 24)
        self.graph_flow_tensor = np.zeros_like(self.dataset.target_graph.edge_attr)

        self.target_flows = self.dataset.target_graph.edge_attr[self.dataset.sensor_idxs, :].numpy()

    def reset(self, **kwargs):
        """
        Reset the environment to its initial state.

        Returns:
            np.ndarray: Initial state of the environment.
            dict: Additional information.
        """
        return self.cluster_flow_tensor.reshape(self.t*self.num_clusters, self.num_clusters)


    def compute_reward(self):
        flows = np.round(self.cluster_flow_tensor, 0).astype(np.int32)
        self.od_result = sample_od_pairs(flows, self.dataset.clusters, self.num_clusters)
        self.graph_flow_tensor = np.zeros_like(self.dataset.target_graph.edge_attr)
        for (hour, origin_node_idx, dest_node_idx), count in self.od_result.items():
            edge_path = bfs(origin_node_idx, dest_node_idx, self.num_nodes, self.edge_index)
            self.graph_flow_tensor[edge_path, hour] += count

        pred_flows = self.graph_flow_tensor[self.dataset.sensor_idxs, :]
        abs_diff = np.abs(pred_flows - self.target_flows).sum()
        denominator = (np.log(abs_diff + 1) + 1)

        res = 1 / denominator

        return res
    

    def save_plans_from_flow_res(self, filepath:Path):
        if not os.path.exists(filepath.parent):
            os.makedirs(filepath.parent)

        if len(self.od_result) > 0:
            plans = ET.Element("plans", attrib={"xml:lang": "de-CH"})
            person_ids = []
            person_count = 1

            for (hour, origin_node_idx, dest_node_idx), count in self.od_result.items():
                origin_node_id = self.dataset.node_mapping.inverse[origin_node_idx]
                dest_node_id = self.dataset.node_mapping.inverse[dest_node_idx]
                origin_node = self.dataset.node_coords[origin_node_id]
                dest_node = self.dataset.node_coords[dest_node_id]
                start_time = hour
                end_time = (start_time + 8) % self.t

                for _ in range(count):
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

    def step(self, actions):
        """
        Take an action and return the next state, reward, done, and info.

        Args:
            actions (np.ndarray): Actions to take.

        Returns:
            tuple: Next state, reward, done flags, and additional info.
        """
        self.cluster_flow_tensor = actions.reshape(self.cluster_flow_tensor.shape)
        self.reward = self.compute_reward()
        if self.reward > self.best_reward:
            self.best_reward = self.reward

        return (
            self.cluster_flow_tensor.reshape(self.t*self.num_clusters, self.num_clusters),
            self.reward,
            self.done,
            dict(graph_env_inst=self),
        )

    def seed(self, seed: int):
        np.random.seed(seed)
        torch.random.manual_seed(seed)

    def repeat(self, a):
        return [a for _ in range(self.n_agents)]
    
    def split(self, a):
        return [a[i] for i in range(self.n_agents)]
