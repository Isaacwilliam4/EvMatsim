eval "$(conda shell.bash hook)"
conda activate matsimenv

python3 -m evsim.scripts.create_population \
"./scenario_examples/utah_flow_scenario_example/utahnetwork.xml" \
"./scenario_examples/cluster_scenarios/utah_flow_scenario_example_1_000_000/utahplans_1_000_000.xml" \
"--num_agents" "1_000_000" \

python3 -m evsim.scripts.create_population \
"./scenario_examples/utah_flow_scenario_example/utahnetwork.xml" \
"./scenario_examples/cluster_scenarios/utah_flow_scenario_example_2_000_000/utahplans_2_000_000.xml" \
"--num_agents" "2_000_000" \

python3 -m evsim.scripts.create_population \
"./scenario_examples/utah_flow_scenario_example/utahnetwork.xml" \
"./scenario_examples/cluster_scenarios/utah_flow_scenario_example_3_000_000/utahplans_3_000_000.xml" \
"--num_agents" "3_000_000" \