import subprocess
import pandas as pd
import xml.etree.ElementTree as ET
import os
import argparse
import shutil
import matplotlib.pyplot as plt
from evsim.util import *
from evsim.scripts.create_population import *
from pathlib import Path

def update_Q(Q: pd.DataFrame, chosen_links, score):
    # Set 'link_id' as the index for faster lookups
    Q = Q.set_index("link_id")

    for link in chosen_links:
        if link in Q.index:
            row = Q.loc[link]
            avg_score = 0 if row['average_reward'] == -9999 else row["average_reward"]
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

def update_csv_and_fig(algorithm_results_path,
                       iteration, 
                       algorithm_name, 
                       average_score, 
                       chosen_links, 
                       figs_path):


    algorithm_results = pd.read_csv(algorithm_results_path)
    row = pd.DataFrame({"iteration": [iteration], "avg_score": [average_score], "selected_links": [chosen_links]})
    algorithm_results = pd.concat([algorithm_results, row], ignore_index=True)
    algorithm_results.to_csv(algorithm_results_path, index=False)
    plt.plot(algorithm_results["iteration"].values, algorithm_results["avg_score"].values)
    plt.xlabel("Iteration")
    plt.ylabel("AvgScore")
    plt.title(algorithm_name)
    plt.savefig(os.path.join(figs_path, f"{algorithm_name}_plot.png"))

def main(args):
    if args.num_agents:
        node_coords = get_node_coords(args.network_path)
        create_population_and_plans_xml(args.num_agents, node_coords, args.plans_path)
    num_runs = args.num_runs
    update_last_iteration(args.config_path, args.num_matsim_iters - 1)
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

    algorithm_results_path = os.path.join(csvs_path, f'{algorithm_name}_results.csv')
    algorithm_results = pd.DataFrame({'iteration':[], 'avg_score':[], "selected_links":[]})
    algorithm_results.to_csv(algorithm_results_path, index=False)

    max_score = -np.inf

    if args.min_ram and args.max_ram:
        os.environ["MAVEN_OPTS"] = f"-Xms{args.min_ram}g -Xmx{args.max_ram}g"

    if os.path.exists(args.q_path):
        Q = load_Q(args.q_path)
    else:
        Q = pd.DataFrame(
            {
                "link_id": link_ids,
                "average_reward": np.full(len(link_ids), -9999),
                "count": np.zeros_like(link_ids, dtype=int),
            }
        )

    total_iterations = 0
    # Explore phase: random link selection without replacement
    explored_links = np.random.permutation(link_ids)
    for i in range(args.explore_steps):
        # Display run status
        print(f"\033[36m\n{'#' * 62}\033[0m")
        print(f"\033[1m\033[32m# {'EXPLORATION':^58} #\033[0m")
        print(f"\033[1m\033[32m# {f'{i+1}/{args.explore_steps}':^58} #\033[0m")
        print(f"\033[36m{'#' * 62}\033[0m\n")
        if len(explored_links) < args.num_chargers:
            explored_links = np.random.permutation(link_ids)
        chosen_links, explored_links = (
            explored_links[:args.num_chargers],
            explored_links[args.num_chargers:],
        )

        create_chargers_xml(chosen_links, args.chargers_path)
        # Run matsim in Java
        os.system(f'mvn exec:java -Dexec.args="{args.config_path}"')
        scores = pd.read_csv(os.path.join(args.output_path, "scorestats.csv"), sep=";")
        average_score = scores["avg_executed"].iloc[-1]

        # Update Q values
        Q = update_Q(Q, chosen_links, average_score)
        save_Q(Q, args.q_path)

        update_csv_and_fig(algorithm_results_path,
                    total_iterations, 
                    algorithm_name, 
                    average_score, 
                    chosen_links, 
                    figs_path)
        
        total_iterations += 1


    for i in range(1, num_runs + 1):
        print_run_info(i, num_runs)

        if args.algorithm == "montecarlo":
            chosen_links = monte_carlo_algorithm(args.num_chargers, link_ids)
        elif args.algorithm == "egreedy":
            chosen_links = e_greedy(args.num_chargers, Q)

        create_chargers_xml(chosen_links, args.chargers_path)

        os.system(f'mvn -e exec:java -Dexec.args="{args.config_path}"')
        scores = pd.read_csv(os.path.join(args.output_path, "scorestats.csv"), sep=";")

        average_score = scores["avg_executed"].iloc[-1]

        # Update Q values
        Q = update_Q(Q, chosen_links, average_score)
        save_Q(Q, args.q_path)

        update_csv_and_fig(algorithm_results_path,
                    total_iterations, 
                    algorithm_name, 
                    average_score, 
                    chosen_links, 
                    figs_path)
        
        total_iterations += 1

        if average_score > max_score:
            max_score = average_score
            output_path = Path(args.output_path)
            dest_dir = os.path.join(os.path.join(output_path.parent), "bestoutput")
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
    argparser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    argparser.add_argument("config_path", type=str, help="Path to the matsim config.xml file")
    argparser.add_argument("network_path", type=str, help="Path to the matsim network.xml file")
    argparser.add_argument("plans_path", type=str, help="Path to the output plans.xml file")
    argparser.add_argument("chargers_path", type=str, help="Path to the output matsim chargers.xml file")
    argparser.add_argument("results_path", type=str, help="Directory where results will be saved")
    argparser.add_argument("output_path", type=str, help="Path to the output directory created by matsim")
    argparser.add_argument("q_path",help="Path to q file containing dataframe hold link average reward, \
                           will be created if doesn't exist, should be .csv file", type=str)
    argparser.add_argument("--algorithm",help="Algorithm to use for optimization",choices=["montecarlo","egreedy"],
                            default="montecarlo",type=str)
    argparser.add_argument("--explore_steps", help="Number of steps to explore", default=0, type=int)
    argparser.add_argument("--alg_prefix", required=True, default="my_algorithm", type=str, help="Prefix for your algorithm")
    argparser.add_argument("--num_runs", default=50, type=int, help="Number of iterations for the algorithm")
    argparser.add_argument("--num_matsim_iters", default=5, type=int, help="Number of iterations for the matsim simulator")
    argparser.add_argument("--num_agents", type=int, help="Number of agents on the network")
    argparser.add_argument("--num_chargers", default=10, type=int, help="Number of chargers on the network")
    argparser.add_argument("--min_ram", type=int, help="Minimum memory in gigs used by the program")
    argparser.add_argument("--max_ram", type=int, help="Maximum memory in gigs used by the program")

    args = argparser.parse_args()
    main(args)
