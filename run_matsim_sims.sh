cd matsim/
export MAVEN_OPTS="-Xmx61G"

mvn exec:java -Dexec.mainClass="org.matsim.run.RunMatsim" -Dexec.args="/home/isaacp/repos/EvMatsim/contribs/rlev/scenario_examples/i-15-scenario/i-15-config.xml"
