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



class MatsimGraphEnv(gym.Env):
    def __init__(self):
        super().__init__()
        current_time = datetime.now()
        self.time_string = current_time.strftime("%Y%m%d_%H%M%S_%f")
        self.config_path = Path("/home/isaacp/repos/EvMatsim/contribs/ev/scenario_examples/utahev_scenario_example/utahevconfig.xml")

        self.charger_list = ['none', 'default', 'dynamic']

        self.dataset = MatsimXMLDataset(self.config_path, self.time_string, self.charger_list)

        self.num_edges, self.edge_space = self.dataset.graph.edge_index.size(1), self.dataset.graph.edge_attr.size(1) 
        self.num_charger_types = len(self.charger_list)
        # Define action and observation space
        # Example: Discrete action space with 3 actions
        self.action_space = spaces.MultiDiscrete([self.num_charger_types] * self.num_edges)
        
        self.observation_space = spaces.Box(
            low=0.0,                     # Minimum value for all features
            high=1.0,                    # Maximum value for all features
            shape=(self.num_edges, self.edge_space),   # Shape of the observation space
            dtype=np.float32             # Data type of the features
        )
        
        # Initialize environment-specific variables
        self.state = self.dataset.graph.edge_attr
        self.done = False

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

    def reset(self):
        pass

    def step(self, action):
        """Take an action and return the next state, reward, done, and info."""


        reward = self.send_reward_request()

        
        
        return self.state, reward, self.done, info

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