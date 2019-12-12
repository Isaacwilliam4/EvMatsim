package org.matsim.contrib.osm.networkReader;

import org.apache.log4j.Logger;
import org.matsim.api.core.v01.Coord;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.api.core.v01.network.Node;
import org.matsim.core.network.NetworkUtils;
import org.matsim.core.utils.geometry.CoordUtils;
import org.matsim.core.utils.geometry.CoordinateTransformation;

import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.concurrent.ConcurrentMap;
import java.util.function.BiPredicate;
import java.util.function.Predicate;
import java.util.stream.Stream;

public class SupersonicOsmNetworkReader {

	private static final Logger log = Logger.getLogger(SupersonicOsmNetworkReader.class);

	private static final Set<String> reverseTags = new HashSet<>(Arrays.asList("-1", "reverse"));
	private static final Set<String> oneWayTags = new HashSet<>(Arrays.asList("yes", "true", "1"));
	private static final Set<String> notOneWayTags = new HashSet<>(Arrays.asList("no", "false", "0"));

	private final ConcurrentMap<String, LinkProperties> linkProperties;
	private final BiPredicate<Coord, Integer> includeLinkAtCoordWithHierarchy;
	private final Predicate<Long> preserveNodeWithId;
	private final AfterLinkCreated afterLinkCreated;
	private final CoordinateTransformation coordinateTransformation;

	private Network network;

	private SupersonicOsmNetworkReader(CoordinateTransformation coordinateTransformation,
									   ConcurrentMap<String, LinkProperties> linkPropertiesMap,
									   BiPredicate<Coord, Integer> includeLinkAtCoordWithHierarchy, Predicate<Long> preserveNodeWithId,
									   AfterLinkCreated afterLinkCreated) {

		this.coordinateTransformation = coordinateTransformation;
		this.includeLinkAtCoordWithHierarchy = includeLinkAtCoordWithHierarchy;
		this.afterLinkCreated = afterLinkCreated;
		this.preserveNodeWithId = preserveNodeWithId;

		this.linkProperties = linkPropertiesMap;
	}

	public Network read(String inputFile) {
		return read(Paths.get(inputFile));
	}

	public Network read(Path inputFile) {

		NodesAndWays nodesAndWays = OsmNetworkParser.parse(inputFile, linkProperties, coordinateTransformation, includeLinkAtCoordWithHierarchy);
		this.network = NetworkUtils.createNetwork();

		log.info("starting convertion \uD83D\uDE80");
		convert(nodesAndWays.getWays(), nodesAndWays.getNodes());

		log.info("finished convertion");
		return network;
	}

	private void convert(Map<Long, ProcessedOsmWay> ways, Map<Long, ProcessedOsmNode> nodes) {

		ways.values().parallelStream()
				.flatMap(way -> this.createWaySegments(nodes, way))
				.flatMap(this::createLinks)
				.forEach(this::addLinkToNetwork);
	}

	private Stream<WaySegment> createWaySegments(Map<Long, ProcessedOsmNode> nodes, ProcessedOsmWay way) {

		List<WaySegment> segments = new ArrayList<>();
		double segmentLength = 0;

		// set up first node for segment
		long fromNodeId = way.getNodeIds().get(0);
		ProcessedOsmNode fromNodeForSegment = nodes.get(fromNodeId);

		for (int i = 1, linkdIdPostfix = 1; i < way.getNodeIds().size(); i++, linkdIdPostfix += 2) {

			// get the from and to nodes for a sub segment of the current way
			ProcessedOsmNode fromOsmNode = nodes.get(way.getNodeIds().get(i - 1));
			ProcessedOsmNode toOsmNode = nodes.get(way.getNodeIds().get(i));

			// add the distance between those nodes to the overal length of segment
			segmentLength += CoordUtils.calcEuclideanDistance(fromOsmNode.getCoord(), toOsmNode.getCoord());

			if (isLoop(fromNodeForSegment, toOsmNode)) {
				// detected a loop. Keep all nodes of the segment
				Collection<WaySegment> loopSegments = handleLoop(nodes, fromNodeForSegment, way, i, linkdIdPostfix);
				segments.addAll(loopSegments);

				// set up next iteration
				linkdIdPostfix += loopSegments.size() * 2;
				segmentLength = 0;
				fromNodeForSegment = toOsmNode;
			}
			// if we have an intersection or the end of the way
			else if (toOsmNode.isIntersection() || toOsmNode.getId() == way.getEndNodeId() || preserveNodeWithId.test(toOsmNode.getId())) {

				// check whether to and fromNode want to have this link
				if (toOsmNode.isWayReferenced(way.getId()) || fromNodeForSegment.isWayReferenced(way.getId())) {
					segments.add(
							new WaySegment(fromNodeForSegment, toOsmNode, segmentLength, way.getLinkProperties(), way.getTags(), way.getId(),
									//if the way id is 1234 we will get a link id like 12340001, this is necessary because we need to generate unique
									// ids. The osm wiki says ways have no more than 2000 nodes which means that i will never be greater 1999.
									// we have to increase the appendix by two for each segment, to leave room for backwards links
									way.getId() * 10000 + linkdIdPostfix)
					);

					//prepare for next segment
					segmentLength = 0;
					fromNodeForSegment = toOsmNode;
				}
			}
		}
		return segments.stream();
	}

	private boolean isLoop(ProcessedOsmNode fromNode, ProcessedOsmNode toNode) {
		return fromNode.getId() == toNode.getId();
	}


	private Collection<WaySegment> handleLoop(Map<Long, ProcessedOsmNode> nodes, ProcessedOsmNode node, ProcessedOsmWay way, int toNodeIndex, int idPostfix) {

		// we need an extra test whether the loop is within the link filter
		if (!includeLinkAtCoordWithHierarchy.test(node.getCoord(), way.getLinkProperties().hierachyLevel))
			return Collections.emptyList();

		// we assume that the whole loop should be included
		List<WaySegment> result = new ArrayList<>();
		ProcessedOsmNode toSegmentNode = node;

		// iterate backwards and keep all elements of the loop. Don't do thinning since this is an edge case
		for (int i = toNodeIndex - 1; i > 0; i--) {

			long fromId = way.getNodeIds().get(i);
			ProcessedOsmNode fromSegmentNode = nodes.get(fromId);

			result.add(new WaySegment(
					fromSegmentNode, toSegmentNode,
					CoordUtils.calcEuclideanDistance(fromSegmentNode.getCoord(), toSegmentNode.getCoord()),
					way.getLinkProperties(),
					way.getTags(),
					way.getId(), way.getId() * 10000 + idPostfix));

			if (fromId == node.getId()) {
				// finish creating segments after creating the last one
				break;
			}
			toSegmentNode = fromSegmentNode;
			idPostfix += 2;
		}
		return result;
	}

	private Stream<Link> createLinks(WaySegment segment) {

		LinkProperties properties = segment.getLinkProperties();
		List<Link> result = new ArrayList<>();

		Node fromNode = createNode(segment.getFromNode().getCoord(), segment.getFromNode().getId());
		Node toNode = createNode(segment.getToNode().getCoord(), segment.getToNode().getId());

		if (!isOnewayReverse(segment.tags)) {
			Link forwardLink = createLink(fromNode, toNode, segment, false);
			result.add(forwardLink);
		}

		if (!isOneway(segment.getTags(), properties)) {
			Link reverseLink = createLink(toNode, fromNode, segment, true);
			result.add(reverseLink);
		}

		return result.stream();
	}

	// same here. Node id-creation seems to be tricky when multi-threading
	private Node createNode(Coord coord, long nodeId) {
		synchronized (Id.class) {
			Id<Node> id = Id.createNodeId(nodeId);
			return network.getFactory().createNode(id, coord);
		}
	}

	private Link createLink(Node fromNode, Node toNode, WaySegment segment, boolean isReverse) {

		String highwayType = segment.getTags().get(OsmTags.HIGHWAY);
		LinkProperties properties = linkProperties.get(highwayType);

		long linkId = isReverse ? segment.getSegmentId() + 1 : segment.getSegmentId();
		Link link;
		// my guess is that somehow the creation of ids causes a race condition when adding links to the network
		synchronized (Id.class) {
			link = network.getFactory().createLink(Id.createLinkId(linkId), fromNode, toNode);
		}
		link.setLength(segment.getLength());
		link.setFreespeed(getFreespeed(segment.getTags(), link.getLength(), properties));
		link.setNumberOfLanes(getNumberOfLanes(segment.getTags(), isReverse, properties));
		link.setCapacity(getLaneCapacity(link.getLength(), properties) * link.getNumberOfLanes());
		link.getAttributes().putAttribute(NetworkUtils.ORIGID, segment.getOriginalWayId());
		link.getAttributes().putAttribute(NetworkUtils.TYPE, highwayType);
		afterLinkCreated.accept(link, segment.getTags(), isReverse);
		return link;
	}

	@SuppressWarnings("BooleanMethodIsAlwaysInverted")
	private boolean isOneway(Map<String, String> tags, LinkProperties properties) {

		if (tags.containsKey(OsmTags.ONEWAY)) {
			String tag = tags.get(OsmTags.ONEWAY);
			if (oneWayTags.contains(tag)) return true;
			if (reverseTags.contains(tag) || notOneWayTags.contains(tag)) return false;
		}

		// no oneway tag
		if (OsmTags.ROUNDABOUT.equals(tags.get(OsmTags.JUNCTION))) return true;

		// just return the default for this type of link
		return properties.oneway;
	}

	private boolean isOnewayReverse(Map<String, String> tags) {

		if (tags.containsKey(OsmTags.ONEWAY)) {
			String tag = tags.get(OsmTags.ONEWAY);
			if (oneWayTags.contains(tag) || notOneWayTags.contains(tag)) return false;
			return reverseTags.contains(tag);
		}
		return false;
	}

	private double getFreespeed(Map<String, String> tags, double linkLength, LinkProperties properties) {
		if (tags.containsKey(OsmTags.MAXSPEED)) {
			double speed = parseSpeedTag(tags.get(OsmTags.MAXSPEED), properties);
			double urbanSpeedFactor = speed <= 51 / 3.6 ? 0.5 : 1.0; // assume for links with max speed lower than 51km/h to be in urban areas. Reduce speed to reflect traffic lights and suc
			return speed * urbanSpeedFactor;
		} else {
			return calculateSpeedIfNoSpeedTag(properties, linkLength);
		}
	}

	private double parseSpeedTag(String tag, LinkProperties properties) {

		try {
			if (tag.endsWith(OsmTags.MPH))
				return Double.parseDouble(tag.replace(OsmTags.MPH, "").trim()) * 1.609344 / 3.6;
			else
				return Double.parseDouble(tag) / 3.6;
		} catch (NumberFormatException e) {
			//System.out.println("Could not parse maxspeed tag: " + tag + " ignoring it");
		}
		return properties.freespeed;
	}

	/*
	 * For links with unknown max speed we assume that links with a length of less than 300m are urban links. For urban
	 * links with a length of 0m the speed is 10km/h. For links with a length of 300m the speed is the default freespeed
	 * property for that highway type. For links with a length between 0 and 300m the speed is interpolated linearly.
	 *
	 * All links longer than 300m the default freesped property is assumed
	 */
	private double calculateSpeedIfNoSpeedTag(LinkProperties properties, double linkLength) {
		if (properties.hierachyLevel > LinkProperties.LEVEL_MOTORWAY && properties.hierachyLevel <= LinkProperties.LEVEL_TERTIARY
				&& linkLength < 300) {
			return ((10 + (properties.freespeed - 10) / 300 * linkLength) / 3.6);
		}
		return properties.freespeed;
	}

	private double getLaneCapacity(double linkLength, LinkProperties properties) {
		double capacityFactor = linkLength < 100 ? 2 : 1;
		return properties.laneCapacity * capacityFactor;
	}

	private double getNumberOfLanes(Map<String, String> tags, boolean isReverse, LinkProperties properties) {

		try {
			if (tags.containsKey(OsmTags.LANES)) {
				String directionKey = isReverse ? OsmTags.LANES_BACKWARD : OsmTags.LANES_FORWARD;
				if (tags.containsKey(directionKey)) {
					double directionLanes = Double.parseDouble(tags.get(directionKey));
					if (directionLanes > 0) return directionLanes;
				}
				// no forward lane tag, so use the regular lanes tag
				double lanes = Double.parseDouble(tags.get(OsmTags.LANES));

				// lanes tag specifies lanes into both directions of a way, so cut it in half if it is not a oneway street
				if (!isOneway(tags, properties)) return lanes / 2;
				return lanes;
			}
		} catch (NumberFormatException e) {
			return properties.lanesPerDirection;
		}
		return properties.lanesPerDirection;
	}

	private synchronized void addLinkToNetwork(Link link) {

		//we have to test for presence
		if (!network.getNodes().containsKey(link.getFromNode().getId())) {
			network.addNode(link.getFromNode());
		}

		if (!network.getNodes().containsKey(link.getToNode().getId())) {
			network.addNode(link.getToNode());
		}

		if (!network.getLinks().containsKey(link.getId())) {
			network.addLink(link);
		} else {
			log.error("Link id: " + link.getId() + " was already present. This should not happen");
			log.error("The link associated with this id: " + link.toString());
			throw new RuntimeException("Link id: " + link.getId() + " was already present!");
		}
	}

	public static Builder builder() {
		return new Builder();
	}

	public static class Builder {

		private ConcurrentMap<String, LinkProperties> linkProperties = LinkProperties.createLinkProperties();
		private BiPredicate<Coord, Integer> includeLinkAtCoordWithHierarchy = (coord, level) -> true;
		private Predicate<Long> preserveNodeWithId = id -> false;
		private AfterLinkCreated afterLinkCreated = (link, tags, isReverse) -> {
		};
		private CoordinateTransformation coordinateTransformation;

		public Builder coordinateTransformation(CoordinateTransformation coordinateTransformation) {
			this.coordinateTransformation = coordinateTransformation;
			return this;
		}

		public Builder includeLinkAtCoordWithHierarchy(BiPredicate<Coord, Integer> predicate) {
			this.includeLinkAtCoordWithHierarchy = predicate;
			return this;
		}

		public Builder preserveNodeWithId(Predicate<Long> predicate) {
			this.preserveNodeWithId = predicate;
			return this;
		}

		public Builder afterLinkCreated(AfterLinkCreated consumer) {
			this.afterLinkCreated = consumer;
			return this;
		}

		public Builder addOverridingLinkProperties(String highwayType, LinkProperties properties) {
			linkProperties.put(highwayType, properties);
			return this;
		}

		public SupersonicOsmNetworkReader build() {

			if (coordinateTransformation == null) {
				throw new IllegalArgumentException("Target coordinate transformation is required parameter!");
			}

			return new SupersonicOsmNetworkReader(
					coordinateTransformation, linkProperties, includeLinkAtCoordWithHierarchy,
					preserveNodeWithId, afterLinkCreated
			);
		}
	}

	private static class WaySegment {
		private final ProcessedOsmNode fromNode;
		private final ProcessedOsmNode toNode;
		private final double length;
		private final LinkProperties linkProperties;
		private final Map<String, String> tags;
		private final long originalWayId;
		private final long segmentId;

		public WaySegment(ProcessedOsmNode fromNode, ProcessedOsmNode toNode, double length, LinkProperties linkProperties, Map<String, String> tags, long originalWayId, long segmentId) {
			this.fromNode = fromNode;
			this.toNode = toNode;
			this.length = length;
			this.linkProperties = linkProperties;
			this.tags = tags;
			this.originalWayId = originalWayId;
			this.segmentId = segmentId;
		}

		public ProcessedOsmNode getFromNode() {
			return fromNode;
		}

		public ProcessedOsmNode getToNode() {
			return toNode;
		}

		public double getLength() {
			return length;
		}

		public LinkProperties getLinkProperties() {
			return linkProperties;
		}

		public Map<String, String> getTags() {
			return tags;
		}

		public long getOriginalWayId() {
			return originalWayId;
		}

		public long getSegmentId() {
			return segmentId;
		}
	}

	@FunctionalInterface
	public interface AfterLinkCreated {

		void accept(Link link, Map<String, String> osmTags, boolean isReverse);
	}
}
