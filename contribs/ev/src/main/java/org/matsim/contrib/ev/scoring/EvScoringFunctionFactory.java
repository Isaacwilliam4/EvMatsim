package org.matsim.contrib.ev.scoring;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.population.Person;
import org.matsim.contrib.ev.EvConfigGroup;
import org.matsim.contrib.ev.fleet.ElectricFleet;
import org.matsim.core.scoring.ScoringFunction;
import org.matsim.core.scoring.ScoringFunctionFactory;
import org.matsim.core.scoring.SumScoringFunction;
import org.matsim.core.scoring.functions.CharyparNagelActivityScoring;
import org.matsim.core.scoring.functions.CharyparNagelAgentStuckScoring;
// import org.matsim.core.scoring.functions.CharyparNagelLegScoring;
import org.matsim.core.scoring.functions.ScoringParametersForPerson;
import org.matsim.core.scoring.functions.SubpopulationScoringParameters;

import jakarta.inject.Inject;

public class EvScoringFunctionFactory implements ScoringFunctionFactory {

	private final Scenario scenario;
	private final ScoringParametersForPerson params;
	private final ElectricFleet evFleet;
	private final EvConfigGroup evCfg;
	@Inject
	EvScoringFunctionFactory( final Scenario sc, final ElectricFleet electricFleet, final EvConfigGroup evCfg) {
		this.scenario = sc;
		this.params = new SubpopulationScoringParameters( sc );
		this.evFleet = electricFleet;
		this.evCfg = evCfg;
	}


	@Override
	public ScoringFunction createNewScoringFunction(Person person) {
		SumScoringFunction scoringFunctionSum = new SumScoringFunction();
	    //this is the main difference, since we need a special scoring for carsharing legs

		scoringFunctionSum.addScoringFunction(
	    new EvLegScoringFunction(person, params.getScoringParameters(person), this.scenario.getNetwork(), this.evFleet, this.evCfg));
		// scoringFunctionSum.addScoringFunction(
		// 		new CharyparNagelLegScoring(
		// 				params.getScoringParameters( person ),
		// 				this.scenario.getNetwork(),
		// 				this.scenario.getConfig().transit().getTransitModes())
		// 	    );
		//the remaining scoring functions can be changed and adapted to the needs of the user
		scoringFunctionSum.addScoringFunction(
				new CharyparNagelActivityScoring(
						params.getScoringParameters(
								person ) ) );
		scoringFunctionSum.addScoringFunction(
			new EvActivityScoringFunction(
					params.getScoringParameters(
							person ), evCfg ) );
		scoringFunctionSum.addScoringFunction(
				new CharyparNagelAgentStuckScoring(
						params.getScoringParameters(
								person ) ) );
	    return scoringFunctionSum;
	  }
}
