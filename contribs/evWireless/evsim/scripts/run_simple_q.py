import pandas as pd
import numpy as np
import os
import argparse
import shutil
from contribs.ev.evsim.scripts.util import setup_config, load_Q, save_csv_and_plot, get_link_ids, e_greedy
from evsim.scripts.create_population_ev import (
    create_population_and_plans_xml_counts,
    get_node_coords,
)
from evsim.scripts.create_chargers import create_chargers_xml
from pathlib import Path
from datetime import datetime


def main(args):
    current_time = datetime.now()
    time_string = current_time.strftime("%Y%m%d_%H%M%S")

    config_path = Path(args.config_path)
    scenario_path = config_path.parent
    results_path = scenario_path / f"{time_string}_results"
    output_path = os.path.join(results_path / "output")

    (
        network_file_name,
        plans_file_name,
        vehicles_file_name,
        chargers_file_name,
    ) = setup_config(args.config_path, output_path, args.num_matsim_iters - 1)

    network_path = os.path.join(scenario_path, network_file_name)
    plans_path = os.path.join(scenario_path, plans_file_name)
    vehicles_path = os.path.join(scenario_path, vehicles_file_name)
    chargers_path = os.path.join(scenario_path, chargers_file_name)

    os.makedirs(results_path, exist_ok=False)

    with open(results_path / "args.txt", "w") as f:
        for key, value in vars(args).items():
            f.write(f"{key}: {value}\n")

    q_path = os.path.join(results_path, "Q.csv")
    best_output_path = os.path.join(results_path / "best_output")

    node_coords = get_node_coords(network_path)
    create_population_and_plans_xml_counts(
        node_coords,
        plans_path,
        vehicles_path,
        args.num_agents,
        counts_path=args.counts_path,
        population_multiplier=args.pop_multiplier,
        initial_soc=args.initial_soc,
    )

    algorithm_results = pd.DataFrame(
        columns=["iteration", "avg_score", "selected_links"]
    )
    link_ids = get_link_ids(network_path)

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

        chosen_links = e_greedy(args.num_chargers, Q, args.epsilon)

        create_chargers_xml(chosen_links, chargers_path, args.percent_dynamic)

        os.system(f'mvn -e exec:java -Dexec.args="{args.config_path}"')
        scores = pd.read_csv(os.path.join(output_path, "scorestats.csv"), sep=";")

        average_score = scores["avg_executed"].iloc[-1]

        algorithm_results, Q = save_csv_and_plot(
            chosen_links,
            average_score,
            i,
            algorithm_results,
            results_path,
            time_string,
            Q,
            q_path,
        )

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
    argparser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    argparser.add_argument(
        "config_path", type=str, help="Path to the matsim config.xml file"
    )
    argparser.add_argument(
        "--counts_path",
        default=None,
        help="path to the counts file with 24 data points in the \
            'Flow (Veh/Hour)' column correlating to the number of vehicles \
                each hour that should go out",
    )
    argparser.add_argument(
        "--num_agents",
        type=int,
        help="Number of agents on the network, if none it will use the \
            existing plans.xml file note: if a counts.xml file is provided \
            in the config, then that will override the num_agents parameter",
    )
    argparser.add_argument(
        "--pop_multiplier",
        default=1,
        type=float,
        help="How much to multiply the population by based on the counts \
              file, if no counts.xml file is provided, this is ignored",
    )
    argparser.add_argument(
        "--percent_dynamic",
        help="percent of chargers that are dynamic chargers, 1 means \
                           all dynamic, 0 means all static",
        default=0,
        type=float,
    )
    argparser.add_argument(
        "--epsilon",
        help="Epsilon value for egreedy policy",
        default=0.05,
        type=float,
    )
    argparser.add_argument(
        "--initial_q_values",
        default=9999,
        type=int,
        help="default q value for q table, high values encourage exploration",
    )
    argparser.add_argument(
        "--num_runs",
        default=50,
        type=int,
        help="Number of iterations for the algorithm",
    )
    argparser.add_argument(
        "--num_matsim_iters",
        default=1,
        type=int,
        help="Number of iterations for the matsim simulator",
    )
    argparser.add_argument(
        "--num_chargers",
        default=10,
        type=int,
        help="Number of chargers on the network",
    )
    argparser.add_argument(
        "--initial_soc",
        default=1,
        type=float,
        help="Initial state of charge for the agents 0<=soc<=1",
    )
    argparser.add_argument(
        "--min_ram", type=int, help="Minimum memory in gigs used by the program"
    )
    argparser.add_argument(
        "--max_ram", type=int, help="Maximum memory in gigs used by the program"
    )

    args = argparser.parse_args()

    main(args)
