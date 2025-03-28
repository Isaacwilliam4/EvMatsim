import xml.etree.ElementTree as ET
import pandas as pd
import os
import argparse
from evsim.scripts.util import get_str

def generate_counts_from_files(
    station_data_folder,
    station_path,
    outputpath,
    year,
    name,
    desc,
):
    """
    Generate an XML counts file from station data by reading counts from files.
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

    station_df = pd.read_csv(station_path)
    counts_data = []

    for _, link_id, station_id in station_df.itertuples():
        station_data_path = os.path.join(station_data_folder, get_str(station_id) + ".txt")
        udot_counts_df = pd.read_csv(station_data_path, sep="\t").sort_values("Hour")
        counts_data.append((link_id, station_id, udot_counts_df["Flow (Veh/Hour)"].values))

    for loc_id, cs_id, volumes in counts_data:
        count = ET.SubElement(counts, "count", loc_id=get_str(loc_id), cs_id=get_str(cs_id))
        for hour, val in enumerate(volumes, start=1):
            ET.SubElement(count, "volume", h=get_str(hour), val=get_str(val))

    ET.ElementTree(counts).write(outputpath, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate XML counts from station data files.")
    parser.add_argument("--station_data_folder", type=str, required=True, help="Path to station data folder.")
    parser.add_argument("--station_path", type=str, required=True, help="Path to the station CSV file.")
    parser.add_argument("--outputpath", type=str, required=True, help="Path to save the output XML file.")
    parser.add_argument("--year", type=int, default=2024, help="Year for the counts.")
    parser.add_argument("--name", type=str, default="default", help="Name for the counts.")
    parser.add_argument("--desc", type=str, default="default", help="Description for the counts.")

    args = parser.parse_args()

    generate_counts_from_files(
        args.station_data_folder,
        args.station_path,
        args.outputpath,
        args.year,
        args.name,
        args.desc,
    )
