import xml.etree.ElementTree as ET
import numpy as np
import argparse
from evsim.scripts.util import get_str, get_link_ids

def generate_counts_simulated(
    network_path,
    outputpath,
    year,
    name,
    desc,
    mean,
    std_dev,
):
    """
    Generate an XML counts file with simulated data using a normal distribution.
    """
    counts = ET.Element(
        "counts",
        {
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:noNamespaceSchemaLocation": "http://matsim.org/files/dtd/counts_v1.xsd",
            "name": name,
            "desc": desc,
            "year": get_str(year),
        },
    )

    link_ids = get_link_ids(network_path)
    link_ids = np.random.choice(link_ids, int(0.1*len(link_ids)), replace=False)  # Select 10% of links to simulate counts for
    counts_data = []

    for i, link_id in enumerate(link_ids):
        station_id = i + 1
        simulated_counts = np.random.normal(mean, std_dev, 24).clip(0, np.inf)  # Simulate 24 hours
        counts_data.append((link_id, station_id, simulated_counts))

    for loc_id, cs_id, volumes in counts_data:
        count = ET.SubElement(counts, "count", loc_id=get_str(loc_id), cs_id=get_str(cs_id))
        for hour, val in enumerate(volumes, start=1):
            ET.SubElement(count, "volume", h=get_str(hour), val=get_str(val))

    ET.ElementTree(counts).write(outputpath, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate XML counts using simulated data.")
    parser.add_argument("--network_path", type=str, required=True, help="Path to the XML network.")
    parser.add_argument("--outputpath", type=str, required=True, help="Path to save the output XML file.")
    parser.add_argument("--year", type=int, default=2024, help="Year for the counts.")
    parser.add_argument("--name", type=str, default="default", help="Name for the counts.")
    parser.add_argument("--desc", type=str, default="default", help="Description for the counts.")
    parser.add_argument("--mean", type=float, default=1000, help="Mean value for simulated counts.")
    parser.add_argument("--std_dev", type=float, default=100, help="Standard deviation for simulated counts.")

    args = parser.parse_args()

    generate_counts_simulated(
        args.network_path,
        args.outputpath,
        args.year,
        args.name,
        args.desc,
        args.mean,
        args.std_dev,
    )
