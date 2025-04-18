import xml.etree.ElementTree as ET

def update_slope_attributes(input_file, output_file):
    # Parse the XML file
    tree = ET.parse(input_file)
    root = tree.getroot()

    # Iterate through all <link> elements
    for link in root.findall(".//link"):
        slope = link.get("slope")
        if slope is not None:
            # Convert slope to a decimal and rename the attribute to "slopes"
            try:
                slope_decimal = float(slope) / 100
                link.set("slopes", f"{slope_decimal:.6f}")
                del link.attrib["slope"]  # Remove the old "slope" attribute
            except ValueError:
                print(f"Invalid slope value: {slope}")

    # Save the modified XML to the output file
    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    print(f"Updated XML saved to {output_file}")

# Example usage
input_file = r"c:\Users\webec\CODEPROJECTS\ASPIRE\EvMatsim\contribs\ev\scenario_examples\utahev_scenario_example\network_with_slopes.xml"
output_file = r"c:\Users\webec\CODEPROJECTS\ASPIRE\EvMatsim\contribs\ev\scenario_examples\utahev_scenario_example\network_with_slopes_updated.xml"
update_slope_attributes(input_file, output_file)