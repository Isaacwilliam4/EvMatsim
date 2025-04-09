import gymnasium as gym
import numpy as np
import shutil
import torch
import requests
import json
import zipfile
import pandas as pd
from abc import abstractmethod
from gymnasium import spaces
from evsim.classes.matsim_xml_dataset_cluster_flow import ClusterFlowMatsimXMLDataset
from datetime import datetime
from pathlib import Path
from typing import List
from filelock import FileLock

1
class ClusterFlowMatsimGraphEnv(gym.Env):
    """
    A custom Gymnasium environment for Matsim graph-based simulations.
    """

    def __init__(self, config_path, num_agents=100, save_dir=None):
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
        if num_agents < 0:
            num_agents = None
        self.num_agents = num_agents

        # Initialize the dataset with custom variables
        self.config_path: Path = Path(config_path)

        self.dataset = ClusterFlowMatsimXMLDataset(
            self.config_path,
            self.time_string,
            10000,
            50
        )

        self.reward: float = 0
        self.best_reward = -np.inf
        
        self.action_space : spaces.Box = spaces.Box(
            low=0,
            high=np.inf,
            shape=(self.dataset.num_clusters, self.dataset.num_clusters, 24)
        )
        
        self.done: bool = False
        self.lock_file = Path(self.save_dir, "lockfile.lock")
        self.best_output_response = None

        self.observation_space: spaces.Box = spaces.Box(
            low=0,
            high=np.inf,
            shape=(self.dataset.num_clusters, self.dataset.num_clusters, 24)
        )

    def save_server_output(self, response, filetype):
        """
        Save server output to a zip file and extract its contents.

        Args:
            response (requests.Response): Server response object.
            filetype (str): Type of file to save.
        """
        zip_filename = Path(self.save_dir, f"{filetype}.zip")
        extract_folder = Path(self.save_dir, filetype)

        # Use a lock to prevent simultaneous access
        lock = FileLock(self.lock_file)

        with lock:
            # Save the zip file
            with open(zip_filename, "wb") as f:
                f.write(response.content)

            print(f"Saved zip file: {zip_filename}")

            # Extract the zip file
            with zipfile.ZipFile(zip_filename, "r") as zip_ref:
                zip_ref.extractall(extract_folder)

            print(f"Extracted files to: {extract_folder}")

    def send_reward_request(self):
        """
        Send a reward request to the server and process the response.

        Returns:
            tuple: Reward value and server response.
        """
        url = "http://localhost:8000/getReward"
        files = {
            "config": open(self.dataset.config_path, "rb"),
            "network": open(self.dataset.network_xml_path, "rb"),
            "plans": open(self.dataset.plan_xml_path, "rb"),
            # "vehicles": open(self.dataset.vehicle_xml_path, "rb"),
            "counts": open(self.dataset.counts_xml_path, "rb"),
        }
        response = requests.post(
            url, params={"folder_name": self.time_string}, files=files
        )
        json_response = json.loads(response.headers["X-response-message"])
        reward = json_response["reward"]
        filetype = json_response["filetype"]

        if filetype == "initialoutput":
            self.save_server_output(response, filetype)

        return float(reward), response

    def reset(self, **kwargs):
        """
        Reset the environment to its initial state.

        Returns:
            np.ndarray: Initial state of the environment.
            dict: Additional information.
        """
        return self.dataset.flow_tensor, dict(info="info")


    def step(self, actions):
        """
        Take an action and return the next state, reward, done, and info.

        Args:
            actions (np.ndarray): Actions to take.

        Returns:
            tuple: Next state, reward, done flags, and additional info.
        """
        action_type, action_vals = actions
        action_vals = torch.from_numpy(action_vals.reshape(-1, 24))
        if action_type == "quantity":
            self.dataset.graph.x[:,self.dataset.node_quantity_idx] = action_vals
        elif action_type == "node_probability":
            self.dataset.graph.x[:,self.dataset.node_stop_probability_idx] = action_vals
        elif action_type == "edge_probability":
            self.dataset.graph.edge_attr[:,self.dataset.edge_take_prob_idx] = action_vals

        flow_dist_reward, server_response = self.send_reward_request()
        self.reward = flow_dist_reward
        if self.reward > self.best_reward:
            self.best_reward = self.reward
            self.best_output_response = server_response

        return (
            dict(
            x=self.dataset.graph.x.numpy().astype(np.int32),
            edge_index=self.dataset.graph.edge_index.numpy().astype(np.int32),
            edge_attr=self.dataset.graph.edge_attr.numpy().astype(np.float32),
            ),
            self.reward,
            self.done,
            self.done,
            dict(graph_env_inst=self),
        )
    

    def get_ods(self):
        for hour in range(24):
            for node in self.dataset.graph.x:
                node_id = node[0].item()
                node_quantity = node[self.dataset.node_quantity_idx + hour].item()
                node_stop_probability = node[self.dataset.node_stop_probability_idx + hour].item()
                print(f"Node {node_id} Hour {hour}: Quantity = {node_quantity}, Stop Probability = {node_stop_probability}")
    
    def close(self):
        """
        Clean up resources used by the environment.

        This method is optional and can be customized.
        """
        shutil.rmtree(self.dataset.config_path.parent)

