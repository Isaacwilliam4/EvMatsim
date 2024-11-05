import subprocess
import pandas as pd
import xml.etree.ElementTree as ET
import os
import argparse
import shutil
import matplotlib.pyplot as plt
from evsim.util import *
from evsim.scripts.create_population import *

def main(args):
    if args.num_agents:
        node_coords = get_node_coords(args.network_path)
        create_population_and_plans_xml(args.num_agents, node_coords, args.plans_path)
    num_runs = args.num_runs
    NUM_MATSIM_ITERS = args.num_matsim_iters
    update_last_iteration(args.config_path, NUM_MATSIM_ITERS - 1)
    algorithm_results = pd.DataFrame(columns=["iteration", "avg_score", "selected_links"])
    link_ids = get_link_ids(args.network_path)
    
    if not os.path.isdir(args.results_path):
        os.makedirs(args.results_path, exist_ok=False)

    csvs_path = os.path.join(args.results_path, "csvs")
    figs_path = os.path.join(args.results_path, "figs")
    
    os.makedirs(csvs_path, exist_ok=True)
    os.makedirs(figs_path, exist_ok=True)

    algorithm_name = f"{args.alg_prefix}_runs{num_runs}_exp"
    num_exps = sum(1 for filename in os.listdir(csvs_path) if algorithm_name in filename)
    algorithm_name += str(num_exps + 1)

    max_score = -np.inf

    if args.min_ram and args.max_ram:
        os.environ["MAVEN_OPTS"] = f"-Xms{args.min_ram}g -Xmx{args.max_ram}g"

    for i in range(1, num_runs + 1):
        print_run_info(i, num_runs)

        chosen_links = monte_carlo_algorithm(args.num_chargers, link_ids, algorithm_results)
        create_chargers_xml(chosen_links, args.chargers_path)

        subprocess.run([f"mvn exec:java -Dexec.args={os.path.abspath(args.config_path)}"], shell=True)
        scores = pd.read_csv(os.path.join(args.output_path, "scorestats.csv"), sep=";")

        average_score = scores["avg_executed"].iloc[-1]
        row = pd.DataFrame({"iteration": [i], "avg_score": [average_score], "selected_links": [chosen_links.tolist()]})
        algorithm_results = pd.concat([algorithm_results, row], ignore_index=True)

        # Save results every iteration
        algorithm_results.to_csv(os.path.join(csvs_path, f"{algorithm_name}_results.csv"), index=False)

        plt.plot(algorithm_results["iteration"], algorithm_results["avg_score"])
        plt.xlabel("Iteration")
        plt.ylabel("AvgScore")
        plt.title(algorithm_name)
        plt.savefig(os.path.join(figs_path, f"{algorithm_name}_plot.png"))

        if average_score > max_score:
            max_score = average_score
            dest_dir = os.path.join(os.path.dirname(args.output_path), "bestoutput")
            shutil.copytree(args.output_path, dest_dir, dirs_exist_ok=True)

def print_run_info(current_run, total_runs):
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"

    print(f"{CYAN}\n" + "#" * 62 + RESET)
    print(f"{BOLD}{GREEN}# {'RUN':^58} #{RESET}")
    print(f"{BOLD}{GREEN}# {f'{current_run}/{total_runs}':^58} #{RESET}")
    print(f"{CYAN}#" * 62 + RESET + "\n")

if __name__ == "__main__":
    argparser = argparse.ArgumentParser()

    argparser.add_argument("config_path", type=str, help="Path to the matsim config.xml file")
    argparser.add_argument("network_path", type=str, help="Path to the matsim network.xml file")
    argparser.add_argument("plans_path", type=str, help="Path to the output plans.xml file")
    argparser.add_argument("chargers_path", type=str, help="Path to the output matsim chargers.xml file")
    argparser.add_argument("results_path", type=str, help="Directory where results will be saved")
    argparser.add_argument("output_path", type=str, help="Path to the output directory created by matsim")

    argparser.add_argument("--alg_prefix", required=True, default="my_algorithm", type=str, help="Prefix for your algorithm")
    argparser.add_argument("--num_runs", default=50, type=int, help="Number of iterations for the algorithm")
    argparser.add_argument("--num_matsim_iters", default=5, type=int, help="Number of iterations for the matsim simulator")
    argparser.add_argument("--num_agents", type=int, help="Number of agents on the network")
    argparser.add_argument("--num_chargers", default=10, type=int, help="Number of chargers on the network")
    argparser.add_argument("--min_ram", type=int, help="Minimum memory in gigs used by the program")
    argparser.add_argument("--max_ram", type=int, help="Maximum memory in gigs used by the program")

    args = argparser.parse_args()
    main(args)
