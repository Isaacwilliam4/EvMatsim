package org.matsim.contrib.ev.charging;

import com.google.common.base.Preconditions;
import com.google.inject.Inject;
import com.google.inject.Provider;

import org.matsim.api.core.v01.Id;
import org.matsim.contrib.ev.fleet.ElectricVehicle;
import org.matsim.contrib.ev.infrastructure.ChargerSpecification;
import org.matsim.core.api.experimental.events.EventsManager;
import org.matsim.vehicles.Vehicle;

import java.util.concurrent.LinkedBlockingQueue;
import java.util.function.Function;
import java.util.*;

import org.matsim.contrib.ev.charging.ChargingLogic;
import org.matsim.contrib.ev.fleet.ElectricVehicle;
import org.matsim.contrib.ev.infrastructure.ChargerSpecification;
import org.matsim.core.api.experimental.events.EventsManager;

public class DynamicChargingLogic implements ChargingLogic{
    protected final ChargerSpecification charger;
	private final ChargingStrategy chargingStrategy;
	private final EventsManager eventsManager;

	private final Map<Id<Vehicle>, ElectricVehicle> vehiclesOnChargingLink = new LinkedHashMap<>();
	private final Queue<ElectricVehicle> arrivingVehicles = new LinkedBlockingQueue<>();
	private final Map<Id<Vehicle>, ChargingListener> listeners = new LinkedHashMap<>();

    public DynamicChargingLogic(ChargerSpecification charger, ChargingStrategy chargingStrategy, EventsManager eventsManager){
        this.chargingStrategy = Objects.requireNonNull(chargingStrategy);
		this.charger = Objects.requireNonNull(charger);
		this.eventsManager = Objects.requireNonNull(eventsManager);
	}
    
    @Override
    public void chargeVehicles(double chargePeriod, double now) {
		Iterator<ElectricVehicle> evIter = vehiclesOnChargingLink.values().iterator();
		while (evIter.hasNext()) {
			ElectricVehicle ev = evIter.next();
			// with dynamic charging we charge the vehicle as it drives on the link
			double oldCharge = ev.getBattery().getCharge();
			double energy = ev.getChargingPower().calcChargingPower(charger) * chargePeriod;
			double newCharge = Math.min(oldCharge + energy, ev.getBattery().getCapacity());
			ev.getBattery().setCharge(newCharge);
			eventsManager.processEvent(new EnergyChargedEvent(now, charger.getId(), ev.getId(), newCharge - oldCharge, newCharge));
		}

		var arrivingVehiclesIter = arrivingVehicles.iterator();
		while (arrivingVehiclesIter.hasNext()) {
			var ev = arrivingVehiclesIter.next();
			plugVehicle(ev, now);
			arrivingVehiclesIter.remove();
		}
	}

    private void plugVehicle(ElectricVehicle ev, double now) {
		if (vehiclesOnChargingLink.put(ev.getId(), ev) != null) {
			throw new IllegalArgumentException();
		}
		eventsManager.processEvent(new ChargingStartEvent(now, charger.getId(), ev.getId(), ev.getBattery().getCharge()));
		listeners.get(ev.getId()).notifyChargingStarted(ev, now);
	}

	@Override
	public void addVehicle(ElectricVehicle ev, double now) {
		addVehicle(ev, new ChargingListener() {
		}, now);
	}

	@Override
	public void addVehicle(ElectricVehicle ev, ChargingListener chargingListener, double now) {
		arrivingVehicles.add(ev);
		listeners.put(ev.getId(), chargingListener);
	}

	@Override
	public void removeVehicle(ElectricVehicle ev, double now) {
		if (vehiclesOnChargingLink.remove(ev.getId()) != null) {// successfully removed
			eventsManager.processEvent(new ChargingEndEvent(now, charger.getId(), ev.getId(), ev.getBattery().getCharge()));
			listeners.remove(ev.getId()).notifyChargingEnded(ev, now);
		}
        else{
			// This happens when the program first starts and a vehicle is placed on a dynamic link but not added to a charger
            // throw new IllegalArgumentException("Attempted to remove vehicle from dynamic charger on link when vehicle was not on link");
        }
	}

	private final Collection<ElectricVehicle> unmodifiablePluggedVehicles = Collections.unmodifiableCollection(vehiclesOnChargingLink.values());

    @Override
    public Collection<ElectricVehicle> getPluggedVehicles() {
        return unmodifiablePluggedVehicles;
    }

    @Override
    public Collection<ElectricVehicle> getQueuedVehicles() {
        return Collections.unmodifiableCollection(Collections.emptyList());
    }

    @Override
    public ChargingStrategy getChargingStrategy() {
        return chargingStrategy;
    }

	public static class FactoryProvider implements Provider<ChargingLogic.Factory> {
		@Inject
		private EventsManager eventsManager;

		private final Function<ChargerSpecification, ChargingStrategy> chargingStrategyCreator;

		public FactoryProvider(Function<ChargerSpecification, ChargingStrategy> chargingStrategyCreator) {
			this.chargingStrategyCreator = chargingStrategyCreator;
		}

		@Override
		public ChargingLogic.Factory get() {
			return charger -> new DynamicChargingLogic(charger,
					chargingStrategyCreator.apply(charger), eventsManager);
		}
	}
    
}
