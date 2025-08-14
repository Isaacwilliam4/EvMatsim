package org.matsim.contrib.rlev;

import org.matsim.contrib.rlev.charging.ChargingModule;
import org.matsim.contrib.rlev.discharging.DischargingModule;
import org.matsim.contrib.rlev.fleet.ElectricFleetModule;
import org.matsim.contrib.rlev.infrastructure.ChargingInfrastructureModule;
import org.matsim.contrib.rlev.stats.EvStatsModule;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.controler.AbstractModule;
import org.matsim.core.mobsim.qsim.components.QSimComponentsConfigGroup;

import java.util.List;

public class EvBaseModule extends AbstractModule {
	public void install(){
		install(new ElectricFleetModule() );
		install(new ChargingInfrastructureModule() );
		install(new ChargingModule() );
		install(new DischargingModule() );
		install(new EvStatsModule() );
		{
			// this switches on all the QSimComponents that are registered at various places under EvModule.EV_Component.
			ConfigUtils.addOrGetModule( this.getConfig(), QSimComponentsConfigGroup.class ).addActiveComponent( EvModule.EV_COMPONENT );
		}
	}

}
