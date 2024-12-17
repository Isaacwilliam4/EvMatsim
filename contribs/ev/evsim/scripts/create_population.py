import xml.etree.ElementTree as ET
import random
import os
import argparse
import pandas as pd
from util import *

def get_node_coords(network_file):
    # Parse the network XML file
    tree = ET.parse(network_file)
    root = tree.getroot()

    # Create a dictionary to store node coordinates by ID
    node_coords = {}

    # Find all node elements
    for node in root.findall(".//node"):
        node_id = node.get("id")
        x = float(node.get("x"))
        y = float(node.get("y"))

        # Store node coordinates in the dictionary
        node_coords[node_id] = (x, y)

    return node_coords

def create_population_and_plans_xml_counts(node_coords, 
                                        plans_output,
                                        vehicles_output,
                                        num_agents,
                                        counts_input,
                                        alpha,
                                        beta):
    
    plans_output = os.path.abspath(plans_output)
    vehicles_output = os.path.abspath(vehicles_output)

    # Create the root element for the plans
    plans = ET.Element("plans", attrib={'xml:lang': 'de-CH'})  # Root element with lang attribute

    # List of node IDs to randomly select for activities
    node_ids = list(node_coords.keys())
    person_ids = []
    person_count = 1

    if counts_input:
        counts_input = os.path.abspath(counts_input)
        counts_df = pd.read_csv(counts_input, sep='\t')
        counts = counts_df['Flow (Veh/Hour)'].values
    else:
        # if no counts file given, generate bimodal distribution with num_agent samples
        dist1 = np.random.normal(8, 3, num_agents // 2)
        dist2 = np.random.normal(17, 3, num_agents - len(dist1))
        dist = np.concatenate([dist1, dist2])
        counts = np.clip(dist, 0, 24)

    for i, count in enumerate(counts):
        count = int(get_str(count))
        for j in range(int(count*alpha)):
            origin_node_id = random.choice(node_ids)
            dest_node_id = random.choice(node_ids)
            origin_node = node_coords[origin_node_id]
            dest_node = node_coords[dest_node_id]
            person = ET.SubElement(plans, "person", id=str(person_count))
            person_ids.append(person_count)
            person_count += 1
            plan = ET.SubElement(person, "plan", selected="yes")
            start_time = (i+1) % 24
            end_time = (start_time + 8) % 24
            start_time_str = f"0{start_time}:00:00" if start_time < 10 else f"{start_time}:00:00"
            end_time_str = f"0{end_time}:00:00" if end_time < 10 else f"{end_time}:00:00"
            home_activity = ET.SubElement(plan, "act", type="h", x=str(origin_node[0]), y=str(origin_node[1]), end_time=start_time_str)
            leg_to_work = ET.SubElement(plan, "leg", mode="car")
            work_activity = ET.SubElement(plan, "act", type="h", 
                                    x=str(dest_node[0]), y=str(dest_node[1]), start_time=start_time_str, end_time=end_time_str)

    vehicle_tree = create_vehicle_definitions(person_ids, beta)
    save_xml(vehicle_tree, vehicles_output)

    # Convert the ElementTree to a string
    tree = ET.ElementTree(plans)

    # Manually write the header to the output file
    with open(plans_output, "wb") as f:
        # Write the XML declaration and DOCTYPE
        f.write(b'<?xml version="1.0" ?>\n')
        f.write(b'<!DOCTYPE plans SYSTEM "http://www.matsim.org/files/dtd/plans_v4.dtd">\n')

        # Write the tree structure
        tree.write(f)

def main(args):
    node_coords = get_node_coords(os.path.abspath(args.network))

    create_population_and_plans_xml_counts(
                                    node_coords, 
                                    args.plans_output,
                                    args.vehicles_output,
                                    args.num_agents,
                                    args.counts_input,
                                    args.pop_mulitiplier,
                                    args.percent_home_charge)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate population and plans XML files')

    # Define positional arguments
    parser.add_argument('network', type=str, help='Input matsim xml network')
    parser.add_argument('plans_output', type=str, help='Output path of plans network')
    parser.add_argument('vehicles_output', type=str, help='Vehicle file used to create vehicles')
    parser.add_argument('num_agents', type=int, help='The number of agents to generate', default=100)
    parser.add_argument('--counts_input', type=str, help='Counts file to use for creating population, if none \
                        provided then a bimodal distribution with num_agents samples will be generated', default=None)
    parser.add_argument('--pop_mulitiplier', type=float, help='How much to mulitply population by based on the counts file', default=1)
    parser.add_argument('--percent_home_charge', type=float, help='Percentage of population that charges at home', default=1)

    args = parser.parse_args()

    main(args)
