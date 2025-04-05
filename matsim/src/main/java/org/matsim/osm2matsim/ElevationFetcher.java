import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.*;

public class ElevationFetcher {
    public static void main(String[] args) {
        if (args.length < 2) {
            System.out.println("Usage: java ElevationFetcher original_coordinates.csv Elevations.csv");
            System.exit(1);
        }

        String inputCsv = args[0];
        String outputCsv = args[1];

        try {
            fetchAndAddElevations(inputCsv, outputCsv);
        } catch (Exception e) {
            System.err.println("Error processing elevations: " + e.getMessage());
            e.printStackTrace();
        }
    }

    private static void fetchAndAddElevations(String inputCsvFile, String outputCsvFile) throws Exception {
        System.out.println("Reading coordinates from: " + inputCsvFile);
        
        // Read input CSV
        List<String> sensorIds = new ArrayList<>();
        List<double[]> coordinates = new ArrayList<>();
        
        try (BufferedReader br = new BufferedReader(new FileReader(inputCsvFile))) {
            String line = br.readLine(); // Skip header
            while ((line = br.readLine()) != null) {
                String[] parts = line.split(",");
                if (parts.length >= 3) {
                    String sensorId = parts[0];
                    double lat = Double.parseDouble(parts[1]);
                    double lon = Double.parseDouble(parts[2]);
                    
                    sensorIds.add(sensorId);
                    coordinates.add(new double[]{lat, lon});
                }
            }
        }
        
        System.out.println("Loaded " + sensorIds.size() + " coordinates");
        
        // Process elevations in batches
        Map<String, Double> elevations = new HashMap<>();
        int batchSize = 100;
        
        for (int i = 0; i < coordinates.size(); i += batchSize) {
            int end = Math.min(i + batchSize, coordinates.size());
            List<double[]> batch = coordinates.subList(i, end);
            List<String> batchIds = sensorIds.subList(i, end);
            
            System.out.println("Processing batch " + (i/batchSize + 1) + "/" + 
                              Math.ceil((double)coordinates.size()/batchSize) + "...");
            
            // Prepare API request
            StringBuilder jsonRequest = new StringBuilder();
            jsonRequest.append("{\"locations\":[");
            
            for (int j = 0; j < batch.size(); j++) {
                double[] coord = batch.get(j);
                jsonRequest.append("{\"latitude\":" + coord[0] + ",\"longitude\":" + coord[1] + "}");
                if (j < batch.size() - 1) {
                    jsonRequest.append(",");
                }
            }
            
            jsonRequest.append("]}");
            
            // Make API call
            URL url = new URL("https://api.open-elevation.com/api/v1/lookup");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("Accept", "application/json");
            conn.setDoOutput(true);
            
            try (OutputStream os = conn.getOutputStream()) {
                byte[] input = jsonRequest.toString().getBytes("utf-8");
                os.write(input, 0, input.length);
            }
            
            int responseCode = conn.getResponseCode();
            if (responseCode == 200) {
                try (BufferedReader br = new BufferedReader(new InputStreamReader(conn.getInputStream()))) {
                    StringBuilder response = new StringBuilder();
                    String responseLine;
                    while ((responseLine = br.readLine()) != null) {
                        response.append(responseLine.trim());
                    }
                    
                    // Simple JSON parsing (you might want to use a proper JSON library)
                    String json = response.toString();
                    int resultsStart = json.indexOf("\"results\":[") + 11;
                    int resultsEnd = json.lastIndexOf("]");
                    
                    if (resultsStart >= 11 && resultsEnd > resultsStart) {
                        String resultsJson = json.substring(resultsStart, resultsEnd);
                        
                        String[] resultItems = resultsJson.split("\\},\\{");
                        for (int j = 0; j < resultItems.length; j++) {
                            String item = resultItems[j].replace("{", "").replace("}", "");
                            String[] fields = item.split(",");
                            
                            double elevation = 0;
                            for (String field : fields) {
                                if (field.contains("\"elevation\":")) {
                                    elevation = Double.parseDouble(field.split(":")[1]);
                                    break;
                                }
                            }
                            
                            if (j < batchIds.size()) {
                                elevations.put(batchIds.get(j), elevation);
                                System.out.println("Sensor " + batchIds.get(j) + ": Elevation = " + elevation + "m");
                            }
                        }
                    } else {
                        System.err.println("Unable to parse API response: " + json);
                        // Default to 0 elevation if parsing fails
                        for (String sensorId : batchIds) {
                            elevations.put(sensorId, 0.0);
                        }
                    }
                }
            } else {
                System.err.println("API Error: " + responseCode);
                try (BufferedReader br = new BufferedReader(new InputStreamReader(conn.getErrorStream()))) {
                    StringBuilder errorResponse = new StringBuilder();
                    String responseLine;
                    while ((responseLine = br.readLine()) != null) {
                        errorResponse.append(responseLine.trim());
                    }
                    System.err.println("Error response: " + errorResponse.toString());
                }
                
                // Default to 0 elevation if API fails
                for (String sensorId : batchIds) {
                    elevations.put(sensorId, 0.0);
                }
            }
            
            // Wait a bit to avoid rate limiting
            if (i + batchSize < coordinates.size()) {
                System.out.println("Waiting before next batch...");
                Thread.sleep(1000);
            }
        }
        
        // Create output directory if needed
        File outputFile = new File(outputCsvFile);
        if (outputFile.getParentFile() != null) {
            outputFile.getParentFile().mkdirs();
        }
        
        // Write results to CSV
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputCsvFile))) {
            writer.write("SensorID,Latitude,Longitude,Elevation");
            writer.newLine();
            
            for (int i = 0; i < sensorIds.size(); i++) {
                String sensorId = sensorIds.get(i);
                double[] coord = coordinates.get(i);
                double elevation = elevations.getOrDefault(sensorId, 0.0);
                
                writer.write(sensorId + "," + coord[0] + "," + coord[1] + "," + elevation);
                writer.newLine();
            }
        }
        
        System.out.println("Successfully added elevations and saved to: " + outputCsvFile);
    }
}