import xml.etree.ElementTree as ET
import numpy as np

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


    return np.array(link_ids).astype(int)

def update_last_iteration(xml_file, new_value):
    # Parse the XML file
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Find the 'controler' module
    for module in root.findall(".//module"):
        if module.get('name') == 'controler':
            # Find the 'lastIteration' parameter and update its value
            for param in module.findall("param"):
                if param.get('name') == 'lastIteration':
                    param.set('value', str(new_value))
                    break
                
        # Manually write the header to the output file
    with open(xml_file, "wb") as f:
        # Write the XML declaration and DOCTYPE
        f.write(b'<?xml version="1.0" ?>\n')
        f.write(b'<!DOCTYPE config SYSTEM "http://www.matsim.org/files/dtd/config_v2.dtd">\n')

        # Write the tree structure
        tree.write(f)

def get_str(num):
    if isinstance(num, str):
        return num.replace(',', '').replace('.0', '')
    return str(int(num)).replace(',', '').replace('.0', '')

def monte_carlo_algorithm(num_chargers, link_ids) -> list:
    return np.random.choice(link_ids, num_chargers).tolist()
    
def e_greedy(num_chargers, Q, epsilon=0.05) -> list:
    links = Q['link_id'].values
    rewards = Q['average_reward'].values
    vals = zip(links, rewards)
    vals = sorted(vals, key = lambda x : x[1])
    chargers = []

    for _ in range(num_chargers):
        if np.random.random() > epsilon:
            chosen_val = vals.pop()
            chargers.append(chosen_val[0])
        else:
            chosen_val = vals[np.random.randint(0, len(vals))]
            chargers.append(chosen_val[0])
            vals.remove(chosen_val)

    return chargers

def save_xml(tree, output_file):
    # Save the XML to a file
    tree.write(output_file, encoding="UTF-8", xml_declaration=True)