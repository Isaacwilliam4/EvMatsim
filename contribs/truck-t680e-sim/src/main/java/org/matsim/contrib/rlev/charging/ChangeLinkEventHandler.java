package org.matsim.contrib.rlev.charging;

import org.matsim.core.events.handler.EventHandler;

public interface ChangeLinkEventHandler extends EventHandler{
    void handleEvent(ChangeLinkEvent event);
}
