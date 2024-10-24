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

argparser = argparse.ArgumentParser()

argparser.add_argument('--config_path', help='The path to the matsim config.xml file', required=True, type=str)
argparser.add_argument('--network_path', help='The path to the matsim network.xml file', required=True, type=str)
argparser.add_argument('--chargers_path', help='The path to the matsim chargers.xml file', required=True, type=str)
argparser.add_argument('--results_path', help='The path to the directory where your results will be saved', required=True, type=str)
argparser.add_argument('--output_path', help='The path to the output directory created by matsim', required=True, type=str)
argparser.add_argument('--alg_prefix', help='Prefix for your algorithm', default='my_algorithm', required=True, type=str)
argparser.add_argument('--num_runs', help='The number of iterations your algorithm will run for', default=50, type=int)
argparser.add_argument('--num_matsim_iters', help='The number of iterations the matsim simulator will run for', default=5, type=int)
argparser.add_argument('--num_chargers', help='The number of chargers that will be placed on the network', type=int, default=10)
argparser.add_argument('--min_ram', help='The minimum memory in gigs used by the program', type=int, required=True)
argparser.add_argument('--max_ram', help='The maximum memory in gigs used by the program', type=int, required=True)


args = argparser.parse_args()

## The number of iterations your algorithm will go through
num_runs = args.num_runs

## The number of matsim iterations the agents will try to optimize for DON'T CHANGE
NUM_MATSIM_ITERS = args.num_matsim_iters
update_last_iteration(args.config_path, NUM_MATSIM_ITERS)

algorithm_results = pd.DataFrame(columns=['iteration','avg_score','selected_links'])

# Get the available link ids
link_ids = get_link_ids(args.network_path)

# The number of chargers we will be placing DON'T CHANGE, so we can be consistent across different algorithms
NUM_CHARGERS = 10

if not os.path.isdir(args.results_path):
  os.makedirs(args.results_path, exist_ok=False)

csvs_path = os.path.join(args.results_path,'csvs')
figs_path = os.path.join(args.results_path,'figs')

if not os.path.isdir(csvs_path):
  os.makedirs(csvs_path, exist_ok=False)

if not os.path.isdir(figs_path):
  os.makedirs(figs_path, exist_ok=False)


algorithm_name = f"{args.alg_prefix}_runs{num_runs}_exp"
num_exps = 0
results_dir = os.listdir(csvs_path)
for filename in results_dir:
  if algorithm_name in filename:
    num_exps += 1
algorithm_name = algorithm_name + str(num_exps+1) 

max_score = 0

# Min and max memory allocation, as you can tell I was using a nice computer (64G of ram), you'll probably want to lower this
os.environ['MAVEN_OPTS'] = f'-Xms{args.min_ram}g -Xmx{args.max_ram}g'

for i in range(1, num_runs+1):

  # Number of run display block
  RESET = "\033[0m"
  BOLD = "\033[1m"
  GREEN = "\033[32m"
  YELLOW = "\033[33m"
  CYAN = "\033[36m"

  print(f"{CYAN}\n" + "#" * 62 + RESET)
  print(f"{BOLD}{GREEN}# {'RUN':^58} #{RESET}")
  print(f"{BOLD}{GREEN}# {f'{i}/{num_runs}':^58} #{RESET}")
  print(f"{CYAN}#" * 62 + RESET + "\n")

  # here the links are chosen randomly implement your own algorithm and reference it here
  chosen_links = monte_carlo_algorithm(NUM_CHARGERS, link_ids, algorithm_results)
  create_chargers_xml(chosen_links, args.chargers_path)

  #run the matsim in java
  subprocess.run(['mvn','exec:java'])
  scores = pd.read_csv(os.path.join(args.output_path, 'scorestats.csv'), sep=';')

  average_score = scores['avg_average'].iloc[-1]
  row = pd.DataFrame({'iteration':[i], 'avg_score':[average_score],'selected_links':[chosen_links.tolist()]})

  algorithm_results = pd.concat([algorithm_results, row], ignore_index=True)

  #Save results every iteration in case something goes wrong
  algorithm_results.to_csv(os.path.join(csvs_path, f'{algorithm_name}_results.csv'), index=False)

  plt.plot(algorithm_results['iteration'], algorithm_results['avg_score'])
  plt.xlabel('Iteration')
  plt.ylabel('AvgScore')
  plt.title(algorithm_name)

  #path for where your score/iteration figure will go
  plt.savefig(os.path.join(figs_path, f'{algorithm_name}_plot.png'))

  if average_score > max_score:
    max_score = average_score
    src_dir = args.output_path
    dest_dir = os.path.join(os.path.dirname(src_dir), 'bestoutput')
    shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)



