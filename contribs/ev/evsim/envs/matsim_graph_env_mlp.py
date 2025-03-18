import gymnasium as gym
from gymnasium import spaces
import numpy as np
from evsim.classes.matsim_xml_dataset import MatsimXMLDataset
from evsim.util import *
import shutil
from datetime import datetime
from pathlib import Path
import torch
import requests
from evsim.scripts.create_chargers import *
from evsim.classes.chargers import *
from typing import List
import json
import zipfile
from filelock import FileLock


class MatsimGraphEnvMlp(gym.Env):
    """
    A custom Gymnasium environment for Matsim graph-based simulations.

    Attributes:
        config_path (Path): Path to the configuration file.
        num_agents (int): Number of agents in the simulation.
        save_dir (str): Directory to save outputs.
        dataset (MatsimXMLDataset): Dataset for Matsim simulation.
        action_space (spaces.MultiDiscrete): Action space for the environment.
        observation_space (spaces.Box): Observation space for the environment.
        reward (float): Current reward value.
        best_reward (float): Best reward achieved so far.
        state (spaces.Box): Current state of the environment.
        done (bool): Flag indicating if the episode is done.
    """

    def __init__(self, config_path, num_agents=100, save_dir=None):
        """
        Initialize the MatsimGraphEnvMlp environment.

        Args:
            config_path (str): Path to the configuration file.
            num_agents (int): Number of agents in the simulation.
            save_dir (str): Directory to save outputs.
        """
        super().__init__()
        self.save_dir = save_dir
        current_time = datetime.now()
        self.time_string = current_time.strftime("%Y%m%d_%H%M%S_%f")
        if num_agents < 0:
            num_agents = None
        self.num_agents = num_agents

        self.config_path: Path = Path(config_path)
        self.charger_list: List[Charger] = [
            NoneCharger,
            DynamicCharger,
            StaticCharger,
        ]
        self.dataset = MatsimXMLDataset(
            self.config_path,
            self.time_string,
            self.charger_list,
            num_agents=self.num_agents,
            initial_soc=0.5,
        )
        self.num_links_reward_scale = -100

        self.reward: float = 0
        self.best_reward = -np.inf
        self.num_charger_types: int = len(self.charger_list)

        self.action_space: spaces.MultiDiscrete = spaces.MultiDiscrete(
            [self.num_charger_types] * self.dataset.linegraph.num_nodes
        )
        self.x = spaces.Box(
            low=0,
            high=1,
            shape=self.dataset.linegraph.x.shape,
            dtype=np.float32,
        )
        self.edge_index = self.dataset.linegraph.edge_index.to(torch.int32)
        edge_index_np = self.edge_index.numpy()
        max_edge_index = np.max(edge_index_np) + 1
        self.edge_index_space = spaces.Box(
            low=edge_index_np,
            high=np.full(edge_index_np.shape, max_edge_index),
            shape=self.edge_index.shape,
            dtype=np.int32,
        )

        self.observation_space = spaces.Box(
            low=0,
            high=1.0,
            shape=self.dataset.linegraph.x.shape,
            dtype=np.float32,
        )

        self.state = self.observation_space
        self.done: bool = False
        self.lock_file = Path(self.save_dir, "lockfile.lock")
        self.best_output_response = None

    def save_server_output(self, response, filetype):
        """
        Save server output to a zip file and extract its contents.

        Args:
            response (requests.Response): Server response containing the file.
            filetype (str): Type of the file to save.
        """
        zip_filename = Path(self.save_dir, f"{filetype}.zip")
        extract_folder = Path(self.save_dir, filetype)

        lock = FileLock(self.lock_file)

        with lock:
            with open(zip_filename, "wb") as f:
                f.write(response.content)

            print(f"Saved zip file: {zip_filename}")

            with zipfile.ZipFile(zip_filename, "r") as zip_ref:
                zip_ref.extractall(extract_folder)

            print(f"Extracted files to: {extract_folder}")

    def send_reward_request(self):
        """
        Send a request to the server to calculate the reward.

        Returns:
            float: Reward value.
            requests.Response: Server response.
        """
        url = "http://localhost:8000/getReward"
        files = {
            "config": open(self.dataset.config_path, "rb"),
            "network": open(self.dataset.network_xml_path, "rb"),
            "plans": open(self.dataset.plan_xml_path, "rb"),
            "vehicles": open(self.dataset.vehicle_xml_path, "rb"),
            "chargers": open(self.dataset.charger_xml_path, "rb"),
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
        return self.dataset.linegraph.x.numpy(), dict(info="info")

    def step(self, actions):
        """
        Take an action and return the next state, reward, done, and info.

        Args:
            actions (np.ndarray): Actions to take.

        Returns:
            tuple: Next state, reward, done flags, and additional info.
        """
        create_chargers_xml_gymnasium(
            self.dataset.charger_xml_path,
            self.charger_list,
            actions,
            self.dataset.edge_mapping,
        )
        charger_cost = self.dataset.parse_charger_network_get_charger_cost()
        charger_cost_reward = charger_cost / self.dataset.max_charger_cost
        avg_charge_reward, server_response = self.send_reward_request()
        _reward = 100 * (avg_charge_reward - charger_cost_reward.item())
        self.reward = _reward
        if _reward > self.best_reward:
            self.best_reward = _reward
            self.best_output_response = server_response

        return (
            self.dataset.linegraph.x.numpy(),
            _reward,
            self.done,
            self.done,
            dict(graph_env_inst=self),
        )

    def render(self):
        """
        Render the environment (optional).
        """
        print(f"State: {self.state}")

    def close(self):
        """
        Clean up resources (optional).
        """
        shutil.rmtree(self.dataset.config_path.parent)

    def save_charger_config_to_csv(self, csv_path):
        """
        Save the current charger configuration to a CSV file.

        Args:
            csv_path (str): Path to save the CSV file.
        """
        static_chargers = []
        dynamic_chargers = []
        charger_config = self.dataset.graph.edge_attr[:, 3:]

        for idx, row in enumerate(charger_config):
            if not row[0]:
                if row[1]:
                    dynamic_chargers.append(int(self.dataset.edge_mapping.inverse[idx]))
                elif row[2]:
                    static_chargers.append(int(self.dataset.edge_mapping.inverse[idx]))

        df = pd.DataFrame(
            {
                "iteration": [0],
                "reward": [self.reward],
                "static_chargers": [static_chargers],
                "dynamic_chargers": [dynamic_chargers],
            }
        )
        df.to_csv(csv_path, index=False)


if __name__ == "__main__":
    env = MatsimGraphEnvMlp(
        config_path="/home/isaacp/EvMatsim/contribs/ev/script_scenarios/"
        "utahevscenario/utahevconfig.xml"
    )
    sample = env.action_space.sample()
    env.save_charger_config_to_csv(Path(Path(__file__).parent, "test_save_charger.csv"))
    env.close()
