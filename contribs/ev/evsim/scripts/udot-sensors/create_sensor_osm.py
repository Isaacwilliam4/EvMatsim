import json
import xml.etree.ElementTree as ET
import xml.dom.minidom


def create_sensor_osm(flows_path: str, locations_path: str):
    # read in flows and locations and store in memory as python dict
    with open(flows_path, "r") as sensor_flows:
        flows = json.load(sensor_flows)

    with open(locations_path, "r") as sensor_locations:
        locations = json.load(sensor_locations)

    # Create OSM XML root
    osm_root = ET.Element("osm", version="0.6", generator="CustomScript")

    # Assign unique negative IDs to each node
    node_id = -1

    # Convert each sensor into an OSM node
    for sensor_id, (lat, lon) in locations.items():
        node = ET.SubElement(
            osm_root,
            "node",
            id=str(node_id),
            lat=str(lat),
            lon=str(lon),
            visible="true",
        )

        # Add sensor ID as a tag
        ET.SubElement(node, "tag", k="sensor_id", v=sensor_id)

        # Add flow data for each hour as a tag
        if sensor_id in flows:
            for hour, flow in enumerate(flows[sensor_id]):
                ET.SubElement(
                    node, "tag", k=f"flow_{hour:02d}", v=str(flow)
                )  # Store flow as a string

        node_id -= 1  # Ensure unique negative IDs

    # Convert to pretty-printed XML
    xml_string = ET.tostring(osm_root, encoding="utf-8")
    pretty_xml = xml.dom.minidom.parseString(xml_string).toprettyxml(indent="  ")

    # Save to .osm file
    with open("sensor_flow_map.osm", "w", encoding="utf-8") as f:
        f.write(pretty_xml)


if __name__ == "__main__":
    create_sensor_osm("sensor_flows.json", "sensor_locations.json")
