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
    def __init__(self, config_path, num_agents=100):
        super().__init__()
        current_time = datetime.now()
        self.time_string = current_time.strftime("%Y%m%d_%H%M%S_%f")
        if num_agents < 0:
            num_agents = None
        self.num_agents = num_agents

        ########### Initialize the dataset with your custom variables ###########
        self.config_path: Path = Path(config_path)
        self.charger_list: List[Charger] = [NoneCharger, DynamicCharger, StaticCharger]
        self.dataset = MatsimXMLDataset(self.config_path, 
                                        self.time_string, 
                                        self.charger_list, 
                                        num_agents=self.num_agents, 
                                        initial_soc=0.5)
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
        return self.state.numpy(), dict(graph_env_inst=self)

    def step(self, actions):
        """Take an action and return the next state, reward, done, and info."""

        create_chargers_xml_gymnasium(self.dataset.charger_xml_path, self.charger_list, actions, self.dataset.edge_mapping)
        self.dataset.parse_charger_network()
        reward = self.send_reward_request()
        self.state = self.dataset.graph.edge_attr
        num_chargers_reward = (self.num_links_reward_scale*(torch.sum(self.state[:, 4:]) / torch.sum(self.state[:, 3:])).item())
        reward += num_chargers_reward
        self.reward = reward
        return self.state.numpy(), reward, self.done, self.done, dict(graph_env_inst=self)

    def render(self):
        """Optional: Render the environment."""
        print(f"State: {self.state}")

    def close(self):
        """Optional: Clean up resources."""
        shutil.rmtree(self.dataset.config_path.parent)

    def save_charger_config_to_csv(self, csv_path):
        """Saves the current configuration with the chargers and their
        link ids to the specifies csv path, overwrites the path if it
        exists

        Args:
            csv_path (str): Path where to save the csv
        """
        static_chargers = []
        dynamic_chargers = []
        charger_config = self.state[:, 3:]

        for idx,row in enumerate(charger_config):
            if not row[0]:
                if row[1]:
                    static_chargers.append(int(self.dataset.edge_mapping.inverse[idx]))
                elif row[2]:
                    dynamic_chargers.append(int(self.dataset.edge_mapping.inverse[idx]))

        df = pd.DataFrame({'iteration':[0],'reward':[self.reward], 'static_chargers':[static_chargers], 'dynamic_chargers':[dynamic_chargers]})
        df.to_csv(csv_path, index=False)


if __name__ == "__main__":
    env = MatsimGraphEnv(config_path="/home/isaacp/EvMatsim/contribs/ev/script_scenarios/utahevscenario/utahevconfig.xml")
    sample = env.action_space.sample()
    env.save_charger_config_to_csv(Path(Path(__file__).parent, 'test_save_charger.csv'))
    env.close()