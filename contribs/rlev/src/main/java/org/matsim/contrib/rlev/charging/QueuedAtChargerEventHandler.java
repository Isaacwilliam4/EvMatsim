package org.matsim.contrib.rlev.charging;

import org.matsim.core.events.handler.EventHandler;

public interface QueuedAtChargerEventHandler extends EventHandler {
	void handleEvent(QueuedAtChargerEvent event);
}
