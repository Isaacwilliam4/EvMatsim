package org.matsim.contrib.ev.scoring;

import org.matsim.api.core.v01.population.Activity;
import org.matsim.contrib.ev.EvConfigGroup;
import org.matsim.core.scoring.functions.ActivityTypeOpeningIntervalCalculator;
import org.matsim.core.scoring.functions.ActivityUtilityParameters;
import org.matsim.core.scoring.functions.OpeningIntervalCalculator;
import org.matsim.core.config.Config;
import com.google.inject.Inject;

import org.matsim.core.scoring.functions.ScoringParameters;

public class EvActivityScoringFunction implements org.matsim.core.scoring.SumScoringFunction.ActivityScoring {
	private EvConfigGroup evCfg;

	private static final double INITIAL_SCORE = 0.0;
    private final ScoringParameters params;
    private final OpeningIntervalCalculator openingIntervalCalculator;
	private Activity firstActivity;
    private final Score score = new Score();

    @Inject
    public EvActivityScoringFunction(final ScoringParameters params, EvConfigGroup config) {
        this.evCfg = config;
        this.params = params;
        this.openingIntervalCalculator = new ActivityTypeOpeningIntervalCalculator(params);
    }

    @Override
    public void finish() {
        if (this.firstActivity != null) {
			handleMorningActivity();
		}
    }

    @Override
    public double getScore() {
        return this.score.actCharging_util;
    }

    @Override
    public void handleFirstActivity(Activity act) {
        // Implementation here
    }

	private void handleMorningActivity() {
		assert firstActivity != null;
		// score first activity
		this.score.add(calcActScore(0.0, this.firstActivity.getEndTime().seconds(), firstActivity));
	}

    @Override
    public void handleActivity(Activity act) {
        // Implementation here
        this.score.add(calcActScore(act.getStartTime().seconds(), act.getEndTime().seconds(), act));
    }

    @Override
    public void handleLastActivity(Activity act) {
        // Implementation here
    }

	private Score calcActScore(final double arrivalTime, final double departureTime, final Activity act) {

		ActivityUtilityParameters actParams = this.params.utilParams.get(act.getType());
		if (actParams == null) {
			throw new IllegalArgumentException("acttype \"" + act.getType() + "\" is not known in utility parameters " +
					"(module name=\"scoring\" in the config file).");
		}

		Score tmpScore = new Score();

		if (actParams.isScoreAtAll() && actParams.getType().endsWith("charging interaction")) {
            // Add a disutility for charging
            tmpScore.actCharging_util += (departureTime - arrivalTime)*evCfg.chargingDisutility;
			
		}
		return tmpScore;
	}

    private static final class Score {

		private double actCharging_util = INITIAL_SCORE;

		private void add(Score s) {
			actCharging_util += s.actCharging_util;
		}

	}
}
