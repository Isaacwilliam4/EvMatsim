import xml.etree.ElementTree as ET
import random
import argparse
import os
import numpy as np

def load_network_xml(network_file):
    # Parse the network XML file
    tree = ET.parse(network_file)
    root = tree.getroot()

    # Create a list to store link IDs
    link_ids = []

    # Find all link elements
    for link in root.findall(".//link"):
        link_id = link.get("id")
        link_ids.append(link_id)

    return link_ids

def create_chargers_xml(num_chargers, link_ids:list, output_file_path, percent_dynamic=0.0):
    # Create the root element for the chargers
    chargers = ET.Element("chargers")

    # Loop to create the specified number of chargers
    num_dynamic = int(num_chargers*percent_dynamic)
    num_static = num_chargers - num_dynamic
    
    link_ids = np.array(link_ids)
    dynamic_chargers = np.random.choice(link_ids, num_dynamic)
    link_ids = np.setdiff1d(link_ids, dynamic_chargers)
    static_chargers = np.random.choice(link_ids, num_static)

    id=0
    i=0

    while i < len(dynamic_chargers):
        charger = ET.SubElement(chargers, "charger", id=str(id), link=dynamic_chargers[i], plug_power="50", plug_count="9999", type="dynamic")
        id += 1
        i += 1
    
    i = 0
    while i < len(static_chargers):
        charger = ET.SubElement(chargers, "charger", id=str(i), link=static_chargers[i], plug_power="100.0", plug_count="5")
        id += 1
        i += 1

    # Convert the ElementTree to a string
    tree = ET.ElementTree(chargers)

    # Manually write the header to the output file
    with open(output_file_path, "wb") as f:
        # Write the XML declaration and DOCTYPE
        f.write(b'<?xml version="1.0" ?>\n')
        f.write(b'<!DOCTYPE chargers SYSTEM "http://matsim.org/files/dtd/chargers_v1.dtd">\n')

        # Write the tree structure
        tree.write(f)

    print(f"{num_chargers} chargers written to {output_file_path}")

def main(args):
    link_ids = load_network_xml(os.path.abspath(args.input_file))

    if args.num_chargers is not None:
        num_chargers = args.num_chargers
    elif args.percent is not None:
        num_links = len(link_ids)
        num_chargers = int(num_links * (args.percent / 100))
    else:
        raise ValueError("Either num_chargers or percent must be specified")

    create_chargers_xml(num_chargers, link_ids, os.path.abspath(args.output_file), args.percent_dynamic)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate chargers XML file.')
    
    # Define positional arguments
    parser.add_argument('input_file', type=str, help='Input MATSim XML network')
    parser.add_argument('output_file', type=str, help='Output path of chargers XML file')
    parser.add_argument('--num_chargers', type=int, help='Number of chargers to generate')
    parser.add_argument('--percent', type=float, help='Percentage of links to place chargers on')
    parser.add_argument('--percent_dynamic', type=float, help='Percentage of chargers that are dynamic\
                        vs static chargers, 1.0 = 100 percent of chargers are dynamic, 0.0 = 100 percent of chargers\
                        are static')

    args = parser.parse_args()

    main(args)
