import xml.etree.ElementTree as ET
import random
import argparse
import os
import numpy as np

parser = argparse.ArgumentParser(description='Generate population and plans XML files')

parser.add_argument('--input', type=str, help='Input matsim xml network', required=True)
parser.add_argument('--inputchrg', type=str, help='Input of the charger.xml file', required=True)
parser.add_argument('--output', type=str, help='Output path of plans network', required=True)
parser.add_argument('--numagents', type=int, help='Number of agents to generate', required=True)

args = parser.parse_args()

def decimal_to_time(decimal_hours):
    # Get the hours and minutes from the decimal
    hours = int(decimal_hours)
    minutes = int((decimal_hours - hours) * 60)
    
    # Format the time as HH:MM:SS
    time_str = f"{hours:02}:{minutes:02}:00"
    return time_str

def load_network_xml(network_file):
    # Parse the network XML file
    tree = ET.parse(network_file)
    root = tree.getroot()

    # Create dictionaries to store node coordinates and link-node mappings
    node_coords = {}
    link_to_node = {}

    # Find all node elements
    for node in root.findall(".//node"):
        node_id = node.get("id")
        x = float(node.get("x"))
        y = float(node.get("y"))

        # Store node coordinates in the dictionary
        node_coords[node_id] = (x, y)

    # Find all link elements and map each link to its 'to' node
    for link in root.findall(".//link"):
        link_id = link.get("id")
        to_node_id = link.get("to")

        # Store the link-to-node mapping
        link_to_node[link_id] = to_node_id

    return node_coords, link_to_node

def load_chargers_xml(chargers_file):
    # Parse the chargers XML file
    tree = ET.parse(chargers_file)
    root = tree.getroot()

    # Create a list to store link IDs where chargers are located
    charger_link_ids = []

    # Find all individual charger elements
    for charger in root.findall(".//charger"):
        # Get the link attribute from each charger
        link_id = charger.get("link")
        if link_id:
            charger_link_ids.append(link_id)

    return charger_link_ids

def create_population_and_plans_xml(num_agents, node_coords, link_to_node, charger_link_ids, output_file_path):
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
        # Add the charging activity with x and y coordinates
        charging_activity = ET.SubElement(plan, "act", type="car charging interaction", 
                                            link=charger_link_id, 
                                            x=str(charger_coords[0]), 
                                            y=str(charger_coords[1]), 
                                            end_time="20:30:00")
        leg_to_home = ET.SubElement(plan, "leg", mode="car")
        home_activity_2 = ET.SubElement(plan, "act", type="h", 
                                            x=str(home_node[0]), y=str(home_node[1]))

        # Optionally add a charging stop
        if random.random() < 0.5:  # 50% chance the agent needs to charge
            # Select a random charger link ID
            charger_link_id = random.choice(charger_link_ids)

            # Get the corresponding node ID for this charger link
            charger_node_id = link_to_node.get(charger_link_id)

            if charger_node_id:
                # Get the coordinates of the charging node
                charger_coords = node_coords.get(charger_node_id)

                if charger_coords:
                    # Add the leg to the charging station
                    leg_to_charger = ET.SubElement(plan, "leg", mode="car")

                    # Add the charging activity with x and y coordinates
                    charging_activity = ET.SubElement(plan, "act", type="car charging interaction", 
                                                      link=charger_link_id, 
                                                      x=str(charger_coords[0]), 
                                                      y=str(charger_coords[1]), 
                                                      end_time="20:30:00")

                    # Add the leg from the charging station to home
                    leg_to_home = ET.SubElement(plan, "leg", mode="car")
                    home_activity_2 = ET.SubElement(plan, "act", type="h", 
                                                    x=str(home_node[0]), y=str(home_node[1]))
        else:
            # No charging stop, go directly home
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

# Load the data from the network and chargers files
node_coords, link_to_node = load_network_xml(os.path.abspath(args.input))
charger_link_ids = load_chargers_xml(os.path.abspath(args.inputchrg))

# Generate the population and plans XML file
create_population_and_plans_xml(args.numagents, node_coords, link_to_node, charger_link_ids, os.path.abspath(args.output))
