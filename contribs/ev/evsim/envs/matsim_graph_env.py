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
import json
import zipfile

class MatsimGraphEnv(gym.Env):
    def __init__(self, config_path, num_agents=100, save_dir=None):
        super().__init__()
        self.save_dir = save_dir
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
        self.num_links_reward_scale = -100 #: this times the percentage of links that are chargers is added to your reward
        ########### Initialize the dataset with your custom variables ###########
        
        # self.num_edges: int = self.dataset.linegraph.edge_attr.size(0)
        # self.edge_space: int = self.dataset.linegraph.edge_attr.size(1)
        self.reward: int = 0
        self.num_charger_types: int = len(self.charger_list)
        # Define action and observation space
        # Example: Discrete action space with 3 actions
        
        self.action_space: spaces.MultiDiscrete = spaces.MultiDiscrete([self.num_charger_types] * self.dataset.linegraph.num_nodes)
        self.x = spaces.Box(low=0, high=1, shape=self.dataset.linegraph.x.shape, dtype=np.float32)
        self.edge_index = self.dataset.linegraph.edge_index.to(torch.int32)
        self.edge_index_space = spaces.Box(low=self.edge_index.numpy(), high=self.edge_index.numpy(), shape=self.edge_index.shape, dtype=np.int32)

        self.observation_space: spaces.Dict = spaces.Dict(
            spaces=dict(x=self.x, edge_index=self.edge_index_space)
        )
        
        # Initialize environment-specific variables
        self.state = self.observation_space
        self.done: bool = False

    def save_server_output(self, response, filetype):
        zip_filename = Path(self.save_dir, f"{filetype}.zip") 
        extract_folder = Path(self.save_dir, filetype)

        # Save the zip file
        with open(zip_filename, "wb") as f:
            f.write(response.content)

        print(f"Saved zip file: {zip_filename}")

        # Extract the zip file
        with zipfile.ZipFile(zip_filename, "r") as zip_ref:
            zip_ref.extractall(extract_folder)

        print(f"Extracted files to: {extract_folder}")


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
        #idx:0=reward, idx:1=output if any
        json_response = json.loads(response.headers['X-response-message'])
        reward = json_response['reward']
        filetype = json_response['filetype']

        if filetype != 'none':
            self.save_server_output(response, filetype)

        return float(reward)

    def reset(self, **kwargs):
        return dict(x=self.dataset.linegraph.x, edge_index=self.edge_index), dict(info="info")

    def step(self, actions):
        """Take an action and return the next state, reward, done, and info."""

        create_chargers_xml_gymnasium(self.dataset.charger_xml_path, self.charger_list, actions, self.dataset.edge_mapping)
        charger_cost = self.dataset.parse_charger_network_get_charger_cost()
        charger_cost_reward = charger_cost / self.dataset.max_charger_cost
        avg_charge_reward = self.send_reward_request()
        # self.state = self.dataset.graph.edge_attr
        _reward = 100*(avg_charge_reward - charger_cost_reward.item())
        self.reward = _reward
        return dict(x=self.dataset.linegraph.x, edge_index=self.edge_index), _reward, self.done, self.done, dict(graph_env_inst=self)

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
        charger_config = self.dataset.graph.edge_attr[:, 3:]

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