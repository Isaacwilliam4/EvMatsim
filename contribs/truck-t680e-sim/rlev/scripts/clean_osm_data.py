import osmnx as ox
import argparse
from tqdm import tqdm


def clean_osm_data(input_file, output_file):
    """
    Cleans an OSM graph by processing maxspeed and lanes attributes.

    Args:
        input_file (str): Path to the input OSM XML file.
        output_file (str): Path to save the cleaned OSM XML file.
    """
    # Load the OSM graph from the input file
    G = ox.graph_from_xml(input_file, simplify=False)

    # Clean the OSM data
    for u, v, key, data in tqdm(
        G.edges(keys=True, data=True), desc="Cleaning OSM data"
    ):
        if "maxspeed" in data:
            if isinstance(data["maxspeed"], list):
                speed = data["maxspeed"][0][:2]
            else:
                speed = data["maxspeed"][:2]
            # OSM data is in mph; convert to kph for MATSim
            speedint = int(speed) * 1.609
            data["maxspeed"] = str(speedint)

        if "lanes" in data:
            if isinstance(data["lanes"], list):
                data["lanes"] = data["lanes"][0]

    # Save the cleaned graph to the output file
    ox.save_graph_xml(G, output_file)
    print(f"Cleaned OSM data saved to {output_file}")


def main(input_file, output_file):
    """
    Main function to clean OSM data.

    Args:
        input_file (str): Path to the input OSM XML file.
        output_file (str): Path to save the cleaned OSM XML file.
    """
    clean_osm_data(input_file, output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean OSM data")

    # Define positional arguments
    parser.add_argument("input", type=str, help="Input OSM file")
    parser.add_argument("output", type=str, help="Output path of cleaned OSM file")

    args = parser.parse_args()

    main(args.input, args.output)
