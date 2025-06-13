from gymnasium.envs.registration import register

register(
    id="MatsimGraphEnvGNN-v0", 
    entry_point="rlev.envs.matsim_graph_env_gnn:MatsimGraphEnvGNN",
)

register(
    id="MatsimGraphEnvMlp-v0", 
    entry_point="rlev.envs.matsim_graph_env_mlp:MatsimGraphEnvMlp",
)
