import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import os

station_data_folder = "/home/isaacp/research/repos/EvMatsim/contribs/ev/data/udot_flow_data"
station_path = "/home/isaacp/research/repos/EvMatsim/contribs/ev/data/station_data.csv"
outputpath = "/home/isaacp/research/repos/EvMatsim/contribs/ev/scenarios/tinytown/test_counts.xml"
year = 2024
scale_factor = 10
name = "default"
desc="default"

def get_str(num):
    if type(num) is str:
        return num.replace(',','').replace('.0','')
    return str(int(num)).replace(',','').replace('.0','')

counts = ET.Element("counts", {"name":name, "desc":desc, "year":get_str(year), 'countsScaleFactor':get_str(scale_factor)})
counts.set('countsScaleFactor', get_str(scale_factor))

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
        ET.SubElement(count, "volume", h=get_str(hour+1), val=get_str(val))

tree = ET.ElementTree(counts)
tree.write(outputpath, encoding="utf-8", xml_declaration=True)
