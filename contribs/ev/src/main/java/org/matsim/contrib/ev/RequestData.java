package org.matsim.contrib.ev;

import java.nio.file.Path;

import com.sun.net.httpserver.HttpExchange;

public class RequestData {
    private HttpExchange exchange;
    private Path filePath;

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
