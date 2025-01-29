package org.matsim.contrib.ev;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.io.Reader;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import javax.xml.transform.Transformer;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;
import org.apache.commons.csv.*;
import org.apache.commons.io.FileUtils;
import org.w3c.dom.*;

public class RewardServer {

    public static void main(String[] args) throws Exception {
        // Set up the HTTP server
        int port = 8000;
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/getReward", new RewardHandler());
        server.setExecutor(null); // creates a default executor
        System.out.println("Starting reward server...");
        server.start();
        System.out.println("Reward server is running on https://localhost:" + port);
    }

    public static class RewardHandler implements HttpHandler {
        // This method processes the incoming request and saves the files to disk
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            // Get the content type from the request headers (should include boundary info)
            String folderString = exchange.getRequestURI().getQuery().split("&")[0].split("=")[1];
            String contentType = exchange.getRequestHeaders().getFirst("Content-Type");
            if (contentType == null || !contentType.contains("multipart/form-data")) {
                exchange.sendResponseHeaders(400, -1); // Bad request
                return;
            }

            String boundary = contentType.split("boundary=")[1];

            // Read the request body
            InputStream inputStream = exchange.getRequestBody();
            ByteArrayOutputStream bodyOutput = new ByteArrayOutputStream();
            byte[] buffer = new byte[1024];
            int bytesRead;
            while ((bytesRead = inputStream.read(buffer)) != -1) {
                bodyOutput.write(buffer, 0, bytesRead);
            }
            byte[] body = bodyOutput.toByteArray();

            // Split the body by the boundary
            String bodyString = new String(body, StandardCharsets.UTF_8);
            String[] parts = bodyString.split(boundary);
            Path folderPath = new File("/tmp/" + folderString).toPath();

            folderPath.toFile().mkdirs();
            Path configPath = null;
            // Parse each part
            for (String part : parts) {
                if (part.contains("Content-Disposition")) {
                    // Extract file content and metadata
                    String[] lines = part.split("\r\n");

                    // Get the file name from Content-Disposition
                    String fileName = extractFileName(lines);
                    if (fileName != null) {
                        if (fileName.contains("config")) {
                            configPath = new File(folderPath + "/" + fileName).toPath();
                        }
                        // Get the file content
                        byte[] fileContent = extractFileContent(part);
                        saveFile(folderPath, fileName, fileContent);
                    }
                }
            }

            //Run matsim with the config file and get reward
            double reward = runMatsimInstance(configPath);

            //Delete the folder
            try {
                FileUtils.deleteDirectory(folderPath.toFile());
                System.out.println("Folder and subdirectories deleted successfully.");
            } catch (Exception e) {
                System.err.println("Error deleting folder: " + e.getMessage());
            }

            // Send a response back (example: successful upload)
            String response = "Files uploaded successfully!";
            exchange.sendResponseHeaders(200, response.getBytes().length);
            OutputStream os = exchange.getResponseBody();
            os.write(response.getBytes());
            os.close();
        }

        private double runMatsimInstance(Path configPath) {
            try {
                // Command to run the Java process
                String javaHome = System.getProperty("java.home");
                String javaBin = javaHome + File.separator + "bin" + File.separator + "java";
                String classpath = System.getProperty("java.class.path");
                String className = "org.matsim.contrib.ev.example.RunEvExampleWithEvScoring"; // Replace with the class you want to execute

                // Build the process
                ProcessBuilder processBuilder = new ProcessBuilder(
                    javaBin, "-cp", classpath, className, configPath.toAbsolutePath().toString()
                );

                // Redirect error and output streams
                processBuilder.redirectErrorStream(true);

                // Start the process
                Process process = processBuilder.start();

                // Capture the output
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(process.getInputStream()))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        System.out.println(line);
                    }
                }
                // Wait for the process to complete and get the exit value
                int exitCode = process.waitFor();
                System.out.println("Process exited with code: " + exitCode);
                Path csvPath = new File(configPath.getParent().toString() + "/output/scorestats.csv").toPath();
                CSVRecord lastRecord = null;

                try (Reader reader = new FileReader(csvPath.toString())) {
                    // Parse the CSV file
                    Iterable<CSVRecord> records = CSVFormat.DEFAULT
                            .withFirstRecordAsHeader()
                            .parse(reader);
    
                    for (CSVRecord record : records) {
                        lastRecord = record;
                }
                } catch (IOException e) {
                    e.printStackTrace();
                }
                // parse the csv path to get the reward
                double reward = Double.parseDouble(lastRecord.get("avg_executed"));
                return reward;

            } catch (Exception e) {
                e.printStackTrace();
            }
            return 0.0;
        }

        private String extractFileName(String[] lines) {
            for (String line : lines) {
                if (line.startsWith("Content-Disposition")) {
                    // Use regex to extract the filename from the header
                    Pattern pattern = Pattern.compile("filename=\"([^\"]+)\"");
                    Matcher matcher = pattern.matcher(line);
                    if (matcher.find()) {
                        return matcher.group(1); // Return filename
                    }
                }
            }
            return null;
        }

        private byte[] extractFileContent(String part) {
            // Find the position where the file content starts (skip headers)
            int contentStart = part.indexOf("\r\n\r\n") + 4; // Skip headers
        
            // Find the position of the last CRLF before the boundary
            // The last line contains invalid characters for xml, hence the removal
            int contentEnd = part.lastIndexOf("\r\n");
        
            // Ensure contentEnd is valid and greater than contentStart
            if (contentEnd > contentStart) {
                part = part.substring(contentStart, contentEnd); // Exclude the last line
            } else {
                part = part.substring(contentStart); // No valid end, take the entire content
            }
        
            return part.getBytes(StandardCharsets.UTF_8);
        }

        private void saveFile(Path folderPath, String fileName, byte[] content) throws IOException {
            // Save the file to the server's filesystem
            File file = new File(folderPath.toString() + "/" + fileName);

            try (FileOutputStream fos = new FileOutputStream(file)) {
                fos.write(content);
            }
        }
    }
}
