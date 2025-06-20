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

package org.matsim.contrib.rlev.fleet;

import org.matsim.contrib.rlev.EvConfigGroup;
import org.matsim.contrib.rlev.EvModule;
import org.matsim.contrib.rlev.charging.ChargingPower;
import org.matsim.contrib.rlev.discharging.AuxEnergyConsumption;
import org.matsim.contrib.rlev.discharging.DriveEnergyConsumption;
import org.matsim.contrib.rlev.scoring.EvScoringFunctionFactory;
import org.matsim.core.controler.AbstractModule;
import org.matsim.core.mobsim.framework.events.MobsimBeforeCleanupEvent;
import org.matsim.core.mobsim.framework.listeners.MobsimBeforeCleanupListener;
import org.matsim.core.mobsim.qsim.AbstractQSimModule;
import org.matsim.vehicles.Vehicles;

import com.google.inject.Inject;
import com.google.inject.Provider;

/**
 * @author Michal Maciejewski (michalm)
 */
public final class ElectricFleetModule extends AbstractModule {
	@Inject
	private EvConfigGroup evCfg;

	@Override
	public void install() {
		bind(ElectricFleetSpecification.class).toProvider(new Provider<>() {
			@Inject private Vehicles vehicles;
			@Override public ElectricFleetSpecification get() {
				ElectricFleetSpecification fleetSpecification = new ElectricFleetSpecificationDefaultImpl();
				ElectricFleetUtils.createAndAddVehicleSpecificationsFromMatsimVehicles(fleetSpecification,
						vehicles.getVehicles().values() );
				return fleetSpecification;
			}
		}).asEagerSingleton();
		
		installQSimModule(new AbstractQSimModule() {
			@Override
			protected void configureQSim() {


				if (evCfg.transferFinalSoCToNextIteration) {
					addQSimComponentBinding(EvModule.EV_COMPONENT).toInstance(new MobsimBeforeCleanupListener() {
						@Inject private ElectricFleetSpecification electricFleetSpecification;
						@Inject private ElectricFleet electricFleet;
						@Override public void notifyMobsimBeforeCleanup(MobsimBeforeCleanupEvent e) {
							for (var oldSpec : electricFleetSpecification.getVehicleSpecifications().values()) {
								var matsimVehicle = oldSpec.getMatsimVehicle();
								double socAtEndOfCurrentIteration = electricFleet.getElectricVehicles().get(oldSpec.getId()).getBattery().getSoc();
								ElectricFleetUtils.setInitialSoc(matsimVehicle, socAtEndOfCurrentIteration );
							}
						}
					});
				}
				else {
					addQSimComponentBinding(EvModule.EV_COMPONENT).toInstance(new MobsimBeforeCleanupListener() {
						@Inject private ElectricFleetSpecification electricFleetSpecification;
						@Inject private ElectricFleet electricFleet;
						@Override public void notifyMobsimBeforeCleanup(MobsimBeforeCleanupEvent e) {
							for (var oldSpec : electricFleetSpecification.getVehicleSpecifications().values()) {
								double initialSoc = electricFleet.getElectricVehicles().get(oldSpec.getId()).getVehicleSpecification().getInitialCharge();
								electricFleet.getElectricVehicles().get(oldSpec.getId()).getBattery().setCharge(initialSoc);
							}
						}
					});
				}
			}
		});
	}
}
