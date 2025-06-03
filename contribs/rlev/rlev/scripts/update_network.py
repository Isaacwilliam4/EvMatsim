import xml.etree.ElementTree as ET
import argparse
import numpy as np
import os

DOCTYPE_DECLARATION = (
    '<!DOCTYPE network SYSTEM "http://www.matsim.org/files/dtd/network_v2.dtd">\n'
)


def add_slopes_to_links(xml_file, output_file):
    """
    Update MATSim network XML by modifying or adding attributes to links by setting slopes.

    :param xml_file: Input XML file path
    :param output_file: Output XML file path
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()

    links = root.find("links")
    if links is None:
        print("Error: <links> section not found in the XML file.")
        return

    # Add random slopes to links
    for link in links.findall("link"):
        slope = np.random.normal(-0.1, 0.1)  # Generate a random slope value
        link.set("slopes", str(slope))  # Ensure the attribute name matches your DTD

    # Write the modified XML to a temporary file
    temp_file = output_file + ".tmp"
    tree.write(temp_file, encoding="UTF-8", xml_declaration=True)

    # Manually insert DOCTYPE declaration at the beginning
    with open(temp_file, "r", encoding="UTF-8") as f:
        xml_content = f.readlines()

    with open(output_file, "w", encoding="UTF-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(DOCTYPE_DECLARATION)  # Insert DOCTYPE declaration
        f.writelines(xml_content[1:])  # Skip the original XML declaration

    print(f"Updated network file saved to {output_file}")
    os.remove(temp_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update MATSim network XML by adding slopes to links."
    )

    parser.add_argument("xml_file", help="Path to the input network XML file")
    parser.add_argument("output_file", help="Path to save the updated network XML file")

    args = parser.parse_args()
    add_slopes_to_links(args.xml_file, args.output_file)
