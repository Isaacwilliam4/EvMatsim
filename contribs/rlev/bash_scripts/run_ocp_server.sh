cd ../
export MAVEN_OPTS="-Xmx240G"
mvn exec:java -Dexec.mainClass="org.matsim.contrib.rlev.OCPRewardServer" -Dexec.args="20" > server_output.log 2>&1
