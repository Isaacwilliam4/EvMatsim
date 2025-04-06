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


## New Features Added to `Osm2matsim.java`

### 1. Mapping Sensors to Network Nodes
- **Description**: Sensors are now mapped to the closest nodes in the MATSim network. This mapping is written to a CSV file for further analysis.
- **Usage**:
  - The method `mapSensorsToNodesAndWriteCSV` was added.
  - Example output file: `sensor_to_node_mapping.csv`.

### 2. Writing Combined Coordinates to CSV
- **Description**: The program now writes both the original sensor coordinates (latitude/longitude) and their transformed coordinates (x/y) into a single CSV file. This allows for easy comparison of coordinate transformations.
- **Usage**:
  - The method `writeOriginalAndTransformedCoordinatesToCSV` was added.
  - Example output file: `combined_coordinates.csv`.

### 3. Checking Transformed Coordinates in the Network
- **Description**: A new function, `CheckCoordinates`, was added to verify whether the transformed coordinates (`TransformedX` and `TransformedY`) from the `combined_coordinates.csv` file appear in the `utahevnetwork.xml` file.
- **Usage**:
  - Run the `CheckCoordinates` program to compare the transformed coordinates against the network XML file.
  - Example output: Prints whether each coordinate pair was found or not.

### 4. Fetching Elevation Data
- **Description**: The `ElevationFetcher` function retrieves elevation data for the original sensor coordinates. This data can be used to calculate slopes or enrich the network with elevation information.
- **Usage**:
  - The function fetches elevation data for each sensor and integrates it into the workflow.
  - Example output: Elevation data is added to the sensor data structure or written to a CSV file.

---