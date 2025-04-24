cd matsim/
export MAVEN_OPTS="-Xmx100G"
mvn exec:java -Dexec.mainClass="org.matsim.run.RunMatsim" -Dexec.args="../contribs/ev/scenario_examples/cluster_scenarios/utah_flow_scenario_example_1_000_000/utahconfig.xml" -Dexec.jvmArgs="-Xmx100G"
mvn exec:java -Dexec.mainClass="org.matsim.run.RunMatsim" -Dexec.args="../contribs/ev/scenario_examples/cluster_scenarios/utah_flow_scenario_example_5_000_000/utahconfig.xml" -Dexec.jvmArgs="-Xmx100G"
mvn exec:java -Dexec.mainClass="org.matsim.run.RunMatsim" -Dexec.args="../contribs/ev/scenario_examples/cluster_scenarios/utah_flow_scenario_example_10_000_000/utahconfig.xml" -Dexec.jvmArgs="-Xmx100G"