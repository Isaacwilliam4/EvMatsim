/* *********************************************************************** *
 * project: org.matsim.*
 *                                                                         *
 * *********************************************************************** *
 *                                                                         *
 * copyright       : (C) 2016 by the members listed in the COPYING,        *
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
 * *********************************************************************** */

package org.matsim.contrib.rlev.example;/*
 * created by jbischoff, 19.03.2019
 */

import java.io.File;
import java.io.IOException;
import java.util.Arrays;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.TransportMode;
import org.matsim.contrib.rlev.EvConfigGroup;
import org.matsim.contrib.rlev.EvModule;
import org.matsim.contrib.rlev.charging.ChargingPower;
import org.matsim.contrib.rlev.discharging.AuxEnergyConsumption;
import org.matsim.contrib.rlev.discharging.DriveEnergyConsumption;
import org.matsim.contrib.rlev.discharging.LTHDriveEnergyConsumption;
import org.matsim.contrib.rlev.fleet.ElectricFleet;
import org.matsim.contrib.rlev.fleet.ElectricFleetSpecification;
import org.matsim.contrib.rlev.fleet.ElectricFleetUtils;
import org.matsim.contrib.rlev.infrastructure.LTHConsumptionModelReader;
import org.matsim.contrib.rlev.routing.EvNetworkRoutingProvider;
import org.matsim.contrib.rlev.scoring.EvScoringFunctionFactory;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigGroup;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.controler.AbstractModule;
import org.matsim.core.controler.Controler;
import org.matsim.core.controler.OutputDirectoryHierarchy;
import org.matsim.core.scenario.ScenarioUtils;
// import org.matsim.core.scoring.ScoringFunctionFactory;

import com.google.inject.Inject;
import com.google.inject.Provider;

public class RunEvExampleWithEvScoringWithLTHConsumption {
	static final String DEFAULT_CONFIG_FILE = "test/input/org/matsim/contrib/ev/example/RunEvExample/config.xml";
	private static final Logger log = LogManager.getLogger(RunEvExampleWithEvScoringWithLTHConsumption.class);

	public static void main(String[] args) throws IOException {
		System.setProperty("matsim.preferLocalDtds", "true");

		if (args.length > 0) {
			log.info("Starting simulation run with the following arguments:");
			log.info("args=" + Arrays.toString( args ) );
		} else {
			File localConfigFile = new File(DEFAULT_CONFIG_FILE);
			if (localConfigFile.exists()) {
				log.info("Starting simulation run with the local example config file");
				args = new String[] {DEFAULT_CONFIG_FILE};
			} else {
				log.info("Starting simulation run with the example config file from GitHub repository");
				args = new String[] {"https://raw.githubusercontent.com/matsim-org/matsim/master/contribs/ev/"
						+ DEFAULT_CONFIG_FILE};
			}
		}
		new RunEvExampleWithEvScoringWithLTHConsumption().run(args);
	}

	public void run( String[] args ) {
		Config config = ConfigUtils.loadConfig(args, new EvConfigGroup());
		config.controller().setOverwriteFileSetting(OutputDirectoryHierarchy.OverwriteFileSetting.deleteDirectoryIfExists);
		Scenario scenario = ScenarioUtils.loadScenario(config);
		Controler controler = new Controler(scenario);


		controler.addOverridingModule( new AbstractModule(){
			@Override public void install(){
				bind( AuxEnergyConsumption.Factory.class ).toInstance(
							electricVehicle -> ( beginTime, duration, linkId ) -> 0 ); //a dummy factory, as aux consumption is part of the drive consumption in the model
				bind(DriveEnergyConsumption.Factory.class).toInstance(ev -> new LTHConsumptionModelReader().readURL( ConfigGroup.getInputFileURL( config.getContext(), "MidCarMap.csv" ) ).create(ev) );
				// bind(DriveEnergyConsumption.Factory.class).toInstance(ev -> new LTHConsumptionModelReader().readURL( ConfigGroup.getInputFileURL( config.getContext(), "consumption_map.csv" ) ).create(ev) );
				bind(ElectricFleet.class).toProvider(new Provider<>() {
					@Inject private ElectricFleetSpecification fleetSpecification;
					@Inject private DriveEnergyConsumption.Factory driveConsumptionFactory;
					// @Inject private LTHDriveEnergyConsumption.Factory driveConsumptionFactory;
					@Inject private AuxEnergyConsumption.Factory auxConsumptionFactory;
					@Inject private ChargingPower.Factory chargingPowerFactory;
	
					@Override
					public ElectricFleet get() {
						return ElectricFleetUtils.createDefaultFleet(fleetSpecification, driveConsumptionFactory, auxConsumptionFactory,
								chargingPowerFactory );
					}
				}).asEagerSingleton();
	
				bindScoringFunctionFactory().to(EvScoringFunctionFactory.class);
				install( new EvModule() );

				addRoutingModuleBinding( TransportMode.car ).toProvider(new EvNetworkRoutingProvider(TransportMode.car) );
				// a router that inserts charging activities INTO THE ROUTE when the battery is run empty.  This assumes that a full
				// charge at the start of the route is not sufficient to drive the route.   There are other settings where the
				// situation is different, e.g. urban, where there may be a CHAIN of activities, and charging in general is done in
				// parallel with some of these activities.   That second situation is adressed by some "ev" code in the vsp contrib.
				// kai, dec'22
			}
		} );

		controler.run();
	}
}
