package ch.sbb.matsim.contrib.railsim;

import ch.sbb.matsim.contrib.railsim.config.RailsimConfigGroup;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.network.Link;
import org.matsim.pt.transitSchedule.api.TransitLine;
import org.matsim.pt.transitSchedule.api.TransitRoute;
import org.matsim.vehicles.VehicleType;

import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * Utility class for working with Railsim and its specific attributes.
 *
 * @author Ihab Kaddoura
 * @author rakow
 */
public final class RailsimUtils {

	// link
	public static final String LINK_ATTRIBUTE_GRADE = "railsimGrade";
	public static final String LINK_ATTRIBUTE_RESOURCE_ID = "railsimResourceId";
	public static final String LINK_ATTRIBUTE_CAPACITY = "railsimTrainCapacity";
	public static final String LINK_ATTRIBUTE_MAX_SPEED = "railsimMaxSpeed";
	public static final String LINK_ATTRIBUTE_MINIMUM_TIME = "railsimMinimumTime";
	// vehicle
	public static final String VEHICLE_ATTRIBUTE_ACCELERATION = "railsimAcceleration";
	public static final String VEHICLE_ATTRIBUTE_DECELERATION = "railsimDeceleration";

	private RailsimUtils() {
	}

	// TODO: Setter methods

	/**
	 * Round number to precision commonly used in Railsim.
	 */
	public static double round(double d) {
		return BigDecimal.valueOf(d).setScale(3, RoundingMode.HALF_EVEN).doubleValue();
	}

	/**
	 * @return the train capacity for this link, if no link attribute is provided the default is 1.
	 */
	public static int getTrainCapacity(Link link) {
		Object attr = link.getAttributes().getAttribute(LINK_ATTRIBUTE_CAPACITY);
		return attr != null ? (int) attr : 1;
	}

	/**
	 * @return the minimum time for the switch at the end of the link (toNode); if no link attribute is provided the default is 0.
	 */
	public static double getMinimumTrainHeadwayTime(Link link) {
		Object attr = link.getAttributes().getAttribute(LINK_ATTRIBUTE_MINIMUM_TIME);
		return attr != null ? (double) attr : 0;
	}

	/**
	 * Sets the minimum headway time after a link can be released.
	 */
	public static void setMinimumTrainHeadwayTime(Link link, double time) {
		link.getAttributes().putAttribute(LINK_ATTRIBUTE_MINIMUM_TIME, time);
	}

	/**
	 * @return the default deceleration time or the vehicle-specific value
	 */
	public static double getTrainDeceleration(VehicleType vehicle, RailsimConfigGroup railsimConfigGroup) {
		double deceleration = railsimConfigGroup.decelerationGlobalDefault;
		Object attr = vehicle.getAttributes().getAttribute(VEHICLE_ATTRIBUTE_DECELERATION);
		return attr != null ? (double) attr : deceleration;
	}

	/**
	 * @return the default acceleration time or the vehicle-specific value
	 */
	public static double getTrainAcceleration(VehicleType vehicle, RailsimConfigGroup railsimConfigGroup) {
		double acceleration = railsimConfigGroup.accelerationGlobalDefault;
		Object attr = vehicle.getAttributes().getAttribute(VEHICLE_ATTRIBUTE_ACCELERATION);
		return attr != null ? (double) attr : acceleration;
	}

	/**
	 * Resource id or null if there is none.
	 */
	public static String getResourceId(Link link) {
		return (String) link.getAttributes().getAttribute(LINK_ATTRIBUTE_RESOURCE_ID);
	}

	/**
	 * Whether this link is an entry link applicable for re routing.
	 */
	public static boolean isEntryLink(Link link) {
		return Boolean.TRUE.equals(link.getAttributes().getAttribute("railsimEntry"));
	}


	/**
	 * Exit link used for re routing.
	 */
	public static boolean isExitLink(Link link) {
		return Boolean.TRUE.equals(link.getAttributes().getAttribute("railsimExit"));
	}

	/**
	 * @return the vehicle-specific freespeed or 0 if there is no vehicle-specific freespeed provided in the link attributes
	 */
	public static double getLinkFreespeedForVehicleType(VehicleType type, Link link) {
		Object attribute = link.getAttributes().getAttribute(type.getId().toString());
		if (attribute == null) {
			return 0.;
		} else {
			return (double) attribute;
		}
	}

	/**
	 * @return the line-specific freespeed or 0 if there is no line-specific freespeed provided in the link attributes
	 */
	public static double getLinkFreespeedForTransitLine(Id<TransitLine> line, Link link) {
		Object attribute = link.getAttributes().getAttribute(line.toString());
		if (attribute == null) {
			return 0.;
		} else {
			return (double) attribute;
		}
	}

	/**
	 * @return the line- and route-specific freespeed or 0 if there is no line- and route-specific freespeed provided in the link attributes
	 */
	public static double getLinkFreespeedForTransitLineAndTransitRoute(Id<TransitLine> line, Id<TransitRoute> route, Link link) {
		Object attribute = link.getAttributes().getAttribute(line.toString() + "+++" + route.toString());
		if (attribute == null) {
			return 0.;
		} else {
			return (double) attribute;
		}
	}

}
