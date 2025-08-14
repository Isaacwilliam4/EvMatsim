import xml.etree.ElementTree as ET
import random
import os
import argparse
import pandas as pd
import numpy as np

from rlev.scripts.util import save_xml, get_str


def create_vehicle_definitions(ids, initial_soc):
    root = ET.Element(
        "vehicleDefinitions",
        attrib={
            "xmlns": "http://www.matsim.org/files/dtd",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "http://www.matsim.org/files/dtd http://www.matsim.org/files/dtd/vehicleDefinitions_v2.0.xsd",
        },
    )

    vehicle_type = ET.SubElement(root, "vehicleType", id="EV_100.0kWh")
    ET.SubElement(vehicle_type, "capacity", seats="0", standingRoomInPersons="0")
    ET.SubElement(vehicle_type, "length", meter="7.5")
    ET.SubElement(vehicle_type, "width", meter="1.0")

    engine_info = ET.SubElement(vehicle_type, "engineInformation")
    attributes = ET.SubElement(engine_info, "attributes")

    ET.SubElement(
        attributes,
        "attribute",
        name="HbefaTechnology",
        **{"class": "java.lang.String"},
    ).text = "electricity"

    ET.SubElement(
        attributes,
        "attribute",
        name="chargerTypes",
        **{"class": "java.util.Collections$UnmodifiableCollection"},
    ).text = '\n\t\t\t\t["default", "dynamic"]\n\t\t\t'

    ET.SubElement(
        attributes,
        "attribute",
        name="energyCapacityInKWhOrLiters",
        **{"class": "java.lang.Double"},
    ).text = '\n\t\t\t\t100.0\n\t\t\t'

    ET.SubElement(vehicle_type, "costInformation")
    ET.SubElement(vehicle_type, "passengerCarEquivalents", pce="1.0")
    ET.SubElement(vehicle_type, "networkMode", networkMode="car")
    ET.SubElement(vehicle_type, "flowEfficiencyFactor", factor="1.0")

    for id in ids:
        vehicle = ET.SubElement(root, "vehicle", id=str(id), type="EV_100.0kWh")
        attributes = ET.SubElement(vehicle, "attributes")
        ET.SubElement(
            attributes,
            "attribute",
            name="initialSoc",
            **{"class": "java.lang.Double"},
        ).text = f"\n\t\t\t\t{initial_soc:.1f}\n\t\t\t"

    return ET.ElementTree(root)

def create_vehicles_from_plans(
    plans_xml_path,
    vehicles_output,
    initial_soc=1,
):
    plans_xml_path = os.path.abspath(plans_xml_path)
    vehicles_output = os.path.abspath(vehicles_output)

    # Parse the input plans XML
    tree = ET.parse(plans_xml_path)
    root = tree.getroot()

    # Extract person IDs
    person_ids = []
    for person in root.findall("person"):
        person_id = person.get("id")
        if person_id:
            person_ids.append(person_id)

    # Create the vehicle definitions XML tree
    vehicle_tree = create_vehicle_definitions(person_ids, initial_soc)
    save_xml(vehicle_tree, vehicles_output)

def main(args):
    """
    Main function to parse arguments and generate population and plans.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
    """
    create_vehicles_from_plans(
        args.plans_xml,
        args.vehicles_output,
        args.initial_soc,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate population and plans XML files"
    )

    parser.add_argument("plans_xml", type=str, help="Path to the matsim plans XML")
    parser.add_argument(
        "vehicles_output", type=str, help="Output file of the vehicles.xml"
    )
    parser.add_argument(
        "initial_soc", type=int, help="Initial state of charge of the vehicles"
    )

    args = parser.parse_args()
    main(args)
