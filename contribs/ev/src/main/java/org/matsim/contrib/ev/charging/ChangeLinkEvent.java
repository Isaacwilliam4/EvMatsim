package org.matsim.contrib.ev.charging;

import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.events.Event;
import org.matsim.api.core.v01.events.GenericEvent;
import org.matsim.api.core.v01.network.Link;
import org.matsim.vehicles.Vehicle;

import java.util.Map;

public class ChangeLinkEvent extends Event{
    public static final String EVENT_TYPE = "link_changed";
	public static final String ATTRIBUTE_VEHICLE = "vehicle";
	public static final String ATTRIBUTE_OLDLINK = "old_link";
	public static final String ATTRIBUTE_CURRENTLINK = "current_link";

    private final Id<Vehicle> vehicleId;
    private final Id<Link> oldLinkId;
    private final Id<Link> currentLinkId; 

    public ChangeLinkEvent(double time, Id<Link> oldLinkId, Id<Link> currentLinkId, Id<Vehicle> vehicleId){
        super(time);
        this.vehicleId = vehicleId;
        this.oldLinkId = oldLinkId;
        this.currentLinkId = currentLinkId;
    }

	public Id<Vehicle> getVehicleId() {
		return vehicleId;
	}

	public Id<Link> getOldLinkId() {
		return oldLinkId;
	}

	public Id<Link> getCurrentLinkId() {
		return currentLinkId;
	}

    @Override
    public String getEventType() {
        return EVENT_TYPE;
    }

	@Override
	public Map<String, String> getAttributes() {
		Map<String, String> attr = super.getAttributes();
		attr.put(ATTRIBUTE_OLDLINK, oldLinkId + "");
		attr.put(ATTRIBUTE_CURRENTLINK, currentLinkId + "");
		attr.put(ATTRIBUTE_VEHICLE, vehicleId + "");
		return attr;
	}

	public static ChangeLinkEvent convert(GenericEvent genericEvent) {
		Map<String, String> attributes = genericEvent.getAttributes();
		double time = genericEvent.getTime();
		Id<Vehicle> vehicleId = Id.createVehicleId(attributes.get(ChangeLinkEvent.ATTRIBUTE_VEHICLE));
		Id<Link> oldLinkId = Id.createLinkId(attributes.get(ChangeLinkEvent.ATTRIBUTE_OLDLINK));
		Id<Link> currentLinkId = Id.createLinkId(attributes.get(ChangeLinkEvent.ATTRIBUTE_CURRENTLINK));
		return new ChangeLinkEvent(time, oldLinkId, currentLinkId, vehicleId);
	}
    
}
