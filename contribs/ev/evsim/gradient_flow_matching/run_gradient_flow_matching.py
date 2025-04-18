import argparse
from evsim.gradient_flow_matching.flowsim_dataset import FlowSimDataset
from pathlib import Path
import os

def main(args):
    output_path = Path(args.results_path)
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    

    dataset = FlowSimDataset(output_path, args.network_path, args.counts_path, args.num_clusters)




if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("results_path", help="path to the output folder for the results of the algorithm")
    parser.add_argument("network_path", help="path to matsim xml network")
    parser.add_argument("counts_path", help="path to matsim xml counts")
    parser.add_argument("num_clusters", type=int, help="number of clusters for the network")
    args = parser.parse_args()
    main(args)