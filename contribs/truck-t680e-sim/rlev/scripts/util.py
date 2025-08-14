import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os


def get_link_ids(network_file):
    """
    Extracts link IDs from a MATSim network XML file.

    Args:
        network_file (str): Path to the network XML file.

    Returns:
        np.ndarray: Array of link IDs as integers.
    """
    tree = ET.parse(network_file)
    root = tree.getroot()
    link_ids = [int(link.get("id")) for link in root.findall(".//link")]
    return np.array(link_ids)


def setup_config(config_xml_path, output_dir, num_iterations=0):
    """
    Configures MATSim XML file with iterations and output directory.

    Args:
        config_xml_path (str): Path to the config XML file.
        output_dir (str): Directory for MATSim results.
        num_iterations (int): Number of MATSim iterations to run.

    Returns:
        tuple: Paths to network, plans, vehicles, and charger XML files.
    """
    tree = ET.parse(config_xml_path)
    root = tree.getroot()

    network_file, plans_file, vehicles_file, chargers_file, counts_file = None, None, None, None, None

    for module in root.findall(".//module"):
        for param in module.findall("param"):
            if param.get("name") == "lastIteration":
                param.set("value", str(num_iterations))
            if param.get("name") == "outputDirectory":
                param.set("value", output_dir)
            if param.get("name") == "inputNetworkFile":
                network_file = param.get("value")
            if param.get("name") == "inputPlansFile":
                plans_file = param.get("value")
            if param.get("name") == "vehiclesFile":
                vehicles_file = param.get("value")
            if param.get("name") == "chargersFile":
                chargers_file = param.get("value")
            if param.get("name") == "inputCountsFile":
                counts_file = param.get("value")

    with open(config_xml_path, "wb") as f:
        f.write(b'<?xml version="1.0" ?>\n')
        f.write(
            b'<!DOCTYPE config SYSTEM "http://www.matsim.org/files/dtd/config_v2.dtd">\n'
        )
        tree.write(f)

    return network_file, plans_file, vehicles_file, chargers_file, counts_file


def get_str(num):
    """
    Converts a number to a string, removing commas and ".0".

    Args:
        num (int or str): Input number or string.

    Returns:
        str: Processed string representation of the number.
    """
    if isinstance(num, str):
        return num.replace(",", "").replace(".0", "")
    return str(int(num)).replace(",", "").replace(".0", "")


def monte_carlo_algorithm(num_chargers, link_ids) -> list:
    """
    Selects random links for chargers using Monte Carlo.

    Args:
        num_chargers (int): Number of chargers to place.
        link_ids (list): List of link IDs.

    Returns:
        list: Selected link IDs.
    """
    return np.random.choice(link_ids, num_chargers).tolist()


def e_greedy(num_chargers, Q, epsilon) -> list:
    """
    Selects links using an epsilon-greedy algorithm.

    Args:
        num_chargers (int): Number of chargers to place.
        Q (pd.DataFrame): DataFrame with link rewards.
        epsilon (float): Exploration probability.

    Returns:
        list: Selected link IDs.
    """
    links = Q["link_id"].values
    rewards = Q["average_reward"].values
    vals = sorted(zip(links, rewards), key=lambda x: x[1])
    chargers = []

    for _ in range(num_chargers):
        if np.random.random() > epsilon:
            chosen_val = vals.pop()
        else:
            chosen_val = vals[np.random.randint(0, len(vals))]
            vals.remove(chosen_val)
        chargers.append(chosen_val[0])

    return chargers


def save_xml(tree, output_file):
    """
    Saves an XML tree to a file.

    Args:
        tree (ET.ElementTree): XML tree to save.
        output_file (str): Path to the output file.
    """
    tree.write(output_file, encoding="UTF-8", xml_declaration=True)


def update_Q(Q: pd.DataFrame, chosen_links, score):
    """
    Updates Q-values for selected links based on a score.

    Args:
        Q (pd.DataFrame): DataFrame with Q-values.
        chosen_links (list): Selected link IDs.
        score (float): Reward score.

    Returns:
        pd.DataFrame: Updated Q-values DataFrame.
    """
    Q = Q.set_index("link_id")

    for link in chosen_links:
        if link in Q.index:
            row = Q.loc[link]
            avg_score = row["average_reward"]
            count = row["count"]

            new_score = ((avg_score * count) + score) / (count + 1)
            count += 1

            Q.loc[link, "average_reward"] = new_score
            Q.loc[link, "count"] = count
        else:
            print(f"Link {link} not found in Q DataFrame")

    return Q.reset_index()


def save_Q(Q: pd.DataFrame, q_path):
    """
    Saves Q-values DataFrame to a CSV file.

    Args:
        Q (pd.DataFrame): DataFrame with Q-values.
        q_path (str): Path to the output CSV file.
    """
    Q.to_csv(q_path, index=False)


def load_Q(q_path):
    """
    Loads Q-values DataFrame from a CSV file.

    Args:
        q_path (str): Path to the input CSV file.

    Returns:
        pd.DataFrame: Loaded Q-values DataFrame.
    """
    return pd.read_csv(q_path)


def save_csv_and_plot(
    chosen_links,
    average_score,
    iter,
    algorithm_results,
    results_path,
    time_string,
    Q,
    q_path,
):
    """
    Saves results to CSV, updates Q-values, and plots scores.

    Args:
        chosen_links (list): Selected link IDs.
        average_score (float): Average reward score.
        iter (int): Current iteration.
        algorithm_results (pd.DataFrame): Results DataFrame.
        results_path (str): Path to save results.
        time_string (str): Timestamp string.
        Q (pd.DataFrame): Q-values DataFrame.
        q_path (str): Path to save Q-values.

    Returns:
        tuple: Updated algorithm results and Q-values.
    """
    Q = update_Q(Q, chosen_links, average_score)
    save_Q(Q, q_path)

    row = pd.DataFrame(
        {
            "iteration": [iter],
            "avg_score": [average_score],
            "selected_links": [chosen_links],
        }
    )
    algorithm_results = pd.concat([algorithm_results, row], ignore_index=True)

    algorithm_results.to_csv(
        os.path.join(results_path, f"{time_string}_results.csv"), index=False
    )

    plt.plot(
        algorithm_results["iteration"].values,
        algorithm_results["avg_score"].values,
    )
    plt.xlabel("Iteration")
    plt.ylabel("AvgScore")
    plt.savefig(os.path.join(results_path, f"{time_string}_results.png"))

    return algorithm_results, Q


def extract_paths_from_config(config_xml_path):
    """
    Extracts file paths from a MATSim config XML file.

    Args:
        config_xml_path (str): Path to the config XML file.

    Returns:
        tuple: Paths to output, network, plans, vehicles, chargers, and Q-values.
    """
    tree = ET.parse(config_xml_path)
    root = tree.getroot()

    output_dir, network_file, plans_file, vehicles_file = None, None, None, None
    chargers_file, q_values_file = None, None

    for module in root.findall(".//module"):
        if module.get("name") == "controler":
            for param in module.findall("param"):
                if param.get("name") == "outputDirectory":
                    output_dir = param.get("value")
                if param.get("name") == "inputNetworkFile":
                    network_file = param.get("value")
                if param.get("name") == "plansFilePath":
                    plans_file = param.get("value")
                if param.get("name") == "vehiclesFilePath":
                    vehicles_file = param.get("value")
                if param.get("name") == "inputChargersFile":
                    chargers_file = param.get("value")
                if param.get("name") == "qValuesFile":
                    q_values_file = param.get("value")

    return (
        output_dir,
        network_file,
        plans_file,
        vehicles_file,
        chargers_file,
        q_values_file,
    )
