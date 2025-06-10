# mvn exec:java -Dexec.mainClass="org.matsim.osm2matsim.Osm2matsim" -Dexec.args="/home/isaacp/repos/EvMatsim/contribs/rlev/scenario_examples/i-15-scenario_1_agent/i-15-cleaned.osm /home/isaacp/repos/EvMatsim/contribs/rlev/scenario_examples/i-15-scenario_1_agent/example_network.xml"


mvn exec:java -Dexec.mainClass="org.matsim.osm2matsim.Osm2matsim" -Dexec.args="/home/isaacp/repos/EvMatsim/contribs/rlev/scenario_examples/i-15-scenario_1_agent/i-15-cleaned.osm \
 /home/isaacp/repos/EvMatsim/contribs/rlev/scenario_examples/i-15-scenario_1_agent/example_network.xml \
 /home/isaacp/repos/EvMatsim/contribs/rlev/rlev/scripts/udot-sensors/sensor_data.csv \
 /home/isaacp/repos/EvMatsim/contribs/rlev/scenario_examples/i-15-scenario_1_agent/example_counts.xml
 "
