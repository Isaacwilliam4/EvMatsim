"""
This script implements a reinforcement learning (RL) training pipeline using
the Proximal Policy Optimization (PPO) algorithm from the Stable-Baselines3
library. The training is performed on custom Matsim-based environments, which
can either use a Multi-Layer Perceptron (MLP) or a Graph Neural Network (GNN)
as the policy architecture.

The script supports parallelized environments, custom callbacks for
TensorBoard logging and checkpointing, and configurable hyperparameters for
training. It also allows resuming training from a previously saved model.

Classes:
    TensorboardCallback: A custom callback for logging additional metrics to
    TensorBoard, such as average and best rewards.

Functions:
    main(args): The main function that sets up the environment, initializes
    the PPO model, and starts the training process.

Command-line Arguments:
    matsim_config (str): Path to the MATSim configuration XML file.
    --num_timesteps (int): Total number of timesteps to train. Default is
    1,000,000.
    --num_envs (int): Number of environments to run in parallel. Default is
    100.
    --num_agents (int): Number of vehicles to simulate in MATSim. Default is
    -1 (use existing plans and vehicles).
    --mlp_dims (str): Dimensions of the MLP layers, specified as
    space-separated integers. Default is "256 128 64".
    --results_dir (str): Directory to save TensorBoard logs and model
    checkpoints. Default is "ppo_results".
    --num_steps (int): Number of steps each environment takes before updating
    the policy. Default is 1.
    --batch_size (int): Number of samples PPO pulls from the replay buffer for
    updates. Default is 25.
    --learning_rate (float): Learning rate for the optimizer. Default is
    0.00001.
    --model_path (str): Path to a previously saved model to resume training.
    Default is None.
    --save_frequency (int): Frequency (in timesteps) to save model weights.
    Default is 10,000.
    --clip_range (float): Clip range for the PPO algorithm. Default is 0.2.
    --policy_type (str): Type of policy to use ("MlpPolicy" or "GNNPolicy").
    Default is "MlpPolicy".

Usage:
    Run the script from the command line, providing the required arguments.
    For example:
        python rl_algorithm_ppo.py /path/to/matsim_config.xml --num_timesteps
        500000 --policy_type GNNPolicy
"""

import gymnasium as gym
import argparse
import os
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.callbacks import (
    BaseCallback,
    CheckpointCallback,
    CallbackList,
)
from datetime import datetime
from pathlib import Path
from evsim.envs.flowsim_env import FlowSimEnv
from multiprocessing import Manager

class TensorboardCallback(BaseCallback):
    """
    A custom callback for reinforcement learning algorithms that integrates
    with TensorBoard and tracks the performance of the environment.

    Attributes:
        save_dir (str or None): Directory path to save the best-performing
        environment's data.
        best_reward (float): The highest reward observed during training.
        best_env (FlowMatsimGraphEnv): The environment
        instance corresponding to the best reward.

    Methods:
        _on_step() -> bool:
            Executes at each step of the training process. Calculates average
            reward, updates the best reward and environment instance if a new
            best reward is observed, and logs metrics to TensorBoard.
    """

    def __init__(self, verbose=0, save_dir=None):
        """
        Initializes the TensorboardCallback.

        Args:
            verbose (int): Verbosity level.
            save_dir (str or None): Directory to save the best-performing
            environment's data.
        """
        super(TensorboardCallback, self).__init__(verbose)
        self.save_dir = save_dir
        self.best_reward = -np.inf
        self.best_env: FlowSimEnv = None

    def _on_step(self) -> bool:
        """
        Executes at each step of the training process. Logs average and best
        rewards to TensorBoard and saves the best-performing environment's
        data.

        Returns:
            bool: True to continue training.
        """
        avg_reward = 0

        for i, infos in enumerate(self.locals["infos"]):
            env_inst: FlowSimEnv = infos["graph_env_inst"]
            reward = env_inst.reward
            avg_reward += reward
            if reward > self.best_reward:
                self.best_env = env_inst
                self.best_reward = self.best_env.best_reward
                self.best_env.save_charger_config_to_csv(
                    Path(self.save_dir, "best_chargers.csv")
                )
                self.best_env.save_server_output(
                    self.best_env.best_output_response, "bestoutput"
                )

        self.logger.record("Avg Reward", (avg_reward / (i + 1)))
        self.logger.record("Best Reward", self.best_reward)

        return True


def main(args: argparse.Namespace):
    """
    Main function to set up the environment, initialize the PPO model, and
    start the training process.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
    """
    save_dir = f"{args.results_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}/"
    os.makedirs(save_dir)

    with open(Path(save_dir, "args.txt"), "w") as f:
        for key, val in args.__dict__.items():
            f.write(f"{key}:{val}\n")

    def make_env():
        """
        Creates a new environment instance based on the policy type.

        Returns:
            gym.Env: A new environment instance.
        """

        return gym.make(
            "FlowMatsimGraphEnvMlp-v0",
            config_path=args.matsim_config,
            num_agents=args.num_agents,
            save_dir=save_dir,
            max_extracted=args.max_extracted
        )

    env = SubprocVecEnv([make_env for _ in range(args.num_envs)])
    """
    n_steps: Number of steps for each environment to collect data before a 
    batch is processed.
    batch_size: Amount of data sampled every n_steps from the replay buffer. 
    Total samples = num_envs * iterations.

    The save frequency only accounts for the number of times each env has run, 
    so we divide it to save every args.save_frequency timesteps.
    """
    args.save_frequency //= args.num_envs

    tensorboard_callback = TensorboardCallback(save_dir=save_dir)
    checkpoint_callback = CheckpointCallback(
        save_freq=args.save_frequency, save_path=save_dir
    )
    callback = CallbackList([tensorboard_callback, checkpoint_callback])

    policy_kwargs = dict(max_extracted=args.max_extracted)

    if args.model_path:
        model = PPO.load(
            args.model_path,
            env,
            n_steps=args.num_steps,
            verbose=1,
            device="cuda:0" if torch.cuda.is_available() else "cpu",
            tensorboard_log=save_dir,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            policy_kwargs=policy_kwargs,
        )
    else:
        model = PPO(
            args.policy_type,
            env,
            n_steps=args.num_steps,
            verbose=1,
            device="cuda:0" if torch.cuda.is_available() else "cpu",
            tensorboard_log=save_dir,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            clip_range=args.clip_range,
            policy_kwargs=policy_kwargs,
        )

    # total_timesteps = n_steps * num_envs * iterations
    model.learn(total_timesteps=args.num_timesteps, callback=callback)
    model.save(Path(save_dir, "ppo_matsim"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train a PPO model on the FlowMatsimGraphEnv.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "matsim_config", type=str, help="Path to the matsim config.xml file."
    )
    parser.add_argument(
        "--num_timesteps",
        type=int,
        default=1_000_000,
        help="Total number of timesteps to train. \
                        num_timesteps = n_steps * num_envs * iterations.",
    )

    parser.add_argument(
        "--num_envs",
        type=int,
        default=100,
        help="Number of environments to run in parallel.",
    )
    parser.add_argument(
        "--num_agents",
        type=int,
        default=-1,
        help="Number of vehicles to simulate in the matsim simulator. If \
                        num_agents < 0, the current plans.xml and vehicles.xml \
                        files will be used and not updated.",
    )
    parser.add_argument(
        "--mlp_dims",
        default="256 128 64",
        help="Dimensions of the multi-layer perceptron given as space-separated \
                        integers. Can be any number of layers. Default has 3 \
                        layers.",
    )
    parser.add_argument(
        "--results_dir",
        type=str,
        default=Path(Path(__file__).parent, "ppo_results"),
        help="Directory to save TensorBoard logs and model checkpoints.",
    )
    parser.add_argument(
        "--num_steps",
        type=int,
        default=1,
        help="Number of steps each environment takes before the policy and \
                        value function are updated.",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=25,
        help="Number of samples PPO should pull from the replay buffer when \
                        updating the policy and value function.",
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=0.00001,
        help="Learning rate for the optimizer. If the actor outputs NaNs from \
                        the MLP network, reduce this value.",
    )
    parser.add_argument(
        "--model_path",
        default=None,
        help="Path to the saved model.zip file if you wish to resume training.",
    )
    parser.add_argument(
        "--save_frequency",
        type=int,
        default=10000,
        help="How often to save the model weights in total timesteps.",
    )
    parser.add_argument(
        "--clip_range",
        default=0.2,
        type=float,
        help="Clip range for the PPO algorithm.",
    )
    parser.add_argument(
        "--policy_type",
        default="MlpPolicy",
        choices=["MlpPolicy", "GNNPolicy", "FlowMlpPolicy"],
        type=str,
        help="The policy type to use for the PPO algorithm.",
    )
    parser.add_argument(
        "--max_extracted",
        default=50,
        type=int,
        help="The maximum number of nodes to consider for origin destination calculation",
    )

    parser.print_help()
    args = parser.parse_args()
    args.mlp_dims = [int(x) for x in args.mlp_dims.split(" ")]

    main(args)
