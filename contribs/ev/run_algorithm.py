import subprocess
import pandas as pd
import xml.etree.ElementTree as ET
import random
import numpy as np
import matplotlib.pyplot as plt


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


    return np.array(link_ids)

def create_chargers_xml(link_ids, output_file_path):
    # Create the root element for the plans
    chargers = ET.Element("chargers")

    # Loop over the number of agents
    for i,id in enumerate(link_ids):
        charger = ET.SubElement(chargers, "charger", id=str(i+1), link=id, plug_power="100.0", plug_count="5")

    # Convert the ElementTree to a string
    tree = ET.ElementTree(chargers)

    # Manually write the header to the output file
    with open(output_file_path, "wb") as f:
        # Write the XML declaration and DOCTYPE
        f.write(b'<?xml version="1.0" ?>\n')
        f.write(b'<!DOCTYPE chargers SYSTEM "http://matsim.org/files/dtd/chargers_v1.dtd">\n')

        # Write the tree structure
        tree.write(f)

    print(f"{num_chargers} chargers written to {output_file_path}")


num_runs = 1
algorithm_results = pd.DataFrame(columns=['iteration','avg_score','selected_chargers'])
link_ids = get_link_ids('./scenarios/tinytown/tiny_town_network.xml')
num_chargers = 10
algorithm_name = "Monte_Carlo_1_run"

for i in range(1, num_runs+1):
  RESET = "\033[0m"
  BOLD = "\033[1m"
  GREEN = "\033[32m"
  YELLOW = "\033[33m"
  CYAN = "\033[36m"

  # Assuming i and num_runs are defined
  print(f"{CYAN}\n" + "#" * 62 + RESET)
  print(f"{BOLD}{GREEN}# {'RUN':^58} #{RESET}")
  print(f"{BOLD}{GREEN}# {f'{i}/{num_runs}':^58} #{RESET}")
  print(f"{CYAN}#" * 62 + RESET + "\n")

  # here the links are chosen randomly
  chosen_links = np.random.choice(link_ids, num_chargers)
  create_chargers_xml(chosen_links, './scenarios/tinytown/tiny_town_chargers.xml')

  subprocess.run(['mvn','exec:java'])

  scores = pd.read_csv('./scenarios/tinytown/output/scorestats.csv',sep=';')

  average_score = scores['avg_average'].iloc[-1]
  row = pd.DataFrame({'iteration':i, 'avg_score':average_score,'selected_chargers':chosen_links.tolist()})

  algorithm_results = pd.concat([algorithm_results, row], ignore_index=True)

algorithm_results.to_csv(f'./python/algorithm_results/csvs/algorithm_results_{algorithm_name}.csv', index=False)

plt.plot(algorithm_results['iteration'], algorithm_results['avg_score'])
plt.xlabel('Iteration')
plt.ylabel('AvgScore')
plt.title(algorithm_name)
plt.savefig(f'./python/algorithm_results/figs/{algorithm_name}.png')