from gymnasium.envs.registration import register

register(
    id='MatsimGraphEnvGNN-v0',  # Unique ID for your environment
    entry_point='evsim.envs.matsim_graph_env_gnn:MatsimGraphEnvGNN',  # Path to the environment class
)

register(
    id='MatsimGraphEnvMlp-v0',  # Unique ID for your environment
    entry_point='evsim.envs.matsim_graph_env_mlp:MatsimGraphEnvMlp',  # Path to the environment class
)