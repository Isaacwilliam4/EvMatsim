import subprocess
import pandas as pd
import xml.etree.ElementTree as ET
import os
import argparse
import shutil
import matplotlib.pyplot as plt
from evsim.util import *
from evsim.scripts.create_population import *
from evsim.scripts.create_chargers import *
from pathlib import Path
from datetime import datetime

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


def main(args):
    config_path = Path(args.config_path)
    scenario_path = config_path.parent
    output_path = os.path.join(scenario_path / "output")
    csvs_path = os.path.join(args.results_path, "csvs")
    figs_path = os.path.join(args.results_path, "figs")
    q_path = os.path.join(args.results_path, "Q.csv")
    best_output_path = os.path.join(scenario_path / "best_output")

    if args.num_agents:
        node_coords = get_node_coords(args.network_path)
        create_population_and_plans_xml_counts(node_coords, args.plans_path, args.vehicles_path, args.num_agents)

    num_runs = args.num_runs
    update_last_iteration_and_output_dir(args.config_path, args.num_matsim_iters - 1, output_path)
    algorithm_results = pd.DataFrame(columns=["iteration", "avg_score", "selected_links"])
    link_ids = get_link_ids(args.network_path)
    
    if not os.path.isdir(args.results_path):
        os.makedirs(args.results_path, exist_ok=False)

    os.makedirs(csvs_path, exist_ok=True)
    os.makedirs(figs_path, exist_ok=True)

    current_time = datetime.now()
    time_string = current_time.strftime("%Y%m%d_%H%M%S")
    algorithm_name = f"{args.alg_prefix}_{time_string}"
    max_score = -np.inf

    if args.min_ram and args.max_ram:
        os.environ["MAVEN_OPTS"] = f"-Xms{args.min_ram}g -Xmx{args.max_ram}g"

    if os.path.exists(q_path):
        Q = load_Q(q_path)
    else:
        Q = pd.DataFrame(
            {
                "link_id": link_ids,
                "average_reward": np.full(link_ids.shape, args.initial_q_values),
                "count": np.zeros_like(link_ids, dtype=int),
            }
        )

    # Explore phase: random link selection without replacement
    explored_links = np.random.permutation(link_ids)
    iter = 0

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

        create_chargers_xml(chosen_links, args.chargers_path, args.percent_dynamic)
        # Run matsim in Java
        os.system(f'mvn exec:java -Dexec.args="{args.config_path}"')
        scores = pd.read_csv(os.path.join(output_path, "scorestats.csv"), sep=";")
        average_score = scores["avg_executed"].iloc[-1]

        # Update Q values
        Q = update_Q(Q, chosen_links, average_score)
        save_Q(Q, q_path)

        row = pd.DataFrame({"iteration": [iter], "avg_score": [average_score], "selected_links": [chosen_links]})
        algorithm_results = pd.concat([algorithm_results, row], ignore_index=True)

        # Save results every iteration
        algorithm_results.to_csv(os.path.join(csvs_path, f"{algorithm_name}_results.csv"), index=False)

        plt.plot(algorithm_results["iteration"].values, algorithm_results["avg_score"].values)
        plt.xlabel("Iteration")
        plt.ylabel("AvgScore")
        plt.title(algorithm_name)
        plt.savefig(os.path.join(figs_path, f"{algorithm_name}_plot.png"))
        iter += 1

    for i in range(1, num_runs + 1):
        print_run_info(i, num_runs)

        if args.algorithm == "montecarlo":
            chosen_links = monte_carlo_algorithm(args.num_chargers, link_ids, algorithm_results)
        elif args.algorithm == "egreedy":
            if args.epsilon < 0:
                epsilon = (num_runs - i + 1) / num_runs
            else:
                epsilon = args.epsilon
            chosen_links = e_greedy(args.num_chargers, Q, epsilon)
        # elif args.algorithm == "pso":
        #     chosen_links, average_score = 

        create_chargers_xml(chosen_links, args.chargers_path, args.percent_dynamic)

        os.system(f'mvn -e exec:java -Dexec.args="{args.config_path}"')
        scores = pd.read_csv(os.path.join(output_path, "scorestats.csv"), sep=";")

        average_score = scores["avg_executed"].iloc[-1]

        # Update Q values
        Q = update_Q(Q, chosen_links, average_score)
        save_Q(Q, q_path)

        row = pd.DataFrame({"iteration": [iter], "avg_score": [average_score], "selected_links": [chosen_links]})
        algorithm_results = pd.concat([algorithm_results, row], ignore_index=True)

        # Save results every iteration
        algorithm_results.to_csv(os.path.join(csvs_path, f"{algorithm_name}_results.csv"), index=False)

        plt.plot(algorithm_results["iteration"].values, algorithm_results["avg_score"].values)
        plt.xlabel("Iteration")
        plt.ylabel("AvgScore")
        plt.title(algorithm_name)
        plt.savefig(os.path.join(figs_path, f"{algorithm_name}_plot.png"))

        if average_score > max_score:
            max_score = average_score
            shutil.copytree(output_path, best_output_path, dirs_exist_ok=True)
        
        iter += 1
    
    # Once the iterations are done, move the output folder and best output folder to the resutls folder
    shutil.move(output_path, args.results_path)
    shutil.move(best_output_path, args.results_path)


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
    argparser.add_argument("plans_path", type=str, help="Path to the plans.xml file")
    argparser.add_argument("vehicles_path", type=str, help="Path to the matsim vehicles.xml file")
    argparser.add_argument("chargers_path", type=str, help="Path to the matsim chargers.xml file")
    argparser.add_argument("results_path", type=str, help="Directory where results will be saved, if a previous run exists,\
                           it will use the Q.csv file to continue the optimization")
    argparser.add_argument("--percent_dynamic", help="percent of chargers that are dynamic chargers, 1 means \
                           all dynamic, 0 means all static", default=0, type=float)
    argparser.add_argument("--explore_steps", help="Number of steps to explore", default=0, type=int)
    argparser.add_argument("--algorithm",help="Algorithm to use for optimization",choices=["montecarlo","egreedy"],
                            default="montecarlo",type=str)
    argparser.add_argument("--epsilon", help="If using the e-greedy algorithm, the epsilon value, if -1 then a\
                           linear decay will be used", default=-1, type=float)
    argparser.add_argument("--alg_prefix", required=True, default="my_algorithm", type=str, help="Prefix for your algorithm")
    argparser.add_argument("--initial_q_values", default=9999, type=int, help="default q value for q table, high values encourage exploration")
    argparser.add_argument("--num_runs", default=50, type=int, help="Number of iterations for the algorithm")
    argparser.add_argument("--num_matsim_iters", default=5, type=int, help="Number of iterations for the matsim simulator")
    argparser.add_argument("--num_agents", type=int, help="Number of agents on the network, if none it will use the existing plans.xml file")
    argparser.add_argument("--num_chargers", default=10, type=int, help="Number of chargers on the network")
    argparser.add_argument("--min_ram", type=int, help="Minimum memory in gigs used by the program")
    argparser.add_argument("--max_ram", type=int, help="Maximum memory in gigs used by the program")

    args = argparser.parse_args()

    print(args)

    main(args)


