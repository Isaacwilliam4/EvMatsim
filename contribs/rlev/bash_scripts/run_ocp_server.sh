cd ../
export MAVEN_OPTS="-Xmx61G"
mvn exec:java -Dexec.mainClass="org.matsim.contrib.rlev.OCPRewardServer" -Dexec.args="16"
