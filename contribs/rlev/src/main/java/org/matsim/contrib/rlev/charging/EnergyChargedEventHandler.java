package org.matsim.contrib.rlev.charging;

import org.matsim.core.events.handler.EventHandler;

/**
 * @author Michal Maciejewski (michalm)
 */
public interface EnergyChargedEventHandler extends EventHandler {
	void handleEvent(EnergyChargedEvent event);
}
