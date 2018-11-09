package org.matsim.core.mobsim.qsim;

import com.google.inject.Provides;
import com.google.inject.Singleton;
import org.matsim.core.mobsim.framework.AgentSource;
import org.matsim.core.mobsim.qsim.agents.AgentFactory;
import org.matsim.core.mobsim.qsim.agents.DefaultAgentFactory;
import org.matsim.core.mobsim.qsim.agents.PopulationAgentSource;
import org.matsim.core.mobsim.qsim.agents.TransitAgentFactory;
import org.matsim.core.mobsim.qsim.interfaces.Netsim;
import org.matsim.core.mobsim.qsim.qnetsimengine.QVehicleFactory;
import org.matsim.core.mobsim.qsim.qnetsimengine.QVehicleImpl;
import org.matsim.pt.config.TransitConfigGroup;

public class PopulationModule extends AbstractQSimModule {
	public final static String COMPONENT_NAME = "PopulationAgentSource";

	@Override
	protected void configureQSim() {
		bind( AgentSource.class).to(PopulationAgentSource.class).asEagerSingleton();
		addNamedComponent(AgentSource.class, COMPONENT_NAME);
	}

	@Provides
	@Singleton
	AgentFactory provideAgentFactory(TransitConfigGroup config, Netsim simulation) {
		if (config.isUseTransit()) {
			return new TransitAgentFactory(simulation);
		} else {
			return new DefaultAgentFactory(simulation);
		}
	}
	
	@Provides
	@Singleton
	QVehicleFactory provideQVehicleFactory( ) {
		return QVehicleImpl::new;
	}
}
