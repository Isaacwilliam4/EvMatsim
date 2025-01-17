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





def main(args):
    current_time = datetime.now()
    time_string = current_time.strftime("%Y%m%d_%H%M%S")

    config_path = Path(args.config_path)
    scenario_path = config_path.parent

    results_path = scenario_path / f"{time_string}_results"
    os.makedirs(results_path, exist_ok=False)

    with open(results_path / "args.txt", "w") as f:
        for key, value in vars(args).items():
            f.write(f"{key}: {value}\n")

    output_path = os.path.join(results_path / "output")
    q_path = os.path.join(results_path, "Q.csv")
    best_output_path = os.path.join(results_path / "best_output")

    if args.num_agents:
        node_coords = get_node_coords(args.network_path)
        create_population_and_plans_xml_counts(node_coords, 
                                               args.plans_path, 
                                               args.vehicles_path, 
                                               args.num_agents, 
                                               initial_soc=args.initial_soc)

 
    setup_config(args.config_path, args.num_matsim_iters - 1, output_path)
    algorithm_results = pd.DataFrame(columns=["iteration", "avg_score", "selected_links"])
    link_ids = get_link_ids(args.network_path)

    current_time = datetime.now()
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

    for i in range(1, args.num_runs + 1):
        print_run_info(i, args.num_runs)

        if args.algorithm == "montecarlo":
            chosen_links = monte_carlo_algorithm(args.num_chargers, link_ids, algorithm_results)
        elif args.algorithm == "egreedy":
            chosen_links = e_greedy(args.num_chargers, Q, args.epsilon)

        create_chargers_xml(chosen_links, args.chargers_path, args.percent_dynamic)

        os.system(f'mvn -e exec:java -Dexec.args="{args.config_path}"')
        scores = pd.read_csv(os.path.join(output_path, "scorestats.csv"), sep=";")

        average_score = scores["avg_executed"].iloc[-1]

        save_csv_and_plot(chosen_links, average_score, i, algorithm_results, results_path, time_string, Q, q_path)

        if average_score > max_score:
            max_score = average_score
            shutil.copytree(output_path, best_output_path, dirs_exist_ok=True)

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
    argparser.add_argument("--percent_dynamic", help="percent of chargers that are dynamic chargers, 1 means \
                           all dynamic, 0 means all static", default=0, type=float)
    argparser.add_argument("--algorithm",help="Algorithm to use for optimization",choices=["montecarlo","egreedy"],
                            default="montecarlo",type=str)
    argparser.add_argument("--epsilon", help="If using the e-greedy algorithm, the epsilon value", default=0.05, type=float)
    argparser.add_argument("--initial_q_values", default=9999, type=int, help="default q value for q table, high values encourage exploration")
    argparser.add_argument("--num_runs", default=50, type=int, help="Number of iterations for the algorithm")
    argparser.add_argument("--num_matsim_iters", default=5, type=int, help="Number of iterations for the matsim simulator")
    argparser.add_argument("--num_agents", type=int, help="Number of agents on the network, if none it will use the existing plans.xml file")
    argparser.add_argument("--num_chargers", default=10, type=int, help="Number of chargers on the network")
    argparser.add_argument("--initial_soc", default=1, type=float, help="Initial state of charge for the agents 0<=soc<=1")
    argparser.add_argument("--min_ram", type=int, help="Minimum memory in gigs used by the program")
    argparser.add_argument("--max_ram", type=int, help="Maximum memory in gigs used by the program")

    args = argparser.parse_args()

    main(args)


