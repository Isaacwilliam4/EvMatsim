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
        
        // Map sensors to closest network links
        Map<String, String> sensorToLinkMap = mapSensorsToLinks(sensorCoords, network);
        // Generate MATSim sensor counts XML
        writeCountsXML(outputPath, sensorToLinkMap, sensorFlows);
        System.out.println("Sensor counts written to sensor_counts.xml!");

        // Use a relative path for the combined output file
        String combinedOutputFile = "sensor_mapping_with_coordinates.csv";
        writeSensorToNodeMappingWithCoordinates(combinedOutputFile, sensorCoords, network, ct);
        }

    private static void writeSensorToNodeMappingWithCoordinates(
        String outputCsvFile,
        Map<String, double[]> sensorCoords, 
        Network network,
        CoordinateTransformation transformation) {
        
        File file = new File(outputCsvFile);
        
        // Create parent directories if they don't exist
        if (file.getParentFile() != null) {
            file.getParentFile().mkdirs();
        }
        
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(file))) {
            // Write the CSV header
            System.out.println("Writing combined sensor mapping and coordinates to CSV...");
            writer.write("SensorID,NodeID,Latitude,Longitude,TransformedX,TransformedY,Distance");
            writer.newLine();

            // Process each sensor
            for (Map.Entry<String, double[]> entry : sensorCoords.entrySet()) {
                String sensorId = entry.getKey();
                double[] coords = entry.getValue(); // [latitude, longitude]

                // Validate coordinates
                if (coords.length != 2) {
                    System.err.println("Invalid coordinates for sensor ID: " + sensorId);
                    continue;
                }

                double sensorLat = coords[0];
                double sensorLon = coords[1];

                // Transform the coordinates
                org.matsim.api.core.v01.Coord transformedCoord = transformation.transform(
                        new org.matsim.api.core.v01.Coord(sensorLon, sensorLat)); // lon, lat order

                // Find closest node
                double minDistance = Double.MAX_VALUE;
                String closestNodeId = null;

                // Iterate through all nodes in the network
                for (org.matsim.api.core.v01.network.Node node : network.getNodes().values()) {
                    double nodeLat = node.getCoord().getY(); // Latitude
                    double nodeLon = node.getCoord().getX(); // Longitude

                    // Calculate Haversine distance
                    double distance = haversineDistance(sensorLat, sensorLon, nodeLat, nodeLon);

                    // Find the closest node
                    if (distance < minDistance) {
                        minDistance = distance;
                        closestNodeId = node.getId().toString();
                    }
                }

                if (closestNodeId != null) {
                    // Write all the data to the CSV file
                    writer.write(sensorId + "," + 
                                closestNodeId + "," + 
                                sensorLat + "," + 
                                sensorLon + "," + 
                                transformedCoord.getX() + "," + 
                                transformedCoord.getY() + "," + 
                                minDistance);
                    writer.newLine();
                    
                    System.out.println("Sensor " + sensorId + " mapped to node " + closestNodeId + " (distance: " + minDistance + "m)");
                } else {
                    System.out.println("Warning: No node found for sensor " + sensorId);
                }
            }

            System.out.println("Combined data written to: " + file.getAbsolutePath());
        } catch (IOException e) {
            System.err.println("Error writing combined data to CSV: " + e.getMessage());
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
                double linkLat = link.getCoord().getY(); // Latitude
                double linkLon = link.getCoord().getX(); // Longitude
            
                // Calculate Haversine distance
                double distance = haversineDistance(sensorCoord.getY(), sensorCoord.getX(), linkLat, linkLon);
            
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

    private static double haversineDistance(double lat1, double lon1, double lat2, double lon2) {
        final int EARTH_RADIUS = 6371000; // Radius of the Earth in meters
    
        // Convert latitude and longitude from degrees to radians
        double lat1Rad = Math.toRadians(lat1);
        double lon1Rad = Math.toRadians(lon1);
        double lat2Rad = Math.toRadians(lat2);
        double lon2Rad = Math.toRadians(lon2);
    
        // Calculate the differences
        double deltaLat = lat2Rad - lat1Rad;
        double deltaLon = lon2Rad - lon1Rad;
    
        // Apply the Haversine formula
        double a = Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
                   Math.cos(lat1Rad) * Math.cos(lat2Rad) *
                   Math.sin(deltaLon / 2) * Math.sin(deltaLon / 2);
        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    
        // Calculate the distance
        return EARTH_RADIUS * c;
    }


}

