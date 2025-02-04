import gymnasium as gym
from gymnasium import spaces
import numpy as np
from torch_geometric.data import Data
from evsim.classes.matsim_xml_dataset import MatsimXMLDataset
from torch_geometric.data import Dataset
from evsim.util import *
import shutil
from datetime import datetime
from pathlib import Path
import torch
import requests
from evsim.scripts.create_chargers import *
from evsim.classes.chargers import *
from typing import List
import os

class MatsimGraphEnv(gym.Env):
    def __init__(self, config_path):
        super().__init__()
        current_time = datetime.now()
        self.time_string = current_time.strftime("%Y%m%d_%H%M%S_%f")

        ########### Initialize the dataset with your custom variables ###########
        self.config_path: Path = Path(config_path)
        self.charger_list: List[Charger] = [NoneCharger, DynamicCharger, StaticCharger]
        self.dataset = MatsimXMLDataset(self.config_path, self.time_string, self.charger_list, num_agents=1, initial_soc=0.5)
        self.num_links_reward_scale = -10 #: this times the percentage of links that are chargers is added to your reward
        ########### Initialize the dataset with your custom variables ###########
        
        self.num_edges: int = self.dataset.graph.edge_attr.size(0)
        self.edge_space: int = self.dataset.graph.edge_attr.size(1)
        self.reward: int = 0
        self.num_charger_types: int = len(self.charger_list)
        # Define action and observation space
        # Example: Discrete action space with 3 actions
        self.action_space: spaces.MultiDiscrete = spaces.MultiDiscrete([self.num_charger_types] * self.num_edges)
        
        self.observation_space: spaces.Box = spaces.Box(
            low=0.0,                     # Minimum value for all features
            high=1.0,                    # Maximum value for all features
            shape=(self.num_edges, self.edge_space),   # Shape of the observation space
            dtype=np.float32             # Data type of the features
        )
        
        # Initialize environment-specific variables
        self.state: torch.tensor = self.dataset.graph.edge_attr
        self.done: bool = False

    def send_reward_request(self):
        url = "http://localhost:8000/getReward"
        files = {
            'config': open(self.dataset.config_path, 'rb'),
            'network': open(self.dataset.network_xml_path, 'rb'),
            'plans': open(self.dataset.plan_xml_path, 'rb'),
            'vehicles': open(self.dataset.vehicle_xml_path, 'rb'),
            'chargers': open(self.dataset.charger_xml_path, 'rb')
        }
        response = requests.post(url, params={'folder_name':self.time_string}, files=files)
        reward  = float(response.text.split(":")[1])
        return reward

    def reset(self, **kwargs):
        return self.state.numpy(), dict(reward=self.reward)

    def step(self, actions):
        """Take an action and return the next state, reward, done, and info."""

        create_chargers_xml_gymnasium(self.dataset.charger_xml_path, self.charger_list, actions, self.dataset.edge_mapping)
        self.dataset.parse_charger_network()
        reward = self.send_reward_request()
        self.state = self.dataset.graph.edge_attr
        reward += (self.num_links_reward_scale*(torch.sum(self.state[:, 4:]) / torch.sum(self.state[:, 3:])).item())
        print(f"Reward: {reward}, Process Id: {os.getpid()}")
        self.reward = reward
        return self.state.numpy(), reward, self.done, self.done, dict(reward=reward)

    def render(self):
        """Optional: Render the environment."""
        print(f"State: {self.state}")

    def close(self):
        """Optional: Clean up resources."""
        shutil.rmtree(self.dataset.config_path.parent)


if __name__ == "__main__":
    env = MatsimGraphEnv()
    sample = env.action_space.sample()
    env.step(env.action_space.sample())
    env.close()