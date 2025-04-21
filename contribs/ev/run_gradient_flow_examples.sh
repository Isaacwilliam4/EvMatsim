eval "$(conda shell.bash hook)"
conda activate matsimenv

python3 -m evsim.gradient_flow_matching.run_gradient_flow_matching \
"./evsim/gradient_flow_matching/utah_flow_results" \
"./scenario_examples/utah_flow_scenario_example/utahnetwork.xml" \
"./scenario_examples/utah_flow_scenario_example/utahcounts.xml" \
"--num_clusters" "100" \
"--num_samples" "100" \
"--training_steps" "1" \
"--log_interval" "1_000" \
"--save_interval" "-1"

python3 -m evsim.gradient_flow_matching.run_gradient_flow_matching \
"./evsim/gradient_flow_matching/utah_flow_results" \
"./scenario_examples/utah_flow_scenario_example/utahnetwork.xml" \
"./scenario_examples/utah_flow_scenario_example/utahcounts.xml" \
"--num_clusters" "100" \
"--num_samples" "1_000" \
"--training_steps" "1" \
"--log_interval" "1_000" \
"--save_interval" "-1"

python3 -m evsim.gradient_flow_matching.run_gradient_flow_matching \
"./evsim/gradient_flow_matching/utah_flow_results" \
"./scenario_examples/utah_flow_scenario_example/utahnetwork.xml" \
"./scenario_examples/utah_flow_scenario_example/utahcounts.xml" \
"--num_clusters" "200" \
"--num_samples" "100" \
"--training_steps" "1" \
"--log_interval" "1_000" \
"--save_interval" "-1"

python3 -m evsim.gradient_flow_matching.run_gradient_flow_matching \
"./evsim/gradient_flow_matching/utah_flow_results" \
"./scenario_examples/utah_flow_scenario_example/utahnetwork.xml" \
"./scenario_examples/utah_flow_scenario_example/utahcounts.xml" \
"--num_clusters" "200" \
"--num_samples" "1_000" \
"--training_steps" "1" \
"--log_interval" "1_000" \
"--save_interval" "-1"


