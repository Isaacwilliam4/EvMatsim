package org.matsim.contrib.ev;

import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;

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
            // Example: Parse input parameters from the URL
            // String query = exchange.getRequestURI().getQuery();
            // String[] params = query.split("&");
            String[] params = {"blah", "blah"};
            String reward = calculateReward(params);

            // Send the reward as a response
            exchange.sendResponseHeaders(200, reward.getBytes().length);
            OutputStream os = exchange.getResponseBody();
            os.write(reward.getBytes());
            os.close();
        }

        private String calculateReward(String[] params) {
            // Logic to calculate reward based on input params
            // For example, if the params represent EV charging states, calculate reward based on efficiency
            return "Reward: 10.0"; // Placeholder reward
        }
    }
}
