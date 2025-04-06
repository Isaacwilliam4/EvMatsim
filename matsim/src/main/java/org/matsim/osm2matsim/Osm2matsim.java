package org.matsim.osm2matsim;

import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.network.NetworkWriter;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.network.algorithms.NetworkCleaner;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.utils.geometry.CoordUtils;
import org.matsim.core.utils.geometry.CoordinateTransformation;
import org.matsim.core.utils.geometry.transformations.TransformationFactory;
import org.matsim.core.utils.io.OsmNetworkReader;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.*;
import java.util.*;
import java.nio.file.Files;
import java.nio.file.Path;

public class Osm2matsim {
    public static void main(String[] args) throws Exception {
        if (args.length < 3) {
            System.out.println("usage: java Osm2matsim <osm-file> <network-output> <sensor-file>");
            System.exit(1);
        }

        String osmFilename = args[0];
        String networkFilename = args[1];
        String sensorFilename = args[2];
        String outputFilePath = args[3];
        
        Path outputPath = Path.of(outputFilePath);

        System.out.println("Converting " + osmFilename + " to " + networkFilename);
        
        // Set up MATSim network conversion
        CoordinateTransformation ct = TransformationFactory.getCoordinateTransformation(
                TransformationFactory.WGS84, TransformationFactory.WGS84_Albers);
        
        Config config = ConfigUtils.createConfig();
        Scenario scenario = ScenarioUtils.createScenario(config);
        Network network = scenario.getNetwork();
        
        // Convert OSM to MATSim
        OsmNetworkReader osmReader = new OsmNetworkReader(network, ct);
        osmReader.parse(osmFilename);

        new NetworkCleaner().run(network);
        new NetworkWriter(network).write(networkFilename);

        System.out.println("Network conversion complete!");

        // Load sensor data
        Map<String, double[]> sensorCoords = new HashMap<>();
        Map<String, int[]> sensorFlows = new HashMap<>();
        
        readSensorData(sensorFilename, sensorCoords, sensorFlows);


        // NEW: Write original coordinates to CSV
        String originalCoordsFile = "C:\\Users\\webec\\CODEPROJECTS\\ASPIRE\\EvMatsim\\matsim\\src\\main\\java\\org\\matsim\\osm2matsim\\original_coordinates.csv";
        writeOriginalCoordinatesToCSV(originalCoordsFile, sensorCoords);

        // NEW: Write original and Transformed Coordinates to CSV 
        String outputCsvFile = "transformed_coordinates.csv";
        writeOriginalAndTransformedCoordinatesToCSV(outputCsvFile, sensorCoords, ct);   
        
        // Map sensors to closest network links
        Map<String, String> sensorToLinkMap = mapSensorsToLinks(sensorCoords, network);
        // Generate MATSim sensor counts XML
        writeCountsXML(outputPath, sensorToLinkMap, sensorFlows);
        System.out.println("Sensor counts written to sensor_counts.xml!");

        // NEW Map sensors to closest network nodes and write to CSV
        String sensorToNodeFile = "C:\\Users\\webec\\CODEPROJECTS\\ASPIRE\\EvMatsim\\matsim\\src\\main\\java\\org\\matsim\\osm2matsim\\sensor_to_node_mapping.csv";
        mapSensorsToNodesAndWriteCSV(sensorToNodeFile, sensorCoords, network);

        // Map sensors to closest network nodes
        Map<String, String> sensorToNodeMap = mapSensorsToNodes(sensorCoords, network);

        // Write the mapping to a CSV file
        String sensorToNodeFile2 = "sensor_to_node_mapping2.csv";
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(sensorToNodeFile2))) {
            writer.write("SensorID,NodeID");
            writer.newLine();
            for (Map.Entry<String, String> entry : sensorToNodeMap.entrySet()) {
                writer.write(entry.getKey() + "," + entry.getValue());
                writer.newLine();
            }
            System.out.println("Sensor-to-node mapping written to: " + sensorToNodeFile2);
        } catch (IOException e) {
            System.err.println("Error writing sensor-to-node mapping to CSV: " + e.getMessage());
        }
    }


    private static void writeOriginalAndTransformedCoordinatesToCSV(
        String outputCsvFile,
        Map<String, double[]> sensorCoords,
        CoordinateTransformation transformation) {
    try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputCsvFile))) {
        // Write the CSV header
        System.out.println("Writing original and transformed coordinates to CSV...");
        writer.write("SensorID,Latitude,Longitude,TransformedX,TransformedY");
        writer.newLine();

        // Write each sensor's original and transformed coordinates
        for (Map.Entry<String, double[]> entry : sensorCoords.entrySet()) {
            String sensorId = entry.getKey();
            double[] coords = entry.getValue(); // [latitude, longitude]

            // Validate coordinates
            if (coords.length != 2) {
                System.err.println("Invalid coordinates for sensor ID: " + sensorId);
                continue;
            }

            // Transform the coordinates
            org.matsim.api.core.v01.Coord transformedCoord = transformation.transform(
                    new org.matsim.api.core.v01.Coord(coords[1], coords[0])); // lon, lat order

            // Write the data to the CSV
            writer.write(sensorId + "," + coords[0] + "," + coords[1] + "," +
                    transformedCoord.getX() + "," + transformedCoord.getY());
            writer.newLine();
        }

        System.out.println("Original and transformed coordinates written to: " + outputCsvFile);
    } catch (IOException e) {
        System.err.println("Error writing original and transformed coordinates to CSV: " + e.getMessage());
    }
}



    private static void readSensorData(String filename, Map<String, double[]> sensorCoords, Map<String, int[]> sensorFlows) throws IOException {
        BufferedReader br = new BufferedReader(new FileReader(filename));
        String line;
        // Skip the first line (header row)
        br.readLine();
    
        while ((line = br.readLine()) != null) {
            String[] parts = line.split(",");
            if (parts.length < 26) continue; // Skip invalid lines
    
            String sensorId = parts[0];
            double lat = Double.parseDouble(parts[1]);
            double lon = Double.parseDouble(parts[2]);
    
            int[] flows = new int[24];
            for (int i = 0; i < 24; i++) {
                flows[i] = (int) Math.round(Double.parseDouble(parts[i + 3])); // Convert flow values
    
            }
    
            sensorCoords.put(sensorId, new double[]{lat, lon});
            sensorFlows.put(sensorId, flows);
        }
        
        br.close();
        System.out.println("Loaded " + sensorCoords.size() + " sensors.");
    }

    // NEW: Write original coordinates to CSV
    private static void writeOriginalCoordinatesToCSV(String outputCsvFile, Map<String, double[]> sensorCoords) {
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputCsvFile))) {
            // Write the CSV header
            System.out.println("Writing original coordinates to CSV...");
            writer.write("SensorID,Latitude,Longitude");
            writer.newLine();
    
            // Write each sensor's original coordinates
            for (Map.Entry<String, double[]> entry : sensorCoords.entrySet()) {
                String sensorId = entry.getKey();
                double[] coords = entry.getValue(); // [latitude, longitude]
    
                // Validate coordinates
                if (coords.length != 2) {
                    System.err.println("Invalid coordinates for sensor ID: " + sensorId);
                    continue;
                }
    
                writer.write(sensorId + "," + coords[0] + "," + coords[1]);
                writer.newLine();
            }
    
            System.out.println("Original coordinates written to: " + outputCsvFile);
        } catch (IOException e) {
            System.err.println("Error writing original coordinates to CSV: " + e.getMessage());
        }
    }

    // NEW: Map sensors to network nodes and write to CSV
    private static void mapSensorsToNodesAndWriteCSV(String outputCsvFile, Map<String, double[]> sensorCoords, Network network) {
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputCsvFile))) {
            // Write the CSV header
            writer.write("SensorID,NodeID,Distance");
            writer.newLine();
    
            System.out.println("Mapping sensors to network nodes...");
    
            for (Map.Entry<String, double[]> entry : sensorCoords.entrySet()) {
                String sensorId = entry.getKey();
                double[] coords = entry.getValue();
    
                // Sensor coordinates (latitude, longitude)
                double sensorLat = coords[0];
                double sensorLon = coords[1];
    
                double minDistance = Double.MAX_VALUE;
                String closestNodeId = null;
    
                // Iterate through all nodes in the network
                for (org.matsim.api.core.v01.network.Node node : network.getNodes().values()) {
                    double nodeLat = node.getCoord().getY(); // Latitude
                    double nodeLon = node.getCoord().getX(); // Longitude
    
                    // Calculate Euclidean distance
                    double distance = CoordUtils.calcEuclideanDistance(
                        new org.matsim.api.core.v01.Coord(sensorLon, sensorLat),
                        new org.matsim.api.core.v01.Coord(nodeLon, nodeLat)
                    );
    
                    // Find the closest node
                    if (distance < minDistance) {
                        minDistance = distance;
                        closestNodeId = node.getId().toString();
                    }
                }

                if (closestNodeId != null) {
                    // Write the mapping to the CSV file
                    writer.write(sensorId + "," + closestNodeId + "," + minDistance);
                    writer.newLine();
                    System.out.println("Sensor " + sensorId + " mapped to node " + closestNodeId + " (distance: " + minDistance + "m)");
                } else {
                    System.out.println("Warning: No node found for sensor " + sensorId);
                }
            }
    
            System.out.println("Sensor-to-node mapping written to: " + outputCsvFile);
        } catch (IOException e) {
            System.err.println("Error writing sensor-to-node mapping to CSV: " + e.getMessage());
        }
    }

    private static Map<String, String> mapSensorsToNodes(Map<String, double[]> sensorCoords, Network network) {
        Map<String, String> sensorToNode = new HashMap<>();
    
        // Get the network's coordinate transformation
        CoordinateTransformation transformation = TransformationFactory.getCoordinateTransformation(
                TransformationFactory.WGS84, TransformationFactory.WGS84_Albers); // Change to match your network's projection
    
        System.out.println("Mapping sensors to network nodes...");
    
        for (Map.Entry<String, double[]> entry : sensorCoords.entrySet()) {
            String sensorId = entry.getKey();
            double[] coords = entry.getValue();
    
            // Transform sensor coordinates to the same system as the network
            org.matsim.api.core.v01.Coord sensorCoord = transformation.transform(
                new org.matsim.api.core.v01.Coord(coords[1], coords[0])); // lon, lat order
    
            double minDistance = Double.MAX_VALUE;
            String closestNodeId = null;
    
            // Iterate through all nodes in the network
            for (org.matsim.api.core.v01.network.Node node : network.getNodes().values()) {
                double distance = CoordUtils.calcEuclideanDistance(sensorCoord, node.getCoord());
    
                if (distance < minDistance) {
                    minDistance = distance;
                    closestNodeId = node.getId().toString();
                }
            }
    
            if (closestNodeId != null) {
                sensorToNode.put(sensorId, closestNodeId);
                System.out.println("Sensor " + sensorId + " mapped to node " + closestNodeId + " (distance: " + minDistance + "m)");
            } else {
                System.out.println("Warning: No node found for sensor " + sensorId);
            }
        }
    
        System.out.println("Mapped " + sensorToNode.size() + " sensors to nodes.");
        return sensorToNode;
    }






    private static Map<String, String> mapSensorsToLinks(Map<String, double[]> sensorCoords, Network network) {
        Map<String, String> sensorToLink = new HashMap<>();
        Set<String> usedLinkIds = new HashSet<>(); // Track assigned location IDs
    
        // Get the network's coordinate transformation
        CoordinateTransformation transformation = TransformationFactory.getCoordinateTransformation(
                TransformationFactory.WGS84, TransformationFactory.WGS84_Albers); // Change to match your network's projection
    
        System.out.println("Mapping sensors to network links...");
    
        for (Map.Entry<String, double[]> entry : sensorCoords.entrySet()) {
            String sensorId = entry.getKey();
            double[] coords = entry.getValue();
    
            // Transform sensor coordinates to the same system as the network
            org.matsim.api.core.v01.Coord sensorCoord = transformation.transform(new org.matsim.api.core.v01.Coord(coords[1], coords[0])); // lon, lat order
    
            double minDistance = Double.MAX_VALUE;
            String closestLinkId = null;
    
            for (Link link : network.getLinks().values()) {
                double distance = CoordUtils.calcEuclideanDistance(sensorCoord, link.getCoord());
    
                // Only assign if the link ID hasn't been used yet
                if (distance < minDistance && !usedLinkIds.contains(link.getId().toString())) {
                    minDistance = distance;
                    closestLinkId = link.getId().toString();
                }
            }
    
            if (closestLinkId != null) {
                sensorToLink.put(sensorId, closestLinkId);
                usedLinkIds.add(closestLinkId); // Mark the link ID as assigned
                System.out.println("Sensor " + sensorId + " mapped to link " + closestLinkId + " (distance: " + minDistance + "m)");
            } else {
                System.out.println("Warning: No unique link found for sensor " + sensorId + ". Skipping...");
            }
        }
    
        System.out.println("Mapped " + sensorToLink.size() + " unique sensors to links.");
        return sensorToLink;
    }



    private static void writeCountsXML(Path outputFilePath, Map<String, String> sensorToLinkMap, Map<String, int[]> sensorFlows) throws Exception {
        if (!outputFilePath.getParent().toFile().exists()) {
            outputFilePath.getParent().toFile().mkdirs();
        }

        File file = new File(outputFilePath.toString());
        if (file.exists()) {
            file.delete();
            file.createNewFile();
        }
        
        DocumentBuilderFactory dbFactory = DocumentBuilderFactory.newInstance();
        DocumentBuilder dBuilder = dbFactory.newDocumentBuilder();
        Document doc = dBuilder.newDocument();
    
        // Root element
        Element rootElement = doc.createElement("counts");
        rootElement.setAttribute("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance");
        rootElement.setAttribute("xsi:noNamespaceSchemaLocation", "http://matsim.org/files/dtd/counts_v1.xsd");
        rootElement.setAttribute("name", "default");
        rootElement.setAttribute("desc", "default");
        rootElement.setAttribute("year", "2024");
        doc.appendChild(rootElement);
    
        // Process each sensor
        for (String sensorId : sensorToLinkMap.keySet()) {
            String linkId = sensorToLinkMap.get(sensorId);
            Element countElement = doc.createElement("count");
            countElement.setAttribute("loc_id", linkId);
            countElement.setAttribute("cs_id", sensorId);
            rootElement.appendChild(countElement);
    
            int[] flows = sensorFlows.get(sensorId);
            for (int hour = 0; hour < 24; hour++) {
                Element volumeElement = doc.createElement("volume");
                volumeElement.setAttribute("h", String.valueOf(hour + 1));
                volumeElement.setAttribute("val", String.valueOf(flows[hour]));
                countElement.appendChild(volumeElement);
            }
        }
    
        javax.xml.transform.TransformerFactory transformerFactory = javax.xml.transform.TransformerFactory.newInstance();
        javax.xml.transform.Transformer transformer = transformerFactory.newTransformer();
        transformer.setOutputProperty(javax.xml.transform.OutputKeys.INDENT, "yes");
    
        javax.xml.transform.dom.DOMSource source = new javax.xml.transform.dom.DOMSource(doc);
        java.io.FileOutputStream fos = new java.io.FileOutputStream(file);
        javax.xml.transform.stream.StreamResult result = new javax.xml.transform.stream.StreamResult(fos);
    
        transformer.transform(source, result);
    
        // Flush and close the stream
        fos.flush();
        fos.close();
    
        System.out.println("Counts XML successfully written to: " + file.getAbsolutePath());
    }

}

