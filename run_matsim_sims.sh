cd matsim/
export MAVEN_OPTS="-Xmx60G"
mvn exec:java -Dexec.mainClass="org.matsim.run.RunMatsim" -Dexec.args="../contribs/ev/scenario_examples/cluster_scenarios/utah_flow_scenario_example_1_000_000/utahconfig.xml"
mvn exec:java -Dexec.mainClass="org.matsim.run.RunMatsim" -Dexec.args="../contribs/ev/scenario_examples/cluster_scenarios/utah_flow_scenario_example_2_000_000/utahconfig.xml"
mvn exec:java -Dexec.mainClass="org.matsim.run.RunMatsim" -Dexec.args="../contribs/ev/scenario_examples/cluster_scenarios/utah_flow_scenario_example_3_000_000/utahconfig.xml"