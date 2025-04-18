import argparse
from evsim.gradient_flow_matching.flowsim_dataset import FlowSimDataset
from pathlib import Path
import os
import torch

def main(args):
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    output_path = Path(args.results_path)
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    dataset = FlowSimDataset(output_path, args.network_path, args.counts_path, args.num_clusters)
    Z_2 = args.num_clusters**2
    TAM = torch.from_numpy(dataset.TAM).to(device).to(torch.float32)
    W = torch.rand(Z_2, 24).to(device).to(torch.float32)
    #TAM (|E|, Z^2)
    TAM = TAM.reshape(-1, Z_2)
    TARGET = dataset.target_graph.edge_attr.to(device)

    optimizer = torch.optim.Adam([W], lr=0.01)

    for step in range(args.training_steps):
        optimizer.zero_grad()
        R = torch.matmul(TAM, W)
        loss = torch.nn.functional.mse_loss(R, TARGET)
        loss.backward()
        optimizer.step()

        if step % 10 == 0:
            print(f"Step: {step}, loss: {loss.item()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("results_path", help="path to the output folder for the results of the algorithm")
    parser.add_argument("network_path", help="path to matsim xml network")
    parser.add_argument("counts_path", help="path to matsim xml counts")
    parser.add_argument("num_clusters", type=int, help="number of clusters for the network")
    parser.add_argument("--training_steps", type=int, default=1000)
    args = parser.parse_args()
    main(args)