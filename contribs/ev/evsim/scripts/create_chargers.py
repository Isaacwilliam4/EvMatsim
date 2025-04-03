import xml.etree.ElementTree as ET
import argparse
import os
import numpy as np
from gymnasium import spaces
from bidict import bidict
from evsim.classes.chargers import Charger
from pathlib import Path


def load_network_xml(network_file):
    """
    Parse the MATSim network XML file and extract link IDs.

    Args:
        network_file (str): Path to the MATSim network XML file.

    Returns:
        list: A list of link IDs extracted from the network file.
    """
    tree = ET.parse(network_file)
    root = tree.getroot()
    link_ids = [link.get("id") for link in root.findall(".//link")]
    return link_ids


def create_chargers_xml_gymnasium(
    charger_xml_path: Path,
    charger_list: list[Charger],
    actions: spaces.MultiDiscrete,
    link_id_mapping: bidict,
):
    """
    Create a chargers XML file for MATSim using a multi-discrete action space.

    Args:
        charger_xml_path (Path): Path to save the chargers XML file.
        charger_list (list): List of charger type objects.
        actions (spaces.MultiDiscrete): Action space with dimension (num_edges),
            where each value corresponds to the index of the charger list
            (0 is no charger).
        link_id_mapping (bidict): Mapping of link IDs to indices.
    """
    chargers = ET.Element("chargers")

    for idx, action in enumerate(actions):
        if action == 0:
            continue
        charger = charger_list[action]
        link_id = link_id_mapping.inv[idx]
        ET.SubElement(
            chargers,
            "charger",
            id=str(idx),
            link=str(link_id),
            plug_power=str(charger.plug_power),
            plug_count=str(charger.plug_count),
            type=charger.type,
        )

    tree = ET.ElementTree(chargers)
    with open(charger_xml_path, "wb") as f:
        f.write(b'<?xml version="1.0" ?>\n')
        f.write(
            b'<!DOCTYPE chargers SYSTEM "http://matsim.org/files/dtd/chargers_v1.dtd">\n'
        )
        tree.write(f)


def create_chargers_xml(link_ids: list, output_file_path, percent_dynamic=0.0):
    """
    Generate a chargers XML file with a mix of dynamic and static chargers.

    Args:
        link_ids (list): List of link IDs to place chargers on.
        output_file_path (str): Path to save the chargers XML file.
        percent_dynamic (float): Percentage of chargers that are dynamic.
    """
    num_chargers = len(link_ids)
    chargers = ET.Element("chargers")

    num_dynamic = int(num_chargers * percent_dynamic)
    num_static = num_chargers - num_dynamic

    link_ids = np.array(link_ids)
    dynamic_chargers = np.random.choice(link_ids, num_dynamic, replace=False)
    link_ids = np.setdiff1d(link_ids, dynamic_chargers)
    static_chargers = np.random.choice(link_ids, num_static, replace=False)

    id = 0
    for link_id in dynamic_chargers:
        ET.SubElement(
            chargers,
            "charger",
            id=str(id),
            link=str(link_id),
            plug_power="70",
            plug_count="9999",
            type="dynamic",
        )
        id += 1

    for link_id in static_chargers:
        ET.SubElement(
            chargers,
            "charger",
            id=str(id),
            link=str(link_id),
            plug_power="100.0",
            plug_count="1",
        )
        id += 1

    tree = ET.ElementTree(chargers)
    with open(output_file_path, "wb") as f:
        f.write(b'<?xml version="1.0" ?>\n')
        f.write(
            b'<!DOCTYPE chargers SYSTEM "http://matsim.org/files/dtd/chargers_v1.dtd">\n'
        )
        tree.write(f)


def main(args):
    """
    Main function to generate a chargers XML file based on input arguments.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
    """
    link_ids = load_network_xml(os.path.abspath(args.input_file))

    if args.num_chargers is not None:
        num_chargers = args.num_chargers
    elif args.percent is not None:
        num_links = len(link_ids)
        num_chargers = int(num_links * (args.percent / 100))
    else:
        raise ValueError("Either num_chargers or percent must be specified")

    link_ids = np.random.choice(link_ids, num_chargers)
    create_chargers_xml(
        link_ids, os.path.abspath(args.output_file), args.percent_dynamic
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate chargers XML file.")

    parser.add_argument("input_file", type=str, help="Input MATSim XML network")
    parser.add_argument(
        "output_file", type=str, help="Output path of chargers XML file"
    )
    parser.add_argument(
        "--num_chargers", type=int, help="Number of chargers to generate"
    )
    parser.add_argument(
        "--percent", type=float, help="Percentage of links to place chargers on"
    )
    parser.add_argument(
        "--percent_dynamic",
        type=float,
        help="Percentage of chargers that are dynamic vs static chargers. "
        "1.0 = 100 percent dynamic, 0.0 = 100 percent static.",
    )

    args = parser.parse_args()
    main(args)
