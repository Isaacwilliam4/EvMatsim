import xml.etree.ElementTree as ET
import random
import os
import argparse

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

def create_population_and_plans_xml(num_agents, node_coords, output_file_path):
    # Create the root element for the plans
    plans = ET.Element("plans", attrib={'xml:lang': 'de-CH'})  # Root element with lang attribute

    # List of node IDs to randomly select for activities
    node_ids = list(node_coords.keys())

    # Loop over the number of agents
    for i in range(1, num_agents + 1):
        # Create a person element
        person = ET.SubElement(plans, "person", id=str(i))

        # Create a plan for the person
        plan = ET.SubElement(person, "plan", selected="yes")

        # Randomly choose home and work nodes
        origin_node_id = random.choice(node_ids)
        dest_node_id = random.choice(node_ids)

        origin_node = node_coords[origin_node_id]
        dest_node = node_coords[dest_node_id]

        # Define the agent's activities and legs
        home_activity = ET.SubElement(plan, "act", type="h", 
                                      x=str(origin_node[0]), y=str(origin_node[1]), end_time="08:00:00")
        leg_to_work = ET.SubElement(plan, "leg", mode="car")
        work_activity = ET.SubElement(plan, "act", type="w", 
                                      x=str(dest_node[0]), y=str(dest_node[1]), start_time="08:00:00", end_time="17:00:00")
        leg_to_home = ET.SubElement(plan, "leg", mode="car")
        return_home_act = ET.SubElement(plan, "act", type="h", 
                                        x=str(origin_node[0]), y=str(origin_node[1]))

    # Convert the ElementTree to a string
    tree = ET.ElementTree(plans)

    # Manually write the header to the output file
    with open(output_file_path, "wb") as f:
        # Write the XML declaration and DOCTYPE
        f.write(b'<?xml version="1.0" ?>\n')
        f.write(b'<!DOCTYPE plans SYSTEM "http://www.matsim.org/files/dtd/plans_v4.dtd">\n')

        # Write the tree structure
        tree.write(f)

def main(input_file, output_file, num_agents):
    node_coords = get_node_coords(os.path.abspath(input_file))
    create_population_and_plans_xml(num_agents, node_coords, os.path.abspath(output_file))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate population and plans XML files')

    # Define positional arguments
    parser.add_argument('input', type=str, help='Input matsim xml network')
    parser.add_argument('output', type=str, help='Output path of plans network')
    parser.add_argument('numagents', type=int, help='Number of agents to generate')

    args = parser.parse_args()

    main(args.input, args.output, args.numagents)
