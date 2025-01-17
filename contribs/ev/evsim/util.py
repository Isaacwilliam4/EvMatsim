import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

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

def setup_config(config_xml_path, num_iterations, output_dir):
    """Sets the number of matsim iterations that need to run,
    sets the output directory file to write the matsim results to,
    and returns the paths to the network, plans, vehicles, and charger xml files.

    Args:
        config_xml_path (str): path to the config xml file
        num_iterations (int): the number of matsim iterations to run
        output_dir (str): the directory to write the matsim results to
    """
    # Parse the XML file
    tree = ET.parse(config_xml_path)
    root = tree.getroot()

    # Find the 'controler' module
    for module in root.findall(".//module"):
        if module.get('name') == 'controler':
            # Find the 'lastIteration' parameter and update its value
            for param in module.findall("param"):
                if param.get('name') == 'lastIteration':
                    param.set('value', str(num_iterations))
                if param.get('name') == 'outputDirectory':
                    param.set('value', output_dir)
                if param.get('name') == 'inputNetworkFile':
                    network_file = param.get('value')
                if param.get('name') == 'plansFilePath':
                    plans_file = param.get('value')
                if param.get('name') == 'vehiclesFilePath':
                    vehicles_file = param.get('value')
                if param.get('name') == 'inputChargersFile':
                    chargers_file = param.get('value')
                if param.get('name') == 'qValuesFile':
                    q_values_file = param.get('value')
            
        # Manually write the header to the output file
    with open(config_xml_path, "wb") as f:
        # Write the XML declaration and DOCTYPE
        f.write(b'<?xml version="1.0" ?>\n')
        f.write(b'<!DOCTYPE config SYSTEM "http://www.matsim.org/files/dtd/config_v2.dtd">\n')

        # Write the tree structure
        tree.write(f)

    return network_file, plans_file, vehicles_file, chargers_file, q_values_file

def get_str(num):
    if isinstance(num, str):
        return num.replace(',', '').replace('.0', '')
    return str(int(num)).replace(',', '').replace('.0', '')

def monte_carlo_algorithm(num_chargers, link_ids) -> list:
    return np.random.choice(link_ids, num_chargers).tolist()
    
def e_greedy(num_chargers, Q, epsilon) -> list:
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

def save_xml(tree, output_file):
    # Save the XML to a file
    tree.write(output_file, encoding="UTF-8", xml_declaration=True)

def update_Q(Q: pd.DataFrame, chosen_links, score):
    # Set 'link_id' as the index for faster lookups
    Q = Q.set_index("link_id")

    for link in chosen_links:
        if link in Q.index:
            row = Q.loc[link]
            avg_score = row["average_reward"]
            count = row["count"]

            new_score = ((avg_score * count) + score) / (count + 1)
            count += 1

            # Update the row with new values
            Q.loc[link, "average_reward"] = new_score
            Q.loc[link, "count"] = count
        else:
            print(f"\n\n\n Link {link} not found in Q DataFrame \n\n\n")

    # Reset the index if you need to work with the 'link_id' as a column again
    Q = Q.reset_index()

    return Q

def save_Q(Q: pd.DataFrame, q_path):
    Q.to_csv(q_path, index=False)


def load_Q(q_path):
    return pd.read_csv(q_path)

def save_csv_and_plot(chosen_links, average_score, iter, algorithm_results, results_path, time_string, Q, q_path):
    # Update Q values
    Q = update_Q(Q, chosen_links, average_score)
    save_Q(Q, q_path)

    row = pd.DataFrame({"iteration": [iter], "avg_score": [average_score], "selected_links": [chosen_links]})
    algorithm_results = pd.concat([algorithm_results, row], ignore_index=True)

    # Save results every iteration
    algorithm_results.to_csv(os.path.join(results_path, f"{time_string}_results.csv"), index=False)

    plt.plot(algorithm_results["iteration"].values, algorithm_results["avg_score"].values)
    plt.xlabel("Iteration")
    plt.ylabel("AvgScore")
    plt.savefig(os.path.join(results_path, f"{time_string}_results.png"))

def extract_paths_from_config(config_xml_path):
    # Parse the XML file
    tree = ET.parse(config_xml_path)
    root = tree.getroot()

    # Find the 'controler' module
    for module in root.findall(".//module"):
        if module.get('name') == 'controler':
            # Find the 'outputDirectory' parameter
            for param in module.findall("param"):
                if param.get('name') == 'outputDirectory':
                    output_dir = param.get('value')
                if param.get('name') == 'inputNetworkFile':
                    network_file = param.get('value')
                if param.get('name') == 'plansFilePath':
                    plans_file = param.get('value')
                if param.get('name') == 'vehiclesFilePath':
                    vehicles_file = param.get('value')
                if param.get('name') == 'inputChargersFile':
                    chargers_file = param.get('value')
                if param.get('name') == 'qValuesFile':
                    q_values_file = param.get('value')
        
    return output_dir, network_file, plans_file, vehicles_file, chargers_file, q_values_file

