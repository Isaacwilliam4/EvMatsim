cd ../
export MAVEN_OPTS="-Xmx5G"
mvn exec:java -Dexec.mainClass="org.matsim.contrib.rlev.OCPRewardServer" -Dexec.args="2" > server_output.log 2>&1
