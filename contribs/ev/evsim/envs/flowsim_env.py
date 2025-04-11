import gymnasium as gym
import numpy as np
import shutil
import torch
import zipfile
from gymnasium import spaces
from evsim.classes.flowsim_dataset import FlowSimDataset
from datetime import datetime
from pathlib import Path
from filelock import FileLock
import networkx as nx
import random

class FlowSimEnv(gym.Env):
    """
    A custom Gymnasium environment for Matsim graph-based simulations.
    """

    def __init__(self, config_path, counts_path, save_dir, num_clusters):
        """
        Initialize the environment.

        Args:
            config_path (str): Path to the configuration file.
            num_agents (int): Number of agents in the environment.
            save_dir (str): Directory to save outputs.
        """
        super().__init__()
        self.save_dir = save_dir
        current_time = datetime.now()
        self.time_string = current_time.strftime("%Y%m%d_%H%M%S_%f")

        # Initialize the dataset with custom variables
        self.config_path: Path = Path(config_path)
        self.counts_path: Path = Path(counts_path)
        self.error_path: Path = Path(self.save_dir, "errors")
        self.num_clusters = num_clusters

        self.dataset = FlowSimDataset(
            self.config_path,
            self.counts_path, 
            self.num_clusters
        )
        self.dataset.save_clusters(Path(self.save_dir, "clusters.txt"))
        self.reward: float = 0
        self.best_reward = -np.inf
        
        """
        The action represents the log_10 of the quantity of cars leaving every cluster at every hour,
        we limit it to -1 to 2 or 0.1 (0) to 100 cars per cluster per hour.
        """
        self.action_space : spaces.Box = spaces.Box(
            low=-1,
            high=2,
            shape=(24, self.dataset.num_clusters, self.dataset.num_clusters)
        )
        
        self.done: bool = False
        self.lock_file = Path(self.save_dir, "lockfile.lock")
        self.best_output_response = None

        self.observation_space: spaces.Box = spaces.Box(
            low=-1,
            high=2,
            shape=(24, self.dataset.num_clusters, self.dataset.num_clusters)
        )

        self.shortest_paths: dict[tuple, list] = dict()

    def reset(self, **kwargs):
        """
        Reset the environment to its initial state.

        Returns:
            np.ndarray: Initial state of the environment.
            dict: Additional information.
        """
        return self.dataset.flow_tensor, dict(info="info")


    def compute_reward(self, actions):
        result = torch.zeros(self.dataset.target_graph.edge_attr.shape)
        nx_graph = nx.DiGraph()
        nx_graph.add_nodes_from(self.dataset.target_graph.x.flatten().tolist())
        nx_graph.add_edges_from(self.dataset.target_graph.edge_index.t().tolist())
        for hour in range(actions.shape[0]):
            for cluster1 in range(actions.shape[1]):
                for cluster2 in range(actions.shape[2]):
                    if cluster1 != cluster2:
                        count = int(10**actions[hour][cluster1][cluster2])
                        for _ in range(count):
                            origin_node_idx = random.choice(
                                self.dataset.clusters[cluster1]
                            )
                            dest_node_idx = random.choice(
                                self.dataset.clusters[cluster2]
                            )
                            node_pair = (origin_node_idx, dest_node_idx)
                            if node_pair not in self.shortest_paths:
                                path = nx.shortest_path(nx_graph, origin_node_idx, dest_node_idx)
                                self.shortest_paths[node_pair] = path
                            else:
                                path = self.shortest_paths[node_pair]
                            result[path, hour] += 1

        res = 1 / (torch.log(((result[self.dataset.sensor_idxs, :] - 
                      self.dataset.target_graph.edge_attr[self.dataset.sensor_idxs, :])**2).sum() + 1) + 1)
        return res.item()


    def step(self, actions):
        """
        Take an action and return the next state, reward, done, and info.

        Args:
            actions (np.ndarray): Actions to take.

        Returns:
            tuple: Next state, reward, done flags, and additional info.
        """
        self.dataset.flow_tensor = actions
        self.reward = self.compute_reward(actions)
        if self.reward > self.best_reward:
            self.best_reward = self.reward

        return (
            self.dataset.flow_tensor,
            self.reward,
            self.done,
            self.done,
            dict(graph_env_inst=self),
        )

    
    def close(self):
        """
        Clean up resources used by the environment.

        This method is optional and can be customized.
        """
        shutil.rmtree(self.dataset.config_path.parent)

    def write_to_error(self, message):
        with open(self.error_path, "a") as f:
            f.write(message)


