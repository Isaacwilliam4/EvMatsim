import numpy as np
from gymnasium import spaces
from evsim.envs.matsim_graph_env import MatsimGraphEnv
from evsim.scripts.create_chargers import create_chargers_xml_gymnasium


class MatsimGraphEnvGNN(MatsimGraphEnv):
    """
    A custom Gymnasium environment for Matsim graph-based simulations
    with GNNs. It supports multi-agent actions and observations.
    """

    def __init__(self, config_path, num_agents=100, save_dir=None):
        """
        Initialize the environment.

        Args:
            config_path (str): Path to the configuration file.
            num_agents (int): Number of agents in the environment.
            save_dir (str): Directory to save outputs.
        """
        super().__init__(config_path, num_agents, save_dir)

        self.observation_space: spaces.Dict = spaces.Dict(
            spaces=dict(x=self.x, edge_index=self.edge_index_space)
        )

    def reset(self, **kwargs):
        """
        Reset the environment to its initial state.

        Returns:
            tuple: Initial observation and additional info.
        """
        return dict(
            x=self.dataset.linegraph.x.numpy(),
            edge_index=self.dataset.linegraph.edge_index.numpy().astype(np.int32),
        ), dict(info="info")

    def step(self, actions):
        """
        Take an action and return the next state, reward, done, and info.

        Args:
            actions (list): Actions to perform.

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
            dict(
                x=self.dataset.linegraph.x.numpy(),
                edge_index=self.dataset.linegraph.edge_index.numpy().astype(np.int32),
            ),
            _reward,
            self.done,
            self.done,
            dict(graph_env_inst=self),
        )
