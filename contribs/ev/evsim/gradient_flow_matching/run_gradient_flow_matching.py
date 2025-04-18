import argparse
from evsim.gradient_flow_matching.flowsim_dataset import FlowSimDataset
from pathlib import Path
import os
import torch
from torch.utils.tensorboard import SummaryWriter
import datetime
from tqdm import tqdm
import os

def main(args):
    
    current_time = datetime.datetime.now()
    unique_time_string = current_time.strftime("%Y%m%d%H%M%S%f")
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    output_path = Path(args.results_path)
    save_path = Path(output_path, unique_time_string)
    tensorboard_path = Path(save_path, "logs")
    os.makedirs(tensorboard_path)

    writer = SummaryWriter(tensorboard_path)

    with open(Path(save_path, "args.txt"), "w") as f:
        for key,val  in args.__dict__.items():
            f.write(f"{key}:{val}\n")

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    dataset = FlowSimDataset(output_path, args.network_path, args.counts_path, args.num_clusters)
    dataset.save_clusters(Path(save_path, "clusters.txt"))
    Z_2 = args.num_clusters**2
    TAM = torch.from_numpy(dataset.TAM).to(device).to(torch.float32)
    W = torch.rand(Z_2, 24).to(device).to(torch.float32)
    W.requires_grad = True
    #TAM (|E|, Z^2)
    TAM = TAM.reshape(-1, Z_2)
    TARGET = dataset.target_graph.edge_attr.to(device).to(torch.float32)

    optimizer = torch.optim.Adam([W], lr=0.1)
    pbar = tqdm(range(args.training_steps))

    for step in pbar:
        optimizer.zero_grad()
        R = torch.matmul(TAM, W)
        loss = torch.nn.functional.mse_loss(R, TARGET)
        loss.backward()
        optimizer.step()

        if step % args.log_interval == 0:
            pbar.set_description(f"Loss: {loss.item()}")
            writer.add_scalar("loss", loss.item(), step)


        if step % args.save_interval == 0:
            torch.save(W, Path(save_path, f"flows_step_{step}.pt"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("results_path", help="path to the output folder for the results of the algorithm")
    parser.add_argument("network_path", help="path to matsim xml network")
    parser.add_argument("counts_path", help="path to matsim xml counts")
    parser.add_argument("num_clusters", type=int, help="number of clusters for the network")
    parser.add_argument("--training_steps", type=int, default=1_000_000)
    parser.add_argument("--log_interval", type=int, default=1000)
    parser.add_argument("--save_interval", type=int, default=100_000)
    args = parser.parse_args()
    main(args)