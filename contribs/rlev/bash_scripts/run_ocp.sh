cd ..

eval "$(conda shell.bash hook)"

conda activate ppomatsimenv

python -m rlev.rl_algorithm_ppo \
"/home/isaacp/repos/EvMatsim/contribs/rlev/scenario_examples/i-15-scenario/i-15-config.xml" \
"--num_timesteps" "1000000" \
"--num_envs" "2" \
"--num_steps" "1" \
"--batch_size" "2" \
"--results_dir" "/home/isaacp/repos/EvMatsim/contribs/rlev/i-15-results" \
"--learning_rate" "0.0001" \
"--clip_range" "0.3" \
"--save_frequency" "20000" \
"--policy_type" "MlpPolicy"

