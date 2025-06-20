/*
 * *********************************************************************** *
 * project: org.matsim.*
 * *********************************************************************** *
 *                                                                         *
 * copyright       : (C) 2019 by the members listed in the COPYING,        *
 *                   LICENSE and WARRANTY file.                            *
 * email           : info at matsim dot org                                *
 *                                                                         *
 * *********************************************************************** *
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *   See also COPYING, LICENSE and WARRANTY file                           *
 *                                                                         *
 * *********************************************************************** *
 */

package org.matsim.contrib.rlev.charging;
import org.matsim.contrib.rlev.fleet.ElectricVehicle;

/**
 * @author Michal Maciejewski (michalm)
 */
public class DynamicChargerStrategy implements ChargingStrategy {

	public DynamicChargerStrategy(double maxSoc) {
		if (maxSoc < 0 || maxSoc > 1) {
			throw new IllegalArgumentException();
		}
	}

	@Override
	public double calcRemainingEnergyToCharge(ElectricVehicle ev) {
		return 1;
	}

	@Override
	public double calcRemainingTimeToCharge(ElectricVehicle ev) {
		return 1;
	}
}
