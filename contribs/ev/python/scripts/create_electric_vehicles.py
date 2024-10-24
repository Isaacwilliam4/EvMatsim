import argparse
import xml.etree.ElementTree as ET
import random

def create_vehicle_definitions(num_vehicles):
    # Create the root element with namespaces
    root = ET.Element("vehicleDefinitions", attrib={
        "xmlns": "http://www.matsim.org/files/dtd",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": "http://www.matsim.org/files/dtd http://www.matsim.org/files/dtd/vehicleDefinitions_v2.0.xsd"
    })

    # Create the vehicle type
    vehicle_type = ET.SubElement(root, "vehicleType", id="EV_5.0kWh")
    
    # Add capacity
    capacity = ET.SubElement(vehicle_type, "capacity", seats="0", standingRoomInPersons="0")

    # Add length and width
    ET.SubElement(vehicle_type, "length", meter="7.5")
    ET.SubElement(vehicle_type, "width", meter="1.0")

    # Add engine information with attributes
    engine_info = ET.SubElement(vehicle_type, "engineInformation")
    attributes = ET.SubElement(engine_info, "attributes")
    
    ET.SubElement(attributes, "attribute", name="HbefaTechnology", **{"class": "java.lang.String"}).text = "electricity"
    ET.SubElement(attributes, "attribute", name="chargerTypes", **{"class": "java.util.Collections$UnmodifiableCollection"}).text = '["default"]'
    ET.SubElement(attributes, "attribute", name="energyCapacityInKWhOrLiters", **{"class": "java.lang.Double"}).text = "5.0"

    # Add cost information (empty for now)
    ET.SubElement(vehicle_type, "costInformation")

    # Add passengerCarEquivalents and networkMode
    ET.SubElement(vehicle_type, "passengerCarEquivalents", pce="1.0")
    ET.SubElement(vehicle_type, "networkMode", networkMode="car")
    ET.SubElement(vehicle_type, "flowEfficiencyFactor", factor="1.0")

    # Create vehicles with varying initial states of charge (SoC)
    for i in range(1, num_vehicles + 1):
        vehicle = ET.SubElement(root, "vehicle", id=str(i), type="EV_5.0kWh")
        attributes = ET.SubElement(vehicle, "attributes")
        
        # Set initial SoC based on the vehicle ID
        soc = round(random.uniform(0.2, 0.8), 2)

        # Add the initialSoc attribute
        ET.SubElement(attributes, "attribute", name="initialSoc", **{"class": "java.lang.Double"}).text = str(soc)

    return ET.ElementTree(root)

def save_xml(tree, output_file):
    # Save the XML to a file
    tree.write(output_file, encoding="UTF-8", xml_declaration=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate MATSim vehicleDefinitions XML.")
    parser.add_argument("--numvehicles", type=int, required=True, help="Number of vehicles to generate.")
    parser.add_argument("--output", type=str, default="vehicle_definitions.xml", help="Output XML file name.")

    args = parser.parse_args()

    # Create the XML tree
    vehicle_definitions_tree = create_vehicle_definitions(args.numvehicles)

    # Save to the specified output file
    save_xml(vehicle_definitions_tree, args.output)
    print(f"Vehicle definitions XML file '{args.output}' generated with {args.numvehicles} vehicles.")
