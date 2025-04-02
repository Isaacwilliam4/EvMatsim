import numpy as np
from gymnasium import spaces
from evsim.envs.flow_matsim_graph_env import FlowMatsimGraphEnv
from evsim.scripts.create_chargers import create_chargers_xml_gymnasium


class FlowMatsimGraphEnvMlp(FlowMatsimGraphEnv):
    """
    A custom Gymnasium environment for Matsim graph-based simulations.
    """

    def __init__(self, config_path, num_agents=100, save_dir=None):
        super().__init__(config_path, num_agents, save_dir)

        self.observation_space: spaces.Dict = spaces.Dict(
            spaces=dict(x=self.x, edge_index=self.edge_index_space)
        )

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
