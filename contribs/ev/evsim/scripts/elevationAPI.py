import xml.etree.ElementTree as ET
import requests
import pyproj
import math
import csv
import time


# For coordinate transformation
def transform_coordinates(x, y, from_epsg=3857, to_epsg=4326):
    """Transform coordinates from one projection to another"""
    transformer = pyproj.Transformer.from_crs(from_epsg, to_epsg, always_xy=True)
    lon, lat = transformer.transform(x, y)
    return lat, lon  # Return as lat, lon for API convenience

# Parse the XML
file_path = "../../scenario_examples/utahev_scenario_example/utahevnetwork.xml" # Change to your file path
tree = ET.parse(file_path)
root = tree.getroot()

# Extract coordinates from nodes
node_coordinates = {}
for node in root.findall(".//node"):
    node_id = node.get('id')
    x = float(node.get('x'))
    y = float(node.get('y'))
    
    # Transform from Web Mercator to WGS84 (lat/lon)
    lat, lon = transform_coordinates(x, y)
    lat = round(lat, 1) #rounding to 1 decimal place for API
    lon = round(lon, 1)
    
    node_coordinates[node_id] = {
        'lat': lat,
        'lon': lon
    }

print(f"Extracted {len(node_coordinates)} nodes with coordinates")

# Batch process for elevation data
batch_size = 1  # Adjust as needed. 100 is max.
all_nodes = list(node_coordinates.items())
results = {}

for i in range(0, len(all_nodes), batch_size):
    batch = all_nodes[i:i+batch_size]
    locations_param = "|".join([f"{data['lat']},{data['lon']}" for _, data in batch])
    print(locations_param)  # Debugging line to check the locations parameter
    
    try:
        # response = requests.get(f"https://api.opentopodata.org/v1/srtm30m?locations={locations_param}")
        response = requests.get(f"https://epqs.nationalmap.gov/v1/json?x=-104.9847034&y=39.7391536&units=meters")
        print(response.json())  # Debugging line to check the response
        
        if response.status_code == 200: #200 request was successful. 400 = bad request, 401 = unauthorized, 403 = forbidden, 404 = not found, 500 = server error
            api_results = response.json()['results']
            
            for j, (node_id, _) in enumerate(batch):
                elevation = api_results[j]['elevation']
                results[node_id] = elevation
                print(f"Node {node_id}: Elevation {elevation} m")
                
            print(f"Processed batch {i//batch_size + 1}/{math.ceil(len(all_nodes)/batch_size)}")
        else:
            print(f"Error in batch {i//batch_size + 1}: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Exception in batch {i//batch_size + 1}: {str(e)}")


    time.sleep(1)  # Rate limiting to avoid hitting API limits



with open('node_elevations.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Node ID', 'X', 'Y', 'Latitude', 'Longitude', 'Elevation (m)'])
    
    for node_id, coords in node_coordinates.items():
        elevation = results.get(node_id, "N/A")
        x = float(root.find(f".//node[@id='{node_id}']").get('x'))
        y = float(root.find(f".//node[@id='{node_id}']").get('y'))
        
        writer.writerow([
            node_id, 
            x, 
            y, 
            coords['lat'], 
            coords['lon'], 
            elevation
        ])

print("Elevation data saved to node_elevations.csv")