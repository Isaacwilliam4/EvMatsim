import gymnasium as gym
from gymnasium import spaces
import numpy as np
from torch_geometric.data import Data
from evsim.classes.matsim_xml_dataset import MatsimXMLDataset
from torch_geometric.data import Dataset

class MatsimGraphEnv(gym.Env):
    def __init__(self, dataset: MatsimXMLDataset):
        super().__init__()
        
        self.dataset = dataset
        self.graph = dataset.get_graph()
        self.num_edges = graph.edge_index.size(1)
        self.num_charger_types = len(self.dataset.charger_dict)
        # Define action and observation space
        # Example: Discrete action space with 3 actions
        self.action_space = spaces.MultiDiscrete([3] * self.num_edges)
        
        self.observation_space = spaces.Box(
            low=0.0,                     # Minimum value for all features
            high=1.0,                    # Maximum value for all features
            shape=(self.num_edges, 6),   # Shape of the observation space
            dtype=np.float32             # Data type of the features
        )
        
        # Initialize environment-specific variables
        self.state = None
        self.done = False

    def reset(self):
        """Reset the environment to the initial state."""
        self.state = np.zeros(4)  # Example initial state
        self.done = False
        return self.state, {}

    def step(self, action):
        """Take an action and return the next state, reward, done, and info."""
        # Example: Update state based on action
        self.state += action - 1  # Example update logic
        
        # Calculate reward (example logic)
        reward = -np.sum(self.state**2)
        
        # Define episode termination condition
        self.done = np.linalg.norm(self.state) > 10
        
        # Optional: Provide additional information
        info = {}
        
        return self.state, reward, self.done, info

    def render(self):
        """Optional: Render the environment."""
        print(f"State: {self.state}")

    def close(self):
        """Optional: Clean up resources."""
        pass


if __name__ == "__main__":
    network_xml_path = "/home/isaacp/repos/EvMatsim/contribs/ev/script_scenarios/utahevscenario/utahevnetwork.xml"
    charger_xml_path = "/home/isaacp/repos/EvMatsim/contribs/ev/script_scenarios/utahevscenario/utahevchargers.xml"
    charger_dict = {
        "none": 0,
        # in matsim the default charger is a static charger we could update this dictionary
        # to include different charger types along with charger cost and other attributes
        # the graph uses this dictionary to map the charger type to an integer
        "default": 1,
        "dynamic": 2
    }
    dataset = MatsimXMLDataset(network_xml_path, charger_xml_path, charger_dict)
    graph : Data = dataset.get_graph()

    env = MatsimGraphEnv(graph)