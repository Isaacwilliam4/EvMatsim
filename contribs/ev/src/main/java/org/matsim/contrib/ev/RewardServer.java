package org.matsim.contrib.ev;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.Reader;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;
import org.apache.commons.csv.*;
import org.apache.commons.io.FileUtils;

public class RewardServer {

    private static final BlockingQueue<RequestData> requestQueue = new LinkedBlockingQueue<>();
    private static final int THREAD_POOL_SIZE = 10;
    private static final ExecutorService executorService = Executors.newFixedThreadPool(THREAD_POOL_SIZE);
    private static final String javaHome = System.getProperty("java.home");
    private static final String javaBin = javaHome + File.separator + "bin" + File.separator + "java";
    private static final String classpath = System.getProperty("java.class.path");
    private static final String className = "org.matsim.contrib.ev.example.RunEvExampleWithEvScoring";

    public static void main(String[] args) throws Exception {
        // Set up the HTTP server
        int port = 8000;
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/getReward", new RewardHandler());
        server.setExecutor(null); // creates a default executor
        System.out.println("Starting reward server...");
        server.start();
        System.out.println("Reward server is running on https://localhost:" + port);

        executorService.submit(() -> {
            for (int i = 0; i < THREAD_POOL_SIZE; i++) {
                processRequest();
            }
        });
    }

    public static void processRequest(){
        try {
            RequestData data = requestQueue.take();
            HttpExchange exchange = data.getExchange();
            Path configPath = data.getFilePath();

            // Build the process
            ProcessBuilder processBuilder = new ProcessBuilder(
                javaBin, "-cp", classpath, className, configPath.toAbsolutePath().toString()
            );

            // Redirect error and output streams
            processBuilder.redirectErrorStream(true);

            // Start the process
            Process process = processBuilder.start();

            // Capture the output
            File logFile = new File(configPath.getParent().toString(), "log.txt");
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
                BufferedWriter writer = new BufferedWriter(new FileWriter(logFile, true))) { // 'true' appends to file
                String line;
                while ((line = reader.readLine()) != null) {
                    writer.write(line);
                    writer.newLine(); // Ensure each line is on a new line
                }
            } catch (IOException e) {
                e.printStackTrace();
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
            double reward = Double.parseDouble(lastRecord.values()[0].split(";")[1]);

            //Delete the folder
            try {
                FileUtils.deleteDirectory(configPath.getParent().toFile());
                System.out.println("Folder and subdirectories deleted successfully.");
            } catch (Exception e) {
                System.err.println("Error deleting folder: " + e.getMessage());
            }

            String response = "reward:" + reward;
            exchange.sendResponseHeaders(exitCode, response.getBytes().length);
            exchange.getResponseBody().write(response.getBytes());
            exchange.close();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static class RewardHandler extends RewardServer implements HttpHandler {
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

            RewardServer.requestQueue.add(new RequestData(exchange, configPath));
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
