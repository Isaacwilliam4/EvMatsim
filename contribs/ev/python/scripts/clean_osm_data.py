import osmnx as ox 
import networkx as nx
import argparse
from tqdm import tqdm

parser = argparse.ArgumentParser(description='Clean OSM data')

parser.add_argument('--input', type=str, help='Input OSM file', required=True)
parser.add_argument('--output', type=str, help='Output path of cleaned OSM file', required=True)

args = parser.parse_args()

G = ox.graph_from_xml(args.input, simplify=False)

for u,v, key, data in tqdm(G.edges(keys=True, data=True), desc='Cleaning OSM data'):
  if 'maxspeed' in data:
    if type(data['maxspeed']) == list:
      speed = data['maxspeed'][0][:2]
    else:
      speed = data['maxspeed'][:2]
    # osm data is in mph, convert to kph for matsim
    speedint = int(speed) * 1.609
    data['maxspeed'] = str(speedint)
  if 'lanes' in data:
    if type(data['lanes']) == list:
      data['lanes'] = data['lanes'][0]

ox.save_graph_xml(G, args.output)