package org.matsim.contrib.ev;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;


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

            // Parse each part
            for (String part : parts) {
                if (part.contains("Content-Disposition")) {
                    // Extract file content and metadata
                    String[] lines = part.split("\r\n");

                    // Get the file name from Content-Disposition
                    String fileName = extractFileName(lines);
                    if (fileName != null) {
                        // Get the file content
                        byte[] fileContent = extractFileContent(part);
                        saveFile(fileName, fileContent);
                    }
                }
            }

            // Send a response back (example: successful upload)
            String response = "Files uploaded successfully!";
            exchange.sendResponseHeaders(200, response.getBytes().length);
            OutputStream os = exchange.getResponseBody();
            os.write(response.getBytes());
            os.close();
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
            return part.substring(contentStart).getBytes(StandardCharsets.UTF_8);
        }

        private void saveFile(String fileName, byte[] content) throws IOException {
            // Save the file to the server's filesystem
            File file = new File("/tmp/scenario/" + fileName);
            if (!file.getParentFile().exists()) {
                file.getParentFile().mkdirs();
            }
            try (FileOutputStream fos = new FileOutputStream(file)) {
                fos.write(content);
            }
        }
    }
}
