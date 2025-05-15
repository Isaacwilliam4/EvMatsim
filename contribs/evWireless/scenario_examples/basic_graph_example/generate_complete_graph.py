import xml.etree.ElementTree as ET
from pathlib import Path
import os

DOCTYPE_DECLARATION = (
    '<!DOCTYPE network SYSTEM "http://www.matsim.org/files/dtd/network_v2.dtd">\n'
)

def parse_network(network_path):
    """
    Parses the MATSim network XML file and creates a graph representation.
    """

    network_path = Path(network_path)
    output_path = Path(network_path.parent, "complete_graph_network.xml")
    matsim_node_ids = []

    network_tree = ET.parse(network_path)
    network_root = network_tree.getroot()

    for node in network_root.findall(".//node"):
        node_id = node.get("id")
        matsim_node_ids.append(node_id)

    links = ET.SubElement(network_root, "links")
    link_id = 1
    for node_id in matsim_node_ids:
        for nod_id2 in matsim_node_ids:
            if node_id != nod_id2:
                attrib = {
                    "id":str(link_id),
                    "from":node_id,
                    "to":nod_id2,
                    "length":"10",
                    "freespeed":"1",
                    "capacity":"1500",
                    "permlanes":"1",
                    "oneway":"1",
                    "modes":"car"
                }
                ET.SubElement(links, "link", attrib=attrib)
                link_id+=1

    # Write the modified XML to a temporary file
    temp_file = Path(network_path.parent, "tmp.tmp") 
    network_tree.write(temp_file, encoding="UTF-8", xml_declaration=True)

    # Manually insert DOCTYPE declaration at the beginning
    with open(temp_file, "r", encoding="UTF-8") as f:
        xml_content = f.readlines()

    with open(output_path, "w", encoding="UTF-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(DOCTYPE_DECLARATION)  # Insert DOCTYPE declaration
        f.writelines(xml_content[1:])  # Skip the original XML declaration

    print(f"Updated network file saved to {output_path}")
    os.remove(temp_file)

if __name__ == "__main__":
    network_path = "/home/isaacp/repos/EvMatsim/contribs/ev/scenario_examples/basic_graph_example/basic_graph_network.xml"
    parse_network(network_path)
