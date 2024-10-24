import subprocess
import pandas as pd
import xml.etree.ElementTree as ET
import random
import numpy as np
import matplotlib.pyplot as plt
import os
from util import *

## The number of iterations your algorithm will go through
num_runs = 50

algorithm_results = pd.DataFrame(columns=['iteration','avg_score','selected_links'])

# Get the available link ids
link_ids = get_link_ids('./scenarios/tinytown/tiny_town_network.xml')

# The number of chargers we will be placing DON'T CHANGE, so we can be consistent across different algorithms
NUM_CHARGERS = 10

# Name your algorithm, this is used for creating files and saving results, so make sure to change if you don't want to overwrite anything
algorithm_name = f"monte_carlo_{num_runs}"

# Min and max memory allocation, as you can tell I was using a nice computer (64G of ram), you'll probably want to lower this
os.environ['MAVEN_OPTS'] = '-Xms40g -Xmx50g'

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

  # here the links are chosen randomly implement your own algorithm
  chosen_links = np.random.choice(link_ids, NUM_CHARGERS)
  create_chargers_xml(chosen_links, './scenarios/tinytown/tiny_town_chargers.xml')

  #run the matsim in java
  subprocess.run(['mvn','exec:java'])
  scores = pd.read_csv('./scenarios/tinytown/output/scorestats.csv',sep=';')

  average_score = scores['avg_average'].iloc[-1]
  row = pd.DataFrame({'iteration':[i], 'avg_score':[average_score],'selected_links':[chosen_links.tolist()]})

  algorithm_results = pd.concat([algorithm_results, row], ignore_index=True)

  #Save results every iteration in case something goes wrong
  algorithm_results.to_csv(f'./python/algorithm_results/csvs/{algorithm_name}_results.csv', index=False)

  plt.plot(algorithm_results['iteration'], algorithm_results['avg_score'])
  plt.xlabel('Iteration')
  plt.ylabel('AvgScore')
  plt.title(algorithm_name)

  #path for where your score/iteration figure will go
  plt.savefig(f'./python/algorithm_results/figs/{algorithm_name}.png')


