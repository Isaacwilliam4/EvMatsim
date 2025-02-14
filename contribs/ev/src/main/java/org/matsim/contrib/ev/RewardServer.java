package org.matsim.contrib.ev;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.Reader;
import java.net.InetSocketAddress;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVRecord;
import org.apache.commons.io.FileUtils;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigReader;
import org.matsim.core.config.ConfigUtils;

import java.nio.file.Files;

import com.google.common.util.concurrent.AtomicDouble;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

public class RewardServer {
    private final BlockingQueue<RequestData> requestQueue = new LinkedBlockingQueue<>();
    private int threadPoolSize;
    private ExecutorService executorService;
    private final String javaHome = System.getProperty("java.home");
    private final String javaBin = javaHome + File.separator + "bin" + File.separator + "java";
    private final String classpath = System.getProperty("java.class.path");
    private final String className = "org.matsim.contrib.ev.example.RunEvExampleWithEvScoring";
    private AtomicDouble bestReward = new AtomicDouble(Double.NEGATIVE_INFINITY);
    private AtomicBoolean initialResponse = new AtomicBoolean(true);

    public RewardServer(int threadPoolSize){
        this.threadPoolSize = threadPoolSize;
        this.executorService = Executors.newFixedThreadPool(this.threadPoolSize);
    }

    public static void main(String[] args) throws Exception {
        int argsThreadPoolSize =  Integer.parseInt(args[0]); 
        RewardServer rewardServer = new RewardServer(argsThreadPoolSize);
        // Set up the HTTP server
        int port = 8000;
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/getReward", rewardServer.new RewardHandler());
        server.setExecutor(null); // creates a default executor
        System.out.println("Starting reward server...");
        server.start();
        System.out.println("Reward server is running on https://localhost:" + port);

        for (int i = 0; i < rewardServer.threadPoolSize; i++) {
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

    public synchronized void setBestReward(double newReward){
        bestReward.set(newReward);
    }

    public synchronized double getBestReward(){
        return bestReward.get();
    }

    private static void stopServer(HttpServer server, RewardServer rewardServer) throws IOException {
        // Stop accepting new connections
        server.stop(0);

        // Gracefully shutdown the executor service
        rewardServer.executorService.shutdown();

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
                Path csvPath = new File(configPath.getParent().toString() + "/output/ITERS/it.0/0.average_charge_time_profiles.txt").toPath();
                double avgChargeIntegral = 0.0;
                double totRecords = 0.0;

                try (Reader reader = new FileReader(csvPath.toString())) {
                    Iterable<CSVRecord> records = CSVFormat.DEFAULT
                            .withFirstRecordAsHeader()
                            .parse(reader);

                    for (CSVRecord record : records) {
                        String[] vals = record.values()[0].split("\t");
                        double avgVal = Double.parseDouble(vals[2]);
                        avgChargeIntegral += avgVal;
                        totRecords += 1;
                    }
                } catch (IOException e) {
                    e.printStackTrace();
                }
                
                boolean isBestReward = false;
                double reward = 0;
                String[] response = new String[2];
                response[0] = "0.0";
                response[1] = "none";

                if (totRecords > 1){
                    reward = avgChargeIntegral / totRecords;
                    response[0] = Double.toString(reward);
                    if (reward > getBestReward()){
                        setBestReward(reward);
                        isBestReward = true;
                    }
                }

                File outputFolder = new File(configPath.getParent().toString() + "/output/");
                File zipFile = new File("output.zip");
                zipDirectory(outputFolder, zipFile);
    
                byte[] zipContent = Files.readAllBytes(zipFile.toPath());
                
                //If  its the first iteration we save the output to get something to compare
                //against, if its the best reward we save it to compare results
                if (initialResponse.get()){
                    response[1] = "firstoutput";
                    exchange.sendResponseHeaders(200, zipContent.length);
                    OutputStream os = exchange.getResponseBody();
                    os.write(zipContent);
                    exchange.close();
                }
                else if (isBestReward){
                    response[1] = "bestoutput";
                    exchange.sendResponseHeaders(200, zipContent.length);
                    OutputStream os = exchange.getResponseBody();
                    os.write(zipContent);
                    exchange.close();
                }
                
                
                exchange.getResponseHeaders().set("X-Response-Message", response);
                FileUtils.deleteDirectory(configPath.getParent().toFile());
                System.out.println("Folder and subdirectories deleted successfully.");
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private static void zipDirectory(File folder, File zipFile) throws IOException {
        FileOutputStream fos = new FileOutputStream(zipFile);
        ZipOutputStream zos = new ZipOutputStream(fos);
        zipFile(folder, folder.getName(), zos);
        zos.close();
        fos.close();
    }

    private static void zipFile(File file, String fileName, ZipOutputStream zos) throws IOException {
        if (file.isDirectory()) {
            for (File subFile : file.listFiles()) {
                zipFile(subFile, fileName + "/" + subFile.getName(), zos);
            }
        } else {
            FileInputStream fis = new FileInputStream(file);
            ZipEntry zipEntry = new ZipEntry(fileName);
            zos.putNextEntry(zipEntry);
            byte[] bytes = new byte[1024];
            int length;
            while ((length = fis.read(bytes)) >= 0) {
                zos.write(bytes, 0, length);
            }
            fis.close();
        }
    }

    public class RewardHandler implements HttpHandler {
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
