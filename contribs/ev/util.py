import xml.etree.ElementTree as ET


def get_link_ids(network_file):
    # Parse the network XML file
    tree = ET.parse(network_file)
    root = tree.getroot()

    # Create a dictionary to store node coordinates by ID
    link_ids = []

    # Find all node elements
    for link in root.findall(".//link"):
        link_id = link.get("id")
        link_ids.append(link_id)


    return np.array(link_ids)

def create_chargers_xml(link_ids, output_file_path):
    # Create the root element for the plans
    chargers = ET.Element("chargers")

    # Loop over the number of agents
    for i,id in enumerate(link_ids):
        charger = ET.SubElement(chargers, "charger", id=str(i+1), link=id, plug_power="100.0", plug_count="5")

    # Convert the ElementTree to a string
    tree = ET.ElementTree(chargers)

    # Manually write the header to the output file
    with open(output_file_path, "wb") as f:
        # Write the XML declaration and DOCTYPE
        f.write(b'<?xml version="1.0" ?>\n')
        f.write(b'<!DOCTYPE chargers SYSTEM "http://matsim.org/files/dtd/chargers_v1.dtd">\n')

        # Write the tree structure
        tree.write(f)