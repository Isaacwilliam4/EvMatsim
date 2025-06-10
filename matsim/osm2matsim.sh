mvn exec:java -Dexec.mainClass="org.matsim.osm2matsim.GetNetworkAndSensors" -Dexec.args="/path/to/EvMatsim/contribs/rlev/scenario_examples/i-15-scenario_1_agent/i-15-cleaned.osm /path/to/EvMatsim/contribs/rlev/scenario_examples/i-15-scenario_1_agent/example_network.xml"


mvn exec:java -Dexec.mainClass="org.matsim.osm2matsim.GetNetworkAndSensors" -Dexec.args="/path/to/EvMatsim/contribs/rlev/scenario_examples/i-15-scenario_1_agent/i-15-cleaned.osm \
 /path/to/EvMatsim/contribs/rlev/scenario_examples/i-15-scenario_1_agent/example_network.xml \
 /path/to/EvMatsim/contribs/rlev/rlev/scripts/udot-sensors/sensor_data.csv \
 /path/to/EvMatsim/contribs/rlev/scenario_examples/i-15-scenario_1_agent/example_counts.xml \
 20"
