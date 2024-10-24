import xml.etree.ElementTree as ET
import random
import argparse
import os

parser = argparse.ArgumentParser(description='Generate population and plans XML files')

parser.add_argument('--input', type=str, help='Input matsim xml network', required=True)
parser.add_argument('--output', type=str, help='Output path of plans network', required=True)
parser.add_argument('--numagents', type=int, help='Number of agents to generate', required=True)


args = parser.parse_args()


def load_network_xml(network_file):
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
        home_node_id = random.choice(node_ids)
        work_node_id = random.choice(node_ids)

        home_node = node_coords[home_node_id]
        work_node = node_coords[work_node_id]

        # Define the agent's activities and legs
        home_activity = ET.SubElement(plan, "act", type="h", 
                                      x=str(home_node[0]), y=str(home_node[1]), end_time="08:00:00")
        leg_to_work = ET.SubElement(plan, "leg", mode="car")
        work_activity = ET.SubElement(plan, "act", type="w", 
                                      x=str(work_node[0]), y=str(work_node[1]), start_time="08:30:00", end_time="17:00:00")
        leg_to_home = ET.SubElement(plan, "leg", mode="car")
        home_activity_2 = ET.SubElement(plan, "act", type="h", 
                                        x=str(home_node[0]), y=str(home_node[1]))

    # Convert the ElementTree to a string
    tree = ET.ElementTree(plans)

    # Manually write the header to the output file
    with open(output_file_path, "wb") as f:
        # Write the XML declaration and DOCTYPE
        f.write(b'<?xml version="1.0" ?>\n')
        f.write(b'<!DOCTYPE plans SYSTEM "http://www.matsim.org/files/dtd/plans_v4.dtd">\n')

        # Write the tree structure
        tree.write(f)

node_coords = load_network_xml(os.path.abspath(args.input))
create_population_and_plans_xml(args.numagents, node_coords, os.path.abspath(args.output))