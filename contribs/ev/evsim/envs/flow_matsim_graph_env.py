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
from evsim.classes.matsim_xml_dataset_flow import FlowMatsimXMLDataset
from datetime import datetime
from pathlib import Path
from evsim.classes.chargers import Charger, StaticCharger, NoneCharger, DynamicCharger
from typing import List
from filelock import FileLock


class FlowMatsimGraphEnv(gym.Env):
    """
    A custom Gymnasium environment for Matsim graph-based simulations.
    """

    def __init__(self, config_path, num_agents=100, save_dir=None, max_extracted:int=100):
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
        self.charger_list: List[Charger] = [
            NoneCharger,
            DynamicCharger,
            StaticCharger,
        ]
        self.dataset = FlowMatsimXMLDataset(
            self.config_path,
            self.time_string,
            self.charger_list,
            num_agents=self.num_agents,
            initial_soc=0.5,
        )
        self.max_extracted = max_extracted
        self.num_links_reward_scale = -100
        self.reward: float = 0
        self.best_reward = -np.inf
        self.num_charger_types: int = len(self.charger_list)

        self.actions : spaces.Box = spaces.Box(
            low=0,
            high=np.inf,
            shape=(24*self.max_extracted,),
            dtype=np.int32,
        )

        self.link_ids : spaces.Box = spaces.Box(
            low=0,
            high=np.inf,
            shape=(self.max_extracted,),
            dtype=np.int32,
        )

        # Define action and observation space
        self.action_space: spaces.Dict = spaces.Dict(
            spaces={
                "actions": self.actions,
                "link_ids": self.link_ids,
            }
        )
        self.x = spaces.Box(
            low=0,
            high=np.inf,
            shape=self.dataset.graph.x.shape,
            dtype=np.int32,
        )
        self.edge_index = self.dataset.graph.edge_index.to(torch.int32)
        edge_index_np = self.edge_index.numpy()
        max_edge_index = np.max(edge_index_np) + 1
        self.edge_index_space = spaces.Box(
            low=edge_index_np,
            high=np.full(edge_index_np.shape, max_edge_index),
            shape=self.edge_index.shape,
            dtype=np.int32,
        )
        self.done: bool = False
        self.lock_file = Path(self.save_dir, "lockfile.lock")
        self.best_output_response = None

        self.observation_space: spaces.Dict = spaces.Dict(
            spaces=dict(x=self.x, edge_index=self.edge_index_space)
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
        return dict(
            x=self.dataset.graph.x.numpy(),
            edge_index=self.dataset.graph.edge_index.numpy().astype(np.int32),
        ), dict(info="info")


    def step(self, actions):
        """
        Take an action and return the next state, reward, done, and info.

        Args:
            actions (np.ndarray): Actions to take.

        Returns:
            tuple: Next state, reward, done flags, and additional info.
        """

        flow_dist_reward, server_response = self.send_reward_request()
        self.reward = flow_dist_reward
        if self.reward > self.best_reward:
            self.best_reward = self.reward
            self.best_output_response = server_response

        return (
            self.dataset.linegraph.x.numpy(),
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

