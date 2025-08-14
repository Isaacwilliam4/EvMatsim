package org.matsim.contrib.rlev.charging;

import org.matsim.core.events.handler.EventHandler;

public interface ChargingStartEventHandler extends EventHandler {
    void handleEvent(ChargingStartEvent event);
}
