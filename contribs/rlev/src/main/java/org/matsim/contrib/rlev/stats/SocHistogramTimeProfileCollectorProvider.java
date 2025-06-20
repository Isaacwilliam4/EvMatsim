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

package org.matsim.contrib.rlev.stats;

import static org.matsim.contrib.common.timeprofile.TimeProfileCollector.ProfileCalculator;

import java.awt.Color;

import org.matsim.contrib.common.histogram.UniformHistogram;
import org.matsim.contrib.common.timeprofile.TimeProfileCharts;
import org.matsim.contrib.common.timeprofile.TimeProfileCharts.ChartType;
import org.matsim.contrib.common.timeprofile.TimeProfileCollector;
import org.matsim.contrib.rlev.fleet.ElectricFleet;
import org.matsim.contrib.rlev.fleet.ElectricVehicle;
import org.matsim.core.controler.MatsimServices;
import org.matsim.core.mobsim.framework.listeners.MobsimListener;

import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.inject.Inject;
import com.google.inject.Provider;

public class SocHistogramTimeProfileCollectorProvider implements Provider<MobsimListener> {
	private final ElectricFleet evFleet;
	private final MatsimServices matsimServices;

	@Inject
	public SocHistogramTimeProfileCollectorProvider(ElectricFleet evFleet, MatsimServices matsimServices) {
		this.evFleet = evFleet;
		this.matsimServices = matsimServices;
	}

	@Override
	public MobsimListener get() {
		var header = ImmutableList.of("0+", "0.1+", "0.2+", "0.3+", "0.4+", "0.5+", "0.6+", "0.7+", "0.8+", "0.9+");
		ProfileCalculator calculator = () -> {
			var histogram = new UniformHistogram(0.1, header.size());
			for (ElectricVehicle ev : evFleet.getElectricVehicles().values()) {
				histogram.addValue(ev.getBattery().getCharge() / ev.getBattery().getCapacity());
			}

			ImmutableMap.Builder<String, Double> builder = ImmutableMap.builder();
			for (int b = 0; b < header.size(); b++) {
				builder.put(header.get(b), (double)histogram.getCount(b));
			}
			return builder.build();
		};

		var collector = new TimeProfileCollector(header, calculator, 60, "soc_histogram_time_profiles", matsimServices);
		collector.setChartTypes(ChartType.StackedArea);
		collector.setChartCustomizer((chart, chartType) -> TimeProfileCharts.changeSeriesColors(chart, new Color(0, 0f, 0), // 0+
				new Color(1, 0f, 0), // 0.1+
				new Color(1, .25f, 0), // 0.2+
				new Color(1, .5f, 0), // 0.3+
				new Color(1, .75f, 0), // 0.4+
				new Color(1f, 1, 0), // 0.5+
				new Color(.75f, 1, 0), // 0.6+
				new Color(.5f, 1, 0), // 0.7+
				new Color(.25f, 1, 0), // 0.8+
				new Color(0f, 1, 0) // 0.9+
		));
		return collector;
	}
}
