from gymnasium.envs.registration import register

register(
    id='MatsimGraphEnv-v0',  # Unique ID for your environment
    entry_point='evsim.envs.matsim_graph_env:MatsimGraphEnv',  # Path to the environment class
)