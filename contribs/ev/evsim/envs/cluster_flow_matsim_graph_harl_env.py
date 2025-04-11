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

    def __init__(self, config_path, save_dir=None, num_clusters=50):
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

        self.dataset = ClusterFlowMatsimXMLDataset(
            self.config_path,
            self.time_string,
            num_clusters=num_clusters
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
        try:
            self.dataset.flow_tensor = actions
            self.dataset.generate_plans_from_flow_tensor()
            flow_dist_reward, server_response = self.send_reward_request()
            self.reward = flow_dist_reward
            if self.reward > self.best_reward:
                self.best_reward = self.reward
                self.best_output_response = server_response

            return (
                self.dataset.flow_tensor,
                self.reward,
                self.done,
                self.done,
                dict(graph_env_inst=self),
            )
        except Exception as e:
            self.dataset.write_to_error_log(f"Error in step: {str(e)}")
            return (
                self.dataset.flow_tensor,
                -np.inf,
                True,
                True,
                dict(graph_env_inst=self),
            )
    
    def close(self):
        """
        Clean up resources used by the environment.

        This method is optional and can be customized.
        """
        shutil.rmtree(self.dataset.config_path.parent)

