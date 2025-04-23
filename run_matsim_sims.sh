cd matsim/
export MAVEN_OPTS="-Xmx100G"
mvn exec:java -Dexec.mainClass="org.matsim.run.RunMatsim" -Dexec.args="../contribs/ev/scenario_examples/cluster_scenarios/utah_flow_scenario_example_10c/utahconfig.xml" -Dexec.jvmArgs="-Xmx100G"
mvn exec:java -Dexec.mainClass="org.matsim.run.RunMatsim" -Dexec.args="../contribs/ev/scenario_examples/cluster_scenarios/utah_flow_scenario_example_50c/utahconfig.xml" -Dexec.jvmArgs="-Xmx100G"
mvn exec:java -Dexec.mainClass="org.matsim.run.RunMatsim" -Dexec.args="../contribs/ev/scenario_examples/cluster_scenarios/utah_flow_scenario_example_100c/utahconfig.xml" -Dexec.jvmArgs="-Xmx100G"
mvn exec:java -Dexec.mainClass="org.matsim.run.RunMatsim" -Dexec.args="../contribs/ev/scenario_examples/cluster_scenarios/utah_flow_scenario_example_200c/utahconfig.xml" -Dexec.jvmArgs="-Xmx100G"