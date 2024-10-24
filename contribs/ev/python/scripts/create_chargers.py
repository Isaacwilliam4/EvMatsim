import xml.etree.ElementTree as ET
import random
import argparse
import os

parser = argparse.ArgumentParser(description='Generate population and plans XML files')

parser.add_argument('--input', type=str, help='Input matsim xml network', required=True)
parser.add_argument('--output', type=str, help='Output path of chargers xml file', required=True)
parser.add_argument('--numchargers', type=int, help='Number of chargers to generate')
parser.add_argument('--percent', type=int, help='Percentage of links to place chargers on')



args = parser.parse_args()

if args.numchargers is None and args.percent is None:
    raise ValueError("Either --numchargers or --percent must be specified")


def load_network_xml(network_file):
    # Parse the network XML file
    tree = ET.parse(network_file)
    root = tree.getroot()

    # Create a dictionary to store node coordinates by ID
    link_ids = []

    # Find all node elements
    for link in root.findall(".//link"):
        link_id = link.get("id")
        link_ids.append(link_id)


    return link_ids



def create_chargers_xml(num_chargers, link_ids, output_file_path):
    # Create the root element for the plans
    chargers = ET.Element("chargers")

    # Loop over the number of agents
    for i in range(1, num_chargers + 1):
        link_id = random.choice(link_ids)
        charger = ET.SubElement(chargers, "charger", id=str(i), link=link_id, plug_power="100.0", plug_count="5")

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

link_ids = load_network_xml(os.path.abspath(args.input))

if args.numchargers is not None:
    numchargers = args.numchargers
else:
    num_links = len(link_ids)
    numchargers = int(num_links * (args.percent / 100))
create_chargers_xml(numchargers, link_ids, os.path.abspath(args.output))