import json
from tqdm import tqdm


def create_sensor_osm(flows_path: str, locations_path: str):
    # read in flows and locations and store in memory as python dict
    with open(flows_path, 'r') as sensor_flows:
        flows = json.load(sensor_flows)
    
    with open(locations_path, 'r') as sensor_locations:
        locations = json.load(sensor_locations)

    josm = {
        "version": 0.6,
        "generator": "Custom",
        "elements": []
    }
    
    # Assign unique negative IDs for new nodes
    node_id = -1
    
    # Convert each sensor into a JOSM node
    for sensor_id, (lat, lon) in tqdm(locations.items()):
        node = {
            "type": "node",
            "id": node_id,
            "lat": lat,
            "lon": lon,
            "tags": {
                "sensor_id": sensor_id  # Store sensor ID as tag
            }
        }
    
        # Add flow data for each hour as a tag
        if sensor_id in flows:
            for hour, flow in enumerate(flows[sensor_id]):
                node["tags"][f"flow_{hour:02d}"] = str(flow)  # Store flow values as tags
    
        josm["elements"].append(node)
        node_id -= 1  # Ensure unique IDs

    # Save to JSON file
    with open("osm_sensor_flow_map.json", "w") as f:
        json.dump(josm, f, indent=4)

    

if __name__ == "__main__":
    create_sensor_osm('sensor_flows.json', 'sensor_locations.json')
