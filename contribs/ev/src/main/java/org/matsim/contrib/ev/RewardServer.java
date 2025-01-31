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
import java.io.Reader;
import java.net.InetSocketAddress;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVRecord;
import org.apache.commons.io.FileUtils;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigReader;
import org.matsim.core.config.ConfigUtils;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

public class RewardServer {
    private final BlockingQueue<RequestData> requestQueue = new LinkedBlockingQueue<>();
    private final int THREAD_POOL_SIZE = 10;
    private final ExecutorService executorService = Executors.newFixedThreadPool(THREAD_POOL_SIZE);
    private final String javaHome = System.getProperty("java.home");
    private final String javaBin = javaHome + File.separator + "bin" + File.separator + "java";
    private final String classpath = System.getProperty("java.class.path");
    private final String className = "org.matsim.contrib.ev.example.RunEvExampleWithEvScoring";

    public static void main(String[] args) throws Exception {
        RewardServer rewardServer = new RewardServer();

        // Set up the HTTP server
        int port = 8000;
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/getReward", rewardServer.new RewardHandler());
        server.setExecutor(null); // creates a default executor
        System.out.println("Starting reward server...");
        server.start();
        System.out.println("Reward server is running on https://localhost:" + port);

        for (int i = 0; i < rewardServer.THREAD_POOL_SIZE; i++) {
            System.out.println("Starting thread: " + i);
            rewardServer.executorService.submit(() -> {
                rewardServer.processRequest();
            });
        }


        // Register shutdown hook for graceful shutdown
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            try {
                System.out.println("Shutting down server...");
                stopServer(server, rewardServer);
            } catch (IOException e) {
                e.printStackTrace();
            }
        }));
    }

    private static void stopServer(HttpServer server, RewardServer rewardServer) throws IOException {
        // Stop accepting new connections
        server.stop(0);

        // Gracefully shutdown the executor service
        rewardServer.executorService.shutdown();
        try {
            if (!rewardServer.executorService.awaitTermination(60, TimeUnit.SECONDS)) {
                rewardServer.executorService.shutdownNow();
                if (!rewardServer.executorService.awaitTermination(60, TimeUnit.SECONDS)) {
                    System.err.println("Executor service did not terminate in time.");
                }
            }
        } catch (InterruptedException e) {
            rewardServer.executorService.shutdownNow();
            Thread.currentThread().interrupt();
        }

        System.out.println("Server shut down gracefully.");
    }

    public void processRequest() {
        while (!Thread.currentThread().isInterrupted()) {
            try {
                System.out.println(Thread.currentThread().getName() + " Waiting for request...");
                RequestData data = this.requestQueue.take();
                HttpExchange exchange = data.getExchange();
                Path configPath = data.getFilePath();
                System.out.println("Processing request for config file: " +
                 configPath + " with thread: " + Thread.currentThread().getName());

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
                     BufferedWriter writer = new BufferedWriter(new FileWriter(logFile, true))) {
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
                    Iterable<CSVRecord> records = CSVFormat.DEFAULT
                            .withFirstRecordAsHeader()
                            .parse(reader);

                    for (CSVRecord record : records) {
                        lastRecord = record;
                    }
                } catch (IOException e) {
                    e.printStackTrace();
                }

                // Parse the csv path to get the reward
                double reward = Double.parseDouble(lastRecord.values()[0].split(";")[1]);

                // Delete the folder
                try {
                    FileUtils.deleteDirectory(configPath.getParent().toFile());
                    System.out.println("Folder and subdirectories deleted successfully.");
                } catch (Exception e) {
                    System.err.println("Error deleting folder: " + e.getMessage());
                }

                String response = "reward:" + reward;
                exchange.sendResponseHeaders(200, response.getBytes().length);
                exchange.getResponseBody().write(response.getBytes());
                exchange.close();
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    public class RewardHandler extends RewardServer implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
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

            String folderString = Long.toString(System.nanoTime()); 
            Path folderPath = new File("/tmp/" + folderString).toPath();

            folderPath.toFile().mkdirs();
            Path configPath = null;
            for (String part : parts) {
                if (part.contains("Content-Disposition")) {
                    String[] lines = part.split("\r\n");
                    String fileName = extractFileName(lines);
                    if (fileName != null) {
                        if (fileName.contains("config")) {
                            configPath = new File(folderPath + "/" + fileName).toPath();
                        }
                        byte[] fileContent = extractFileContent(part);
                        saveFile(folderPath, fileName, fileContent);
                    }
                }
            }

            System.out.println("Adding request for config file: " +
            configPath + " to queue for processing");
            
            URL url = configPath.toUri().toURL();
            Config config = new Config();
            new ConfigReader(config).parse(url);

            config.setParam("controller", "outputDirectory", folderPath.toString() + "/output");
            ConfigUtils.writeConfig(config, configPath.toString());

            // Add the request to the queue
            requestQueue.add(new RequestData(exchange, configPath));
        }
    }

    private void saveFile(Path folderPath, String fileName, byte[] fileContent) throws IOException {
        try (FileOutputStream fileOutput = new FileOutputStream(folderPath + "/" + fileName)) {
            fileOutput.write(fileContent);
        }
    }

    private String extractFileName(String[] lines) {
        for (String line : lines) {
            if (line.contains("filename")) {
                return line.split(";")[2].split("=")[1].replace("\"","");
            }
        }
        return null;
    }

    private byte[] extractFileContent(String part) {
        int startIndex = part.indexOf("\r\n\r\n") + 4;
        int endIndex = part.lastIndexOf("\r\n--");
        return part.substring(startIndex, endIndex).getBytes(StandardCharsets.UTF_8);
    }

    private static class RequestData {
        private final HttpExchange exchange;
        private final Path filePath;

        public RequestData(HttpExchange exchange, Path filePath) {
            this.exchange = exchange;
            this.filePath = filePath;
        }

        public HttpExchange getExchange() {
            return exchange;
        }

        public Path getFilePath() {
            return filePath;
        }
    }

}
