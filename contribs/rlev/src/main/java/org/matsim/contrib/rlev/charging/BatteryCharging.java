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

import org.matsim.contrib.rlev.infrastructure.ChargerSpecification;

/**
 * In order to simulate charging, we only need ChargingPower (no need to implement BatteryCharging), which is easier
 * to implement (and faster to compute). It works well if we simulate charging with relatively small time steps.
 * <p>
 * BatteryCharging extends ChargingPower and introduces methods for computing charging times/energies in a longer time
 * horizon (e.g. charging time until the SoC reaches 90%, or recharged energy given 1 hour of charging).
 * These additional methods are useful for instance in the eVRP context, where we need to plan charging along
 * with other tasks.
 *
 * @author Michal Maciejewski (michalm)
 */
public interface BatteryCharging extends ChargingPower {

	double calcEnergyCharged(ChargerSpecification charger, double chargingPeriod);

	double calcChargingTime(ChargerSpecification charger, double energy);
}
