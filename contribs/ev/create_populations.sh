eval "$(conda shell.bash hook)"
conda activate matsimenv

python3 -m evsim.scripts.create_population \
"./scenario_examples/utah_flow_scenario_example/utahnetwork.xml" \
"./scenario_examples/utah_flow_scenario_example/utahcounts_1_000_000.xml" \
"--num_agents" "1_000_000" \

python3 -m evsim.scripts.create_population \
"./scenario_examples/utah_flow_scenario_example/utahnetwork.xml" \
"./scenario_examples/utah_flow_scenario_example/utahcounts_5_000_000.xml" \
"--num_agents" "5_000_000" \

python3 -m evsim.scripts.create_population \
"./scenario_examples/utah_flow_scenario_example/utahnetwork.xml" \
"./scenario_examples/utah_flow_scenario_example/utahcounts_10_000_000.xml" \
"--num_agents" "10_000_000" \