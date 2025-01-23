import gymnasium as gym
from gymnasium import spaces
import numpy as np
from torch_geometric.data import Data

class MatsimGraphEnv(gym.Env):
    def __init__(self, graph:Data):
        super().__init__()
        
        self.graph = graph
        self.num_edges = graph.edge_index.size(1)
        # Define action and observation space
        # Example: Discrete action space with 3 actions
        self.action_space = spaces.MultiDiscrete([3] * self.num_edges)
        
        # Example: Continuous observation space (state vector of size 4)
        # self.observation_space = spaces.Dict({
        #     "node_features": spaces.
        # })
        
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
