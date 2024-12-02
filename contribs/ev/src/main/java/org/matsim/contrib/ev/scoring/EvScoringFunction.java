package org.matsim.contrib.ev.scoring;

import java.util.Map;

import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.population.Leg;
import org.matsim.api.core.v01.population.Person;
import org.matsim.contrib.ev.fleet.ElectricFleet;
import org.matsim.contrib.ev.fleet.ElectricVehicle;
import org.matsim.core.scoring.functions.ScoringParameters;
import org.matsim.vehicles.Vehicle;


public class EvScoringFunction extends org.matsim.core.scoring.functions.CharyparNagelLegScoring {
	private Person person;
	private final Map<Id<Vehicle>, ? extends ElectricVehicle> eVehicles;

	public EvScoringFunction(Person person, ScoringParameters params, Network network, ElectricFleet fleet)
	{
		super(params, network);
		this.person = person;
		this.eVehicles = fleet.getElectricVehicles();
	}

	@Override
	protected double calcLegScore(double departureTime, double arrivalTime, Leg leg) {

		double tmpScore = super.calcLegScore(departureTime, arrivalTime, leg);
		Id<Vehicle> vehicleId = Id.create(person.getId(), Vehicle.class);
		ElectricVehicle ev = eVehicles.get(vehicleId);

		if (ev != null) {
			double soc = ev.getBattery().getCharge();
			double maxcharge = ev.getBattery().getCapacity();
			double percentCharge = soc / maxcharge;
			tmpScore += 100*percentCharge;
		}

		return tmpScore;
	}

}
