import numpy as np
from gymnasium import spaces
from rlev.envs.matsim_graph_env import MatsimGraphEnv
from rlev.scripts.create_chargers import create_chargers_xml_gymnasium


class MatsimGraphEnvMlp(MatsimGraphEnv):
    """
    A custom Gymnasium environment for Matsim graph-based simulations.
    """

    def __init__(self, config_path, num_agents=100, save_dir=None):
        super().__init__(config_path, num_agents, save_dir)

        self.observation_space = spaces.Box(
            low=0,
            high=1.0,
            shape=self.dataset.linegraph.x.shape,
            dtype=np.float32,
        )

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
        reward = self.send_reward_request(actions)

        return (
            self.dataset.linegraph.x.numpy(),
            reward,
            self.done,
            self.done,
            dict(graph_env_inst=self),
        )
