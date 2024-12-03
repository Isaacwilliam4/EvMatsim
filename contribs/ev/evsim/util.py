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

def create_chargers_xml(link_ids, output_file_path):
    # Create the root element for the plans
    chargers = ET.Element("chargers")

    # Loop over the number of agents
    for i,id in enumerate(link_ids):

        charger = ET.SubElement(chargers, "charger", id=str(i+1), link=str(id), plug_power="100.0", plug_count="5")

    # Convert the ElementTree to a string
    tree = ET.ElementTree(chargers)

    # Manually write the header to the output file
    with open(output_file_path, "wb") as f:
        # Write the XML declaration and DOCTYPE
        f.write(b'<?xml version="1.0" ?>\n')
        f.write(b'<!DOCTYPE chargers SYSTEM "http://matsim.org/files/dtd/chargers_v1.dtd">\n')

        # Write the tree structure
        tree.write(f)

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


def create_vehicle_definitions(ids, charge_home_percent):
    # Create the root element with namespaces
    root = ET.Element("vehicleDefinitions", attrib={
        "xmlns": "http://www.matsim.org/files/dtd",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": "http://www.matsim.org/files/dtd http://www.matsim.org/files/dtd/vehicleDefinitions_v2.0.xsd"
    })

    # Create the vehicle type
    vehicle_type = ET.SubElement(root, "vehicleType", id="EV_65.0kWh")
    
    # Add capacity
    ET.SubElement(vehicle_type, "capacity", seats="0", standingRoomInPersons="0")

    # Add length and width
    ET.SubElement(vehicle_type, "length", meter="7.5")
    ET.SubElement(vehicle_type, "width", meter="1.0")

    # Add engine information with attributes
    engine_info = ET.SubElement(vehicle_type, "engineInformation")
    attributes = ET.SubElement(engine_info, "attributes")
    
    ET.SubElement(attributes, "attribute", name="HbefaTechnology", **{"class": "java.lang.String"}).text = "electricity"
    ET.SubElement(attributes, "attribute", name="chargerTypes", **{"class": "java.util.Collections$UnmodifiableCollection"}).text = '["default"]'
    ET.SubElement(attributes, "attribute", name="energyCapacityInKWhOrLiters", **{"class": "java.lang.Double"}).text = "65.0"

    # Add cost information (empty for now)
    ET.SubElement(vehicle_type, "costInformation")

    # Add passengerCarEquivalents and networkMode
    ET.SubElement(vehicle_type, "passengerCarEquivalents", pce="1.0")
    ET.SubElement(vehicle_type, "networkMode", networkMode="car")
    ET.SubElement(vehicle_type, "flowEfficiencyFactor", factor="1.0")

    # Create vehicles with varying initial states of charge (SoC)
    for id in ids:
        vehicle = ET.SubElement(root, "vehicle", id=str(id), type="EV_65.0kWh")
        attributes = ET.SubElement(vehicle, "attributes")
        
        # # Set initial SoC based on the vehicle ID
        # soc = round(random.uniform(0.2, 0.8), 2)

        # Add the initialSoc attribute
        if np.random.random() < charge_home_percent:
            ET.SubElement(attributes, "attribute", name="initialSoc", **{"class": "java.lang.Double"}).text = str(1)
        else:
            ET.SubElement(attributes, "attribute", name="initialSoc", **{"class": "java.lang.Double"}).text = str(np.random.uniform(.1,.2))

    return ET.ElementTree(root)

def save_xml(tree, output_file):
    # Save the XML to a file
    tree.write(output_file, encoding="UTF-8", xml_declaration=True)