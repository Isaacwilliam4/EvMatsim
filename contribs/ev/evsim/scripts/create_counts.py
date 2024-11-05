import xml.etree.ElementTree as ET
import pandas as pd
import os
import argparse
from ..util import get_str


def main(station_data_folder, station_path, outputpath, year, scale_factor, name, desc):
    
    counts = ET.Element("counts", {"xmlns:xsi":"http://www.w3.org/2001/XMLSchema-instance", "xsi:noNamespaceSchemaLocation":"http://matsim.org/files/dtd/counts_v1.xsd", "name": name, "desc": desc, "year": get_str(year)})

    station_df = pd.read_csv(station_path)
    counts_data = []

    for i, link_id, station_id in station_df.itertuples():
        station_data_path = os.path.join(station_data_folder, get_str(station_id) + ".txt")
        udot_counts_df = pd.read_csv(station_data_path, sep='\t')
        udot_counts_df = udot_counts_df.sort_values('Hour')
        counts_data.append((link_id, station_id, udot_counts_df['Flow (Veh/Hour)'].values))

    for loc_id, cs_id, volumes in counts_data:
        count = ET.SubElement(counts, "count", loc_id=get_str(loc_id), cs_id=get_str(cs_id))
        for hour, val in enumerate(volumes, start=1):
            ET.SubElement(count, "volume", h=get_str(hour), val=get_str(val))

    tree = ET.ElementTree(counts)
    tree.write(outputpath, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process UDOT flow data and generate XML counts.")
    parser.add_argument('station_data_folder', type=str, help="Path to the folder containing station data files.")
    parser.add_argument('station_path', type=str, help="Path to the CSV file containing station information.")
    parser.add_argument('outputpath', type=str, help="Path to save the generated XML file.")
    parser.add_argument('--year', type=int, default=2024, help="Year for the counts (default: 2024).")
    parser.add_argument('--scale_factor', type=int, default=10, help="Scale factor for counts (default: 10).")
    parser.add_argument('--name', type=str, default="default", help="Name for the counts (default: 'default').")
    parser.add_argument('--desc', type=str, default="default", help="Description for the counts (default: 'default').")

    args = parser.parse_args()
    
    main(args.station_data_folder, args.station_path, args.outputpath, args.year, args.scale_factor, args.name, args.desc)
