import xml.etree.ElementTree as ET
import random
import argparse
import os

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

def create_chargers_xml(num_chargers, link_ids, output_file_path):
    # Create the root element for the chargers
    chargers = ET.Element("chargers")

    # Loop to create the specified number of chargers
    for i in range(1, num_chargers + 1):
        link_id = random.choice(link_ids)
        if random.random() < .5:
            charger = ET.SubElement(chargers, "charger", id=str(i), link=link_id, plug_power="100.0", plug_count="5")
        else:
            charger = ET.SubElement(chargers, "charger", id=str(i), link=link_id, plug_power="100.0", plug_count="5", type="dynamic")

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

def main(input_file, output_file, num_chargers=None, percent=None):
    link_ids = load_network_xml(os.path.abspath(input_file))

    if num_chargers is not None:
        num_chargers = num_chargers
    elif percent is not None:
        num_links = len(link_ids)
        num_chargers = int(num_links * (percent / 100))
    else:
        raise ValueError("Either num_chargers or percent must be specified")

    create_chargers_xml(num_chargers, link_ids, os.path.abspath(output_file))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate chargers XML file.')
    
    # Define positional arguments
    parser.add_argument('input', type=str, help='Input MATSim XML network')
    parser.add_argument('output', type=str, help='Output path of chargers XML file')
    parser.add_argument('--numchargers', type=int, help='Number of chargers to generate')
    parser.add_argument('--percent', type=int, help='Percentage of links to place chargers on')

    args = parser.parse_args()

    main(args.input, args.output, args.numchargers, args.percent)
