package org.matsim.contrib.ev;

import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpExchange;
import org.matsim.contrib.ev.HttpRequestParser;
import java.io.*;
import java.util.List;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import org.apache.commons.io.IOUtils;
import org.apache.commons.fileupload.*;
import org.apache.commons.fileupload.disk.DiskFileItemFactory;
import org.apache.commons.fileupload.servlet.ServletFileUpload;

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

    static class RewardHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            HttpRequestParser parser = new HttpRequestParser();
            InputStream is = exchange.getRequestBody();
            String result = IOUtils.toString(is, StandardCharsets.UTF_8);
            
            try{
                parser.parseRequest(result);
            }
            catch(Exception e){
                e.printStackTrace();
            }

            System.out.println("Request received: " + result);

        }

        private String calculateReward(String[] params) {
            // Logic to calculate reward based on input params
            // For example, if the params represent EV charging states, calculate reward based on efficiency
            return "Reward: 10.0"; // Placeholder reward
        }
    }
}
