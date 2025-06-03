package org.matsim.contrib.rlev.temperature;

import org.matsim.core.events.handler.EventHandler;

public interface TemperatureChangeEventHandler extends EventHandler {
    void handleEvent(TemperatureChangeEvent event);

}
