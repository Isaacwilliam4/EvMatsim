package org.matsim.osm2matsim;
import java.io.*;
import java.util.*;
import javax.xml.parsers.*;
import org.w3c.dom.*;

public class CheckCoordinates {

    public static void main(String[] args) {
        String csvFilePath = "c:\\Users\\webec\\CODEPROJECTS\\ASPIRE\\EvMatsim\\matsim\\src\\main\\java\\org\\matsim\\osm2matsim\\combined_coordinates.csv";
        String xmlFilePath = "c:\\Users\\webec\\CODEPROJECTS\\ASPIRE\\EvMatsim\\contribs\\ev\\scenario_examples\\utahev_scenario_example\\utahevnetwork.xml";

        try {
            // Load TransformedX and TransformedY from the CSV file
            Set<String> transformedCoordinates = loadTransformedCoordinates(csvFilePath);

            // Check if the coordinates appear in the XML file
            checkCoordinatesInXML(transformedCoordinates, xmlFilePath);
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
        }
    }

    private static Set<String> loadTransformedCoordinates(String csvFilePath) throws IOException {
        Set<String> transformedCoordinates = new HashSet<>();
        try (BufferedReader br = new BufferedReader(new FileReader(csvFilePath))) {
            String line;
            // Skip the header
            br.readLine();
            while ((line = br.readLine()) != null) {
                String[] parts = line.split(",");
                if (parts.length >= 5) {
                    String transformedX = parts[3].trim();
                    String transformedY = parts[4].trim();
                    transformedCoordinates.add(transformedX + "," + transformedY);
                }
            }
        }
        System.out.println("Loaded " + transformedCoordinates.size() + " transformed coordinates from the CSV file.");
        return transformedCoordinates;
    }

    private static void checkCoordinatesInXML(Set<String> transformedCoordinates, String xmlFilePath) throws Exception {
        // Parse the XML file
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        DocumentBuilder builder = factory.newDocumentBuilder();
        Document document = builder.parse(new File(xmlFilePath));
        document.getDocumentElement().normalize();

        // Extract all coordinate values from the XML file
        NodeList nodeList = document.getElementsByTagName("node");
        Set<String> xmlCoordinates = new HashSet<>();
        for (int i = 0; i < nodeList.getLength(); i++) {
            Node node = nodeList.item(i);
            if (node.getNodeType() == Node.ELEMENT_NODE) {
                Element element = (Element) node;
                String x = element.getAttribute("x");
                String y = element.getAttribute("y");
                xmlCoordinates.add(x + "," + y);
            }
        }
        System.out.println("Loaded " + xmlCoordinates.size() + " coordinates from the XML file.");

        // Check for matches
        int foundCount = 0;
        int notFoundCount = 0;
        for (String coord : transformedCoordinates) {
            if (xmlCoordinates.contains(coord)) {
                foundCount++;
                System.out.println("Found: " + coord);

            } else {
                notFoundCount++;
                System.out.println("Not Found: " + coord);
            }
        }
        System.err.println("Total Found: " + foundCount);
        System.err.println("Total Not Found: " + notFoundCount);
    }
}