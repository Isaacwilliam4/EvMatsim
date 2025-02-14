import xml.etree.ElementTree as ET
import random
import argparse
import os
import numpy as np
from gymnasium import spaces
from bidict import bidict
from evsim.classes.chargers import * 
from pathlib import Path

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

def create_chargers_xml_gymnasium(charger_xml_path:Path, charger_list:list[Charger], actions:spaces.MultiDiscrete, link_id_mapping:bidict):
    """Given a multi-discrete action space, create a chargers XML file for MATSim.

    Args:
        charger_list (list): contains a list of the charger type names
        action (spaces.MultiDiscrete): the action space with dimenstion (num_edges) where each value corresponds to
        index of the charger list (0 is no charger)
        link_id_mapping (dict): (key:link_id, value:index) bidict mapping edge_id to index
    """
    chargers = ET.Element("chargers")

    for idx, action in enumerate(actions):
        if action == 0:
            continue
        else:
            charger = charger_list[action]
            link_id = link_id_mapping.inv[idx]
            charger = ET.SubElement(chargers, "charger", id=str(idx), link=str(link_id), \
                                    plug_power=str(charger.plug_power), plug_count=str(charger.plug_count), type=charger.type)

    # Convert the ElementTree to a string
    tree = ET.ElementTree(chargers)

    # Manually write the header to the output file
    with open(charger_xml_path, "wb") as f:
        # Write the XML declaration and DOCTYPE
        f.write(b'<?xml version="1.0" ?>\n')
        f.write(b'<!DOCTYPE chargers SYSTEM "http://matsim.org/files/dtd/chargers_v1.dtd">\n')

        # Write the tree structure
        tree.write(f)

def create_chargers_xml(link_ids:list, output_file_path, percent_dynamic=0.0):
    num_chargers = len(link_ids)
    # Create the root element for the chargers
    chargers = ET.Element("chargers")

    # Loop to create the specified number of chargers
    num_dynamic = int(num_chargers*percent_dynamic)
    num_static = num_chargers - num_dynamic
    
    link_ids = np.array(link_ids)
    dynamic_chargers = np.random.choice(link_ids, num_dynamic, replace=False)
    link_ids = np.setdiff1d(link_ids, dynamic_chargers)
    static_chargers = np.random.choice(link_ids, num_static, replace=False)

    id=0
    i=0

    while i < len(dynamic_chargers):
        charger = ET.SubElement(chargers, "charger", id=str(id), link=str(dynamic_chargers[i]), plug_power="70", plug_count="9999", type="dynamic")
        id += 1
        i += 1
    
    i = 0
    while i < len(static_chargers):
        charger = ET.SubElement(chargers, "charger", id=str(id), link=str(static_chargers[i]), plug_power="100.0", plug_count="1")
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

def main(args):
    link_ids = load_network_xml(os.path.abspath(args.input_file))

    if args.num_chargers is not None:
        num_chargers = args.num_chargers
    elif args.percent is not None:
        num_links = len(link_ids)
        num_chargers = int(num_links * (args.percent / 100))
    else:
        raise ValueError("Either num_chargers or percent must be specified")

    link_ids = np.random.choice(link_ids, num_chargers)
    create_chargers_xml(link_ids, os.path.abspath(args.output_file), args.percent_dynamic)

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
