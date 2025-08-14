package org.matsim.contrib.rlev.charging;

import org.matsim.contrib.rlev.fleet.ElectricVehicle;

import java.util.Collection;

public interface ChargingWithAssignmentLogic extends ChargingLogic {
	void assignVehicle(ElectricVehicle ev);

	void unassignVehicle(ElectricVehicle ev);

	Collection<ElectricVehicle> getAssignedVehicles();
}
