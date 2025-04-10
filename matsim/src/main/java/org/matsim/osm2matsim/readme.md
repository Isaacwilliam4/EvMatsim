osm2matsim
===

Simple Java application to convert OSM files to MATSim network format, using MATSim APIs.
Based on section 7.2.1 from [the book](https://www.matsim.org/the-book) and on the [RunPNetworkGenerator example](https://github.com/matsim-org/matsim-code-examples/blob/0.9.x/src/main/java/tutorial/population/example08DemandGeneration/RunPNetworkGenerator.java)..


# Prerequisites #
A system with Docker installed for converting OSM files into Matsim network files. Java for network visualization and editing with [networkEditor](https://www.matsim.org/extension/networkeditor).

# Usage #
1. Download the broad map files from http://download.geofabrik.de/

2. Extract the desired bounding box from the larger file:
```
./vendor/osmosis/bin/osmosis --rb file=south-america-latest.osm.pbf \ 
 --bounding-box top=-23.5948 left=-46.6807 bottom=-23.5984 right=-46.6736 \ 
 completeWays=true --used-node --write-xml fiandeiras.osm
```

3. Build the converter:
```
./bin/build.sh
```

4. Convert:
```
./bin/convert.sh input/fiandeiras.osm output/fiandeiras.xml
```

5. (Optional) Visualize and edit network:
```
./bin/edit_network.sh
```

## Repository structure rationale ##
### Why Docker? ###
To avoid issues with different jdk versions.

### Why not maven or gradle? ###
Project too simple to justify this tools. We rely on `javac` and `java` with manually set classpaths. 


## New Feature Added to `Osm2matsim.java`

### Writing Combined Coordinates to CSV
- **Description**: A new function was added to generate a CSV file that combines the following information for each sensor:
  - The original sensor coordinates (latitude and longitude).
  - The transformed coordinates (x and y) after applying the MATSim coordinate transformation.
  - The closest node in the MATSim network and the distance to it.

- **Why It Helps**:
  - This CSV file provides a comprehensive view of how sensor data is mapped to the MATSim network.
  - It allows for easy debugging and validation of the coordinate transformation and sensor-to-node mapping.
  - The file can be used for further analysis, such as comparing transformed coordinates with other datasets or validating network accuracy.

- **Usage**:
  - The method `writeSensorToNodeMappingWithCoordinates` was added to `Osm2matsim.java`.
  - Example output file: `sensor_mapping_with_coordinates.csv`.

  ## Example Output File
### **CSV File: `sensor_mapping_with_coordinates.csv`**
The file contains the following columns:
- `SensorID`: The unique ID of the sensor.
- `NodeID`: The ID of the closest node in the MATSim network.
- `Latitude`: The original latitude of the sensor.
- `Longitude`: The original longitude of the sensor.
- `TransformedX`: The transformed x-coordinate of the sensor.
- `TransformedY`: The transformed y-coordinate of the sensor.
- `Distance`: The Euclidean distance between the sensor and the closest node.

#### **Example Data**:
```
SensorID,NodeID,Latitude,Longitude,TransformedX,TransformedY,Distance
2791,360545262,37.073126,-113.584173,-1.4597582887111293E7,3643368.2416960355,12.34
1460,360545263,40.901566,-111.891267,-1.443979179268998E7,4002309.1699671657,45.67
8097,360545264,41.139605,-111.853837,-1.4437074265662372E7,4023569.1642103107,78.90
```


---