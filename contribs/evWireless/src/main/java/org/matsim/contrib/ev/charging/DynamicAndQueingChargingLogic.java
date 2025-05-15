package org.matsim.contrib.ev.charging;

import org.matsim.contrib.ev.fleet.ElectricVehicle;
import org.matsim.contrib.ev.infrastructure.ChargerSpecification;
import org.matsim.core.api.experimental.events.EventsManager;
import java.util.*;

public class DynamicAndQueingChargingLogic implements ChargingLogic {
    private final ChargingWithQueueingLogic chargingWithQueueingLogic;
    private final DynamicChargingLogic dynamicChargingLogic;
    protected final ChargerSpecification charger;
    private final ChargingStrategy chargingStrategy;
    private final EventsManager eventsManager;
    private boolean isDynamicCharger;


    public DynamicAndQueingChargingLogic(ChargerSpecification charger, ChargingStrategy chargingStrategy, EventsManager eventsManager) {
            this.chargingStrategy = Objects.requireNonNull(chargingStrategy);
            this.charger = Objects.requireNonNull(charger);
            this.eventsManager = Objects.requireNonNull(eventsManager);
            this.chargingWithQueueingLogic = new ChargingWithQueueingLogic(charger, chargingStrategy, eventsManager);
            this.dynamicChargingLogic = new DynamicChargingLogic(charger, chargingStrategy, eventsManager);
            this.isDynamicCharger = this.charger.getChargerType().equals("dynamic");
    }


    @Override
    public void addVehicle(ElectricVehicle ev, double now) {
        if (this.isDynamicCharger){
            this.dynamicChargingLogic.addVehicle(ev, now);
        }
        else{
            this.chargingWithQueueingLogic.addVehicle(ev, now);
        }
    }


    @Override
    public void addVehicle(ElectricVehicle ev, ChargingListener chargingListener, double now) {
        if (this.isDynamicCharger){
            this.dynamicChargingLogic.addVehicle(ev, chargingListener, now);
        }
        else{
            this.chargingWithQueueingLogic.addVehicle(ev, chargingListener, now);
        }
    }


    @Override
    public void removeVehicle(ElectricVehicle ev, double now) {
        if (this.isDynamicCharger){
            this.dynamicChargingLogic.removeVehicle(ev, now);
        }
        else{
            this.chargingWithQueueingLogic.removeVehicle(ev, now);
        }
    }


    @Override
    public void chargeVehicles(double chargePeriod, double now) {
        if (this.isDynamicCharger){
            this.dynamicChargingLogic.chargeVehicles(chargePeriod, now);
        }
        else{
            this.chargingWithQueueingLogic.chargeVehicles(chargePeriod, now);
        }
    }


    @Override
    public Collection<ElectricVehicle> getPluggedVehicles() {
        if (this.isDynamicCharger){
            return this.dynamicChargingLogic.getPluggedVehicles();
        }
        else{
            return this.chargingWithQueueingLogic.getPluggedVehicles();
        }
    }


    @Override
    public Collection<ElectricVehicle> getQueuedVehicles() {
        if (this.isDynamicCharger){
            return this.dynamicChargingLogic.getQueuedVehicles();
        }
        else{
            return this.chargingWithQueueingLogic.getQueuedVehicles();
        }
    }


    @Override
    public ChargingStrategy getChargingStrategy() {
        return chargingStrategy;
    }

}
