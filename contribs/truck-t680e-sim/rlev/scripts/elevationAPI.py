import xml.etree.ElementTree as ET
import csv
import requests
import math
import json
from pyproj import Transformer

def parse_coordinates(x, y):
    """
    Convert from what appears to be a projected coordinate system to WGS84 (lat/lon).
    Using pyproj for accurate conversion similar to Google Maps API.
    """
    # Create a transformer from what seems to be EPSG:3857 (Web Mercator) to EPSG:4326 (WGS84)
    transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    
    # Transform coordinates
    lon, lat = transformer.transform(x, y)
    
    return lon, lat

def get_elevations_batch(locations):
    """Call the elevation API to get elevation data for multiple points in one request."""
    api_endpoint = "https://api.open-elevation.com/api/v1/lookup"
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    # Format locations for the API
    payload = {
        "locations": [
            {"longitude": lon, "latitude": lat} for lon, lat in locations
        ]
    }
    
    try:
        response = requests.post(api_endpoint, headers=headers, data=json.dumps(payload))
        print(f"API Response: {response.text}")
        if response.status_code == 200:
            data = response.json()
            return data["results"]
        else:
            print(f"API Error: {response.status_code}, {response.text}")
            return [{"elevation": 0} for _ in range(len(locations))]
    except Exception as e:
        print(f"Error getting elevations: {e}")
        return [{"elevation": 0} for _ in range(len(locations))]

def process_nodes_and_links(xml_file, output_csv, updated_xml_file, batch_size=100):
    # Parse the XML file
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Extract nodes and prepare for batch processing
    nodes = {}
    node_list = []
    location_list = []
    
    print("Extracting nodes and preparing batch requests...")
    
    for node in root.findall('.//node'):
        node_id = node.get('id')
        x = float(node.get('x'))
        y = float(node.get('y'))
        
        # Convert coordinates to lat/lon
        lon, lat = parse_coordinates(x, y)
        
        # Store basic info
        nodes[node_id] = {
            'x': x,
            'y': y,
            'lon': lon,
            'lat': lat,
            'elevation': None  # Will be populated later
        }
        
        # Add to lists for batch processing
        node_list.append(node_id)
        location_list.append((lat, lon))
    
    # Process elevations in batches
    print(f"Fetching elevations for {len(node_list)} nodes in batches of {batch_size}...")
    
    for i in range(0, len(location_list), batch_size):
        batch_locations = location_list[i:i+batch_size]
        batch_node_ids = node_list[i:i+batch_size]
        
        print(f"Processing batch {i//batch_size + 1}/{math.ceil(len(location_list)/batch_size)}...")
        
        # Get elevations for this batch
        results = get_elevations_batch(batch_locations)
        
        # Assign elevations to nodes
        for j, result in enumerate(results):
            node_id = batch_node_ids[j]
            nodes[node_id]['elevation'] = result['elevation']
            print(f"Node {node_id}: Elevation = {result['elevation']}m")
    
    # Save nodes data to CSV
    with open(output_csv, 'w', newline='') as csvfile:
        fieldnames = ['node_id', 'x', 'y', 'lon', 'lat', 'elevation']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for node_id, data in nodes.items():
            writer.writerow({
                'node_id': node_id,
                'x': data['x'],
                'y': data['y'],
                'lon': data['lon'],
                'lat': data['lat'],
                'elevation': data['elevation']
            })
    
    print(f"Node data saved to {output_csv}")
    
    # Process links
    print("Processing links and calculating slopes...")
    for link in root.findall('.//link'):
        link_id = link.get('id')
        from_node = link.get('from')
        to_node = link.get('to')
        length = float(link.get('length'))
        
        # Get elevations of the nodes
        if from_node in nodes and to_node in nodes:
            from_elevation = nodes[from_node]['elevation']
            to_elevation = nodes[to_node]['elevation']
            
            # Calculate elevation difference (positive = uphill, negative = downhill)
            elevation_diff = to_elevation - from_elevation
            
            # Calculate slope as a decimal (rise/run)
            slope = elevation_diff / length if length > 0 else 0
            
            # Add slope attribute to the link
            attrs = link.find('attributes')
            if attrs is None:
                attrs = ET.SubElement(link, 'attributes')
            
            slope_attr = ET.SubElement(attrs, 'attribute')
            slope_attr.set('name', 'slope')
            slope_attr.set('class', 'java.lang.Double')
            slope_attr.text = str(slope)
            
            print(f"Link {link_id}: from={from_node}, to={to_node}, slope={slope:.6f}")
    
    # Save the updated XML
    tree.write(updated_xml_file)
    print(f"Updated XML saved to {updated_xml_file}")


if __name__ == "__main__":
    input_xml_file = "../../scenario_examples/utahev_scenario_example/utahevnetwork.xml"
    node_csv_file = "node_elevation.csv"
    output_xml_file = "../../scenario_examples/utahev_scenario_example/network_with_slopes.xml"
    
    process_nodes_and_links(input_xml_file, node_csv_file, output_xml_file)