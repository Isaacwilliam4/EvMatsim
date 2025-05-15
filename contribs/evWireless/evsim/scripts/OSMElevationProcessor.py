import xml.etree.ElementTree as ET
import requests
import math
import time
from typing import Dict, List, Tuple

#run with python script.py nods/links.xml lon/lat.osm output.xml

class ElevationProcessor:
    def __init__(self, xml_file: str, osm_file: str):
        """Initialize with paths to XML and OSM files."""
        self.xml_file = xml_file
        self.osm_file = osm_file
        self.xml_tree = ET.parse(xml_file)
        self.xml_root = self.xml_tree.getroot()
        
        # For OSM file, we may need to add a root element if it doesn't have one
        with open(osm_file, 'r') as f:
            osm_content = f.read()
            if not osm_content.strip().startswith('<?xml') and not osm_content.strip().startswith('<osm'):
                osm_content = f'<osm>\n{osm_content}\n</osm>'
            
        self.osm_root = ET.fromstring(osm_content)
        
        self.node_coords = {}  # Will store node id -> lat, lon coordinates
        self.links = []  # Will store (from_node, to_node, link_element)
        self.earth_radius = 6371000  # Earth radius in meters
        
    def parse_xml_links(self):
        """Extract links from the XML file."""
        print("Parsing links from XML file...")
        links_found = 0
        all_node_ids = set()
        
        # Find all links in the XML file
        for link in self.xml_root.findall(".//link"):
            from_node = link.get("from")
            to_node = link.get("to")
            
            if from_node and to_node:
                self.links.append((from_node, to_node, link))
                all_node_ids.add(from_node)
                all_node_ids.add(to_node)
                links_found += 1
        
        print(f"Found {links_found} links referencing {len(all_node_ids)} unique nodes in the XML file.")
        return all_node_ids
    
    def extract_osm_nodes(self, needed_node_ids):
        """Extract node data from the OSM file for the node IDs found in links."""
        print("Extracting node coordinates from OSM file...")
        nodes_matched = 0
        
        # Process OSM nodes (which include lat/lon data)
        for node in self.osm_root.findall(".//node"):
            node_id = node.get("id")
            if node_id in needed_node_ids:
                lat = float(node.get("lat", "0"))
                lon = float(node.get("lon", "0"))
                self.node_coords[node_id] = {"lat": lat, "lon": lon}
                nodes_matched += 1
        
        print(f"Matched {nodes_matched} nodes with coordinates from the OSM file.")
        missing_nodes = len(needed_node_ids) - nodes_matched
        if missing_nodes > 0:
            print(f"Warning: {missing_nodes} nodes from the XML file were not found in the OSM file.")
    
    def fetch_elevations(self):
        """Fetch elevation data for all nodes using Open Elevation API."""
        print("Fetching elevations from Open Elevation API...")
        batch_size = 100  # Process in batches to avoid overwhelming the API
        node_ids = list(self.node_coords.keys())
        nodes_processed = 0
        
        for i in range(0, len(node_ids), batch_size):
            batch_ids = node_ids[i:i+batch_size]
            locations = []
            
            for node_id in batch_ids:
                if node_id in self.node_coords:
                    locations.append({
                        "latitude": self.node_coords[node_id]["lat"],
                        "longitude": self.node_coords[node_id]["lon"]
                    })
            
            if locations:
                try:
                    response = requests.post(
                        "https://api.open-elevation.com/api/v1/lookup",
                        json={"locations": locations}
                    )
                    
                    if response.status_code == 200:
                        results = response.json()["results"]
                        for j, node_id in enumerate(batch_ids):
                            if j < len(results):
                                self.node_coords[node_id]["elevation"] = results[j]["elevation"]
                                nodes_processed += 1
                    else:
                        print(f"Error from API: {response.status_code} - {response.text}")
                    
                    # Be nice to the API with a delay
                    time.sleep(1)
                except Exception as e:
                    print(f"Error fetching elevations: {e}")
                    
            # Print progress
            progress = min(100, int((nodes_processed / len(node_ids)) * 100))
            print(f"Elevation data: {progress}% complete ({nodes_processed}/{len(node_ids)} nodes)")
        
        # Count nodes with elevation data
        nodes_with_elevation = sum(1 for data in self.node_coords.values() if "elevation" in data)
        print(f"Retrieved elevations for {nodes_with_elevation} out of {len(self.node_coords)} nodes.")
        
    def calculate_distance(self, node1_id: str, node2_id: str) -> float:
        """Calculate the distance between two nodes using the Haversine formula."""
        if node1_id not in self.node_coords or node2_id not in self.node_coords:
            return 0.0
        
        lat1 = math.radians(self.node_coords[node1_id]["lat"])
        lon1 = math.radians(self.node_coords[node1_id]["lon"])
        lat2 = math.radians(self.node_coords[node2_id]["lat"])
        lon2 = math.radians(self.node_coords[node2_id]["lon"])
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = self.earth_radius * c  # Distance in meters
        
        return distance
    
    def calculate_slopes(self):
        """Calculate slopes between connected nodes."""
        print("Calculating slopes between connected nodes...")
        slopes_calculated = 0
        missing_data = 0
        
        for from_node, to_node, link in self.links:
            if (from_node in self.node_coords and to_node in self.node_coords and
                "elevation" in self.node_coords[from_node] and 
                "elevation" in self.node_coords[to_node]):
                
                elev1 = self.node_coords[from_node]["elevation"]
                elev2 = self.node_coords[to_node]["elevation"]
                
                # Calculate horizontal distance
                distance = self.calculate_distance(from_node, to_node)
                
                # If we have a length attribute in the link, use that instead
                link_length = link.get("length")
                if link_length:
                    try:
                        distance = float(link_length)
                    except ValueError:
                        pass  # Keep the calculated distance if conversion fails
                
                if distance > 0:
                    # Calculate elevation difference
                    elev_diff = elev2 - elev1
                    
                    # Calculate slope (as a ratio)
                    slope = elev_diff / distance
                    
                    # Calculate slope as a percentage
                    slope_percent = slope# * 100 # Convert to percentage if needed
                    
                    # Add slope directly as an attribute to the link element
                    link.set("slopes", f"{slope_percent:.6f}")
                    
                    slopes_calculated += 1
            else:
                missing_data += 1
        
        print(f"Calculated {slopes_calculated} slopes.")
        if missing_data > 0:
            print(f"Warning: Could not calculate slopes for {missing_data} links due to missing coordinate or elevation data.")
    
    def save_modified_xml(self, output_file: str):
        """Save the modified XML with slope information."""
        print(f"Saving modified XML to {output_file}...")
        self.xml_tree.write(output_file, encoding="utf-8", xml_declaration=True)
        print("Save complete.")
    
    def process(self, output_file: str):
        """Run the complete processing pipeline."""
        node_ids = self.parse_xml_links()
        self.extract_osm_nodes(node_ids)
        self.fetch_elevations()
        self.calculate_slopes()
        self.save_modified_xml(output_file)
        print("Processing complete!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process XML and OSM data to calculate slopes between nodes.")
    parser.add_argument("xml_file", help="Input XML file with links")
    parser.add_argument("osm_file", help="Input OSM file with node coordinates")
    parser.add_argument("output_file", help="Output XML file with added slope data")
    
    args = parser.parse_args()
    
    processor = ElevationProcessor(args.xml_file, args.osm_file)
    processor.process(args.output_file)