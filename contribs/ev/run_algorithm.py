import subprocess
import pandas as pd
import xml.etree.ElementTree as ET
import random
import numpy as np
import matplotlib.pyplot as plt
import os
from python.util import *
import argparse
import shutil

# Argument parser setup
argparser = argparse.ArgumentParser()

argparser.add_argument(
    "--config_path", help="Path to the matsim config.xml file", required=True, type=str
)
argparser.add_argument(
    "--network_path",
    help="Path to the matsim network.xml file",
    required=True,
    type=str,
)
argparser.add_argument(
    "--chargers_path",
    help="Path to the matsim chargers.xml file",
    required=True,
    type=str,
)
argparser.add_argument(
    "--results_path",
    help="Path to directory where results will be saved",
    required=True,
    type=str,
)
argparser.add_argument(
    "--output_path",
    help="Path to output directory created by matsim",
    required=True,
    type=str,
)
argparser.add_argument(
    "--q_path",
    help="Path to q file containing dictionary hold link average reward, will be created if doesn't exist, should be .npz file",
    required=True,
    type=str,
)
argparser.add_argument(
    "--explore_steps", help="Number of steps to explore", default=0, type=int
)
argparser.add_argument(
    "--algorithm",
    help="Algorithm to use for optimization",
    choices=["montecarlo"],
    default="montecarlo",
    type=str,
)
argparser.add_argument(
    "--alg_prefix",
    help="Prefix for the algorithm",
    default="my_algorithm",
    required=True,
    type=str,
)
argparser.add_argument(
    "--num_runs", help="Number of algorithm iterations", default=50, type=int
)
argparser.add_argument(
    "--num_matsim_iters", help="Number of matsim iterations", default=5, type=int
)
argparser.add_argument(
    "--num_chargers",
    help="Number of chargers placed on the network",
    type=int,
    default=10,
)
argparser.add_argument("--min_ram", help="Minimum memory (GB) for program", type=int)
argparser.add_argument("--max_ram", help="Maximum memory (GB) for program", type=int)


# Q dictionary update function
def update_Q(Q, chosen_links, score):
    for link in chosen_links:
        Q[link][1] = (Q[link][1] * Q[link][0] + score) / (
            Q[link][0] + 1
        )  # Update average score
        Q[link][0] += 1  # Increment count for this link


def save_Q(Q, q_path):
    np.savez(os.path.abspath(q_path), Q=Q)


def load_Q(q_path):
    npz_Q = np.load(q_path)
    return npz_Q.Q


# Parse arguments
args = argparser.parse_args()

# Set up iteration and matsim configuration
num_runs = args.num_runs
NUM_MATSIM_ITERS = args.num_matsim_iters
update_last_iteration(args.config_path, NUM_MATSIM_ITERS)

algorithm_results = pd.DataFrame(columns=["iteration", "avg_score", "selected_links"])

# Get available link IDs and setup for consistency
link_ids = get_link_ids(args.network_path)
NUM_CHARGERS = 10  # Constant for consistency across algorithms

# Set up results directories
if not os.path.isdir(args.results_path):
    os.makedirs(args.results_path, exist_ok=False)

csvs_path = os.path.join(args.results_path, "csvs")
figs_path = os.path.join(args.results_path, "figs")
os.makedirs(csvs_path, exist_ok=True)
os.makedirs(figs_path, exist_ok=True)

# Unique algorithm name based on existing runs
algorithm_name = f"{args.alg_prefix}_runs{num_runs}_exp"
num_exps = sum(1 for filename in os.listdir(csvs_path) if algorithm_name in filename)
algorithm_name = f"{algorithm_name}{num_exps + 1}"

max_score = -np.inf

# Set Java memory options if provided
if args.min_ram and args.max_ram:
    os.environ["MAVEN_OPTS"] = f"-Xms{args.min_ram}g -Xmx{args.max_ram}g"

if os.path.exists(args.q_path):
    Q = load_Q(args.q_path)
else:
    # Initialize Q dictionary: [count, average score]
    Q = dict(zip(link_ids, [[0, 0] for _ in range(len(link_ids))]))

# Explore phase: random link selection without replacement
explored_links = np.random.permutation(link_ids)
for i in range(args.explore_steps):
    if len(explored_links) < NUM_CHARGERS:
        break
    chosen_links, explored_links = (
        explored_links[:NUM_CHARGERS],
        explored_links[NUM_CHARGERS:],
    )

    create_chargers_xml(chosen_links, args.chargers_path)

    # Run matsim in Java
    subprocess.run([f"mvn exec:java {os.path.abspath(args.config_path)}"], shell=True)
    scores = pd.read_csv(os.path.join(args.output_path, "scorestats.csv"), sep=";")
    average_score = scores["avg_executed"].iloc[-1]

    # Update Q values
    update_Q(Q, chosen_links, average_score)

# Main algorithm run loop
for i in range(1, num_runs + 1):
    # Display run status
    print(f"\033[36m\n{'#' * 62}\033[0m")
    print(f"\033[1m\033[32m# {'RUN':^58} #\033[0m")
    print(f"\033[1m\033[32m# {f'{i}/{num_runs}':^58} #\033[0m")
    print(f"\033[36m{'#' * 62}\033[0m\n")

    # Link selection based on chosen algorithm
    if args.algorithm == "montecarlo":
        chosen_links = monte_carlo_algorithm(NUM_CHARGERS, link_ids, algorithm_results)

    create_chargers_xml(chosen_links, args.chargers_path)

    # Run matsim in Java
    subprocess.run(["mvn exec:java"], shell=True)
    scores = pd.read_csv(os.path.join(args.output_path, "scorestats.csv"), sep=";")
    average_score = scores["avg_executed"].iloc[-1]

    update_Q(Q, chosen_links, average_score)

    # Record and save results
    row = pd.DataFrame(
        {
            "iteration": [i],
            "avg_score": [average_score],
            "selected_links": [chosen_links.tolist()],
        }
    )
    algorithm_results = pd.concat([algorithm_results, row], ignore_index=True)
    algorithm_results.to_csv(
        os.path.join(csvs_path, f"{algorithm_name}_results.csv"), index=False
    )

    # Plotting the score per iteration
    plt.plot(
        algorithm_results["iteration"].values, algorithm_results["avg_score"].values
    )
    plt.xlabel("Iteration")
    plt.ylabel("Avg Score")
    plt.title(algorithm_name)
    plt.savefig(os.path.join(figs_path, f"{algorithm_name}_plot.png"))

    # Save best result configuration
    if average_score > max_score:
        max_score = average_score
        shutil.copytree(
            args.output_path,
            os.path.join(os.path.dirname(args.output_path), "bestoutput"),
            dirs_exist_ok=True,
        )
