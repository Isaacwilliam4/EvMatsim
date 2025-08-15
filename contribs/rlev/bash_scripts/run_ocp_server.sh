cd ../
export MAVEN_OPTS="-Xmx5G"
mvn exec:java -Dexec.mainClass="org.matsim.contrib.rlev.OCPRewardServer" -Dexec.args="32"
