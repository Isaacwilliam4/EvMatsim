import xml.etree.ElementTree as ET
import random
import os
import argparse
import numpy as np

from evsim.scripts.util import get_str
from tqdm import tqdm

def get_node_coords(network_file):
    tree = ET.parse(network_file)
    root = tree.getroot()
    node_coords = {}

    for node in root.findall(".//node"):
        node_id = node.get("id")
        x = float(node.get("x"))
        y = float(node.get("y"))
        node_coords[node_id] = (x, y)

    return node_coords

def parse_counts_xml(counts_file):
    tree = ET.parse(counts_file)
    root = tree.getroot()
    counts = []

    for count_station in root.findall(".//count"):
        volume = sum(
            int(volume_elem.get("val"))
            for volume_elem in count_station.findall(".//volume")
        )
        counts.append(volume)

    return counts

def create_population_and_plans_xml_counts(
    network_xml_path,
    plans_output,
    num_agents=100,
):
    node_coords = get_node_coords(os.path.abspath(network_xml_path))
    plans_output = os.path.abspath(plans_output)

    plans = ET.Element("plans", attrib={"xml:lang": "de-CH"})
    node_ids = list(node_coords.keys())
    person_ids = []
    person_count = 1

    dist1 = np.random.normal(8, 2.5, num_agents // 2)
    dist2 = np.random.normal(17, 2.5, num_agents - len(dist1))
    dist = np.concatenate([dist1, dist2])
    dist = np.clip(dist, 0, 24)
    bins = np.arange(0, 24)
    counts, _ = np.histogram(dist, bins)
    pbar = tqdm(total=counts.sum(), desc="Creating Population")

    for i, count in enumerate(counts):
        count = int(get_str(count))
        for j in range(int(count)):
            pbar.update(1)
            origin_node_id = random.choice(node_ids)
            dest_node_id = random.choice(node_ids)
            origin_node = node_coords[origin_node_id]
            dest_node = node_coords[dest_node_id]
            person = ET.SubElement(plans, "person", id=str(person_count))
            person_ids.append(person_count)
            person_count += 1
            plan = ET.SubElement(person, "plan", selected="yes")
            start_time = (i + 1) % 24
            end_time = (start_time + 8) % 24
            start_time_str = (
                f"0{start_time}:00:00" if start_time < 10 else f"{start_time}:00:00"
            )
            end_time_str = (
                f"0{end_time}:00:00" if end_time < 10 else f"{end_time}:00:00"
            )
            ET.SubElement(
                plan,
                "act",
                type="h",
                x=str(origin_node[0]),
                y=str(origin_node[1]),
                end_time=start_time_str,
            )
            ET.SubElement(plan, "leg", mode="car")
            ET.SubElement(
                plan,
                "act",
                type="h",
                x=str(dest_node[0]),
                y=str(dest_node[1]),
                start_time=start_time_str,
                end_time=end_time_str,
            )

    tree = ET.ElementTree(plans)
    with open(plans_output, "wb") as f:
        f.write(b'<?xml version="1.0" ?>\n')
        f.write(
            b'<!DOCTYPE plans SYSTEM "http://www.matsim.org/files/dtd/plans_v4.dtd">\n'
        )
        tree.write(f)



def main(args):
    """
    Main function to parse arguments and generate population and plans.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
    """
    create_population_and_plans_xml_counts(
        args.network,
        args.plans_output,
        args.num_agents,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate population and plans XML files"
    )

    parser.add_argument("network", type=str, help="Input matsim xml network")
    parser.add_argument("plans_output", type=str, help="Output path of plans network")
    parser.add_argument(
        "--num_agents",
        type=int,
        help="The number of agents to generate",
        default=100,
    )

    args = parser.parse_args()
    main(args)
