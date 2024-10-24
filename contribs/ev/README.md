
# EV
Electric Vehicle functionality for MATSim


# Usage

The `monte_carlo_algorithm.py` serves as a basis on how to implement your own algorithm for optimizing the charger placement. The code is well commented so you can refer to it in order implement your own algorithm. But this will give you an understanding of the structure of the code and how it works.

```
cd matsim-libs/contribs/ev
python run_algorithm.py --config_path ./scenarios/tinytown/ev_tiny_town_config.xml --network_path ./scenarios/tinytown/tiny_town_network.xml --chargers_path ./scenarios/tinytown/tiny_town_chargers.xml --results_path ./python/algorithm_results --output_path ./scenarios/tinytown/output --alg_prefix mc --num_runs 50 --num_matsim_iters 5 --num_chargers 10 --min_ram 40 --max_ram 50
```
The above script shows how to run the algorithm, make sure to change whatever params you need. You can run the following to see the help.
```
python run_algorithm.py -h
```

## XML files

The MATsim simulator uses xml files to run the simulation and setup the configurations. In `scenarios/tinytown` you'll see the following xml files. The `monte_carlo_algorithm.py` file automatically references these files and updates them according to your parameters.

## MATSim

The MATsim simulator works by simulating plans for agents specified in the `tiny_town_plans.xml` file. Each iteration each agent will keep a memory of $m$ length, here $m$ = 5, and run a greedy epsilon algorithm where $\epsilon=0.2$, meaning there is a 20% probability the agent will explore a new path, and an 80% probability the agent will select the path with the maximum utility score from its memory. The MATsim simulator will run for `NUM_MATSIM_ITERS` iterations trying to maximize the following function, from the MATsim book.

![Utility Math1](./utilility_math1.png)
![Utility Math2](./matsimmath2.png)

To handle electric vehicles the utility has been modified to be 

$S_{plan}=\sum_{q=0}^{N-1}S_{act,q}+\sum_{q=0}^{N-1}(S_{trav,mode(q)}+100c)$

Where $0\leq c \leq1$ is the state of charge of the battery for each agent.