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
import java.util.ArrayList;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVRecord;
import org.apache.commons.io.FileUtils;
import org.jfree.data.json.impl.JSONObject;
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

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import org.w3c.dom.*;
import java.util.List;

public class FlowRewardServer {
    private final BlockingQueue<RequestData> requestQueue = new LinkedBlockingQueue<>();
    private int threadPoolSize;
    private ExecutorService executorService;
    private final String javaHome = System.getProperty("java.home");
    private final String javaBin = javaHome + File.separator + "bin" + File.separator + "java";
    private final String classpath = System.getProperty("java.class.path");
    private final String className = "org.matsim.run.RunMatsim";
    private AtomicDouble bestReward = new AtomicDouble(Double.NEGATIVE_INFINITY);
    private AtomicBoolean initialResponse = new AtomicBoolean(true);

    public FlowRewardServer(int threadPoolSize){
        this.threadPoolSize = threadPoolSize;
        this.executorService = Executors.newFixedThreadPool(this.threadPoolSize);
    }

    public static void main(String[] args) throws Exception {
        int argsThreadPoolSize =  Integer.parseInt(args[0]); 
        FlowRewardServer rewardServer = new FlowRewardServer(argsThreadPoolSize);
        // Set up the HTTP server
        int port = 8000;
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        System.setProperty("matsim.preferLocalDtds", "true");
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

    private static void stopServer(HttpServer server, FlowRewardServer rewardServer) throws IOException {
        // Stop accepting new connections
        server.stop(0);

        // Gracefully shutdown the executor service
        rewardServer.executorService.shutdown();

        System.out.println("Server shut down gracefully.");
    }

    @SuppressWarnings("unchecked")
    public void processRequest() {
        while (!Thread.currentThread().isInterrupted()) {
            HttpExchange exchange = null;
            try {
                System.out.println(Thread.currentThread().getName() + " Waiting for request...");
                RequestData data = this.requestQueue.take();
                exchange = data.getExchange();
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

                Config config = new Config();
                new ConfigReader(config).parse(configPath.toUri().toURL()); 

                ConfigUtils.writeConfig(config, configPath.toString());

                // Wait for the process to complete and get the exit value
                int exitCode = process.waitFor();
                System.out.println("Process exited with code: " + exitCode);
                Path csvPath = new File(configPath.getParent().toString() + "/output/ITERS/it.0/0.countscompare.txt").toPath();
                double totDistributionDiff = 0.0;
                int totRecords = 0;

                Reader reader = new FileReader(csvPath.toString());
                Iterable<CSVRecord> records = CSVFormat.DEFAULT
                        .withFirstRecordAsHeader()
                        .parse(reader);
                //Columns: Link Id	Count Station Id	Hour	MATSIM volumes	Count volumes	Relative Error	Normalized Relative Error	GEH
                for (CSVRecord record : records) {
                    String[] vals = record.values()[0].split("\t");
                    var matsimVolume = Double.parseDouble(vals[3]);
                    var countVolume = Double.parseDouble(vals[4]);
                    totDistributionDiff += Math.abs(matsimVolume - countVolume);
                    totRecords += 1;
                }

                JSONObject response = new JSONObject();
                response.put("filetype", "none");
                double reward = 0;

                if (totRecords > 1){
                    reward = 1 / (1 + Math.log10(totDistributionDiff + 1));
                    response.put("reward", Double.toString(reward));
                    if (reward > getBestReward()){
                        setBestReward(reward);
                    }
                }

                File outputFolder = new File(configPath.getParent().toString() + "/output/");
                File zipFile = new File(configPath.getParent().toString() + "/output.zip");
                zipDirectory(outputFolder, zipFile);
                
                byte[] zipContent = Files.readAllBytes(zipFile.toPath());
                
                //If  its the first iteration we save the output to get something to compare
                if (initialResponse.get()){
                    response.put("filetype", "initialoutput");
                    exchange.getResponseHeaders().set("X-Response-Message", response.toString());
                    exchange.sendResponseHeaders(200, zipContent.length);
                    OutputStream os = exchange.getResponseBody();
                    os.write(zipContent);
                    initialResponse.set(false);
                }
                else {
                    response.put("filetype", "output");
                    exchange.getResponseHeaders().set("X-Response-Message", response.toString());
                    exchange.sendResponseHeaders(200, zipContent.length);
                    OutputStream os = exchange.getResponseBody();
                    os.write(zipContent);
                }
                FileUtils.deleteDirectory(configPath.getParent().toFile());
                System.out.println("Folder and subdirectories deleted successfully.");
            } catch (Exception e) {
                e.printStackTrace();
            }
            finally{
                if (exchange != null){
                    exchange.close();
                }
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
