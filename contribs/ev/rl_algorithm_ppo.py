import gymnasium as gym
import evsim.envs
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback, CallbackList
import argparse
import os
from datetime import datetime
from pathlib import Path
from evsim.envs.matsim_graph_env import MatsimGraphEnv
import numpy as np
import torch


class TensorboardCallback(BaseCallback):
    """
    Custom callback for plotting additional values in tensorboard.
    """

    def __init__(self, verbose=0, save_dir=None):
        super(TensorboardCallback, self).__init__(verbose)
        self.save_dir = save_dir
        self.max_reward = -np.inf
        self.best_env: MatsimGraphEnv = None

    def _on_step(self) -> bool:
        avg_reward = 0

        for i, infos in enumerate(self.locals['infos']):
            env_inst: MatsimGraphEnv = infos['graph_env_inst']
            reward = env_inst.reward
            avg_reward += reward
            if reward > self.max_reward:
                self.max_reward = reward
                self.best_env = env_inst
                self.best_env.save_charger_config_to_csv(Path(self.save_dir, 'best_chargers.csv'))

        self.logger.record('Avg Reward', (avg_reward/(i+1)))
        self.logger.record('Best Reward', self.max_reward)

        return True


def main(args: argparse.Namespace):
    save_dir = f"{args.results_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}/"
    os.makedirs(save_dir)

    with open(Path(save_dir, 'args.txt'), 'w') as f:
        for key,val in args.__dict__.items():
            f.write(f"{key}:{val}\n")

    def make_env():
        return gym.make("MatsimGraphEnv-v0", config_path=args.matsim_config, num_agents=args.num_agents)

    env = SubprocVecEnv([make_env for _ in range(args.num_envs)])
    # n_steps: refers to the number of steps for each environment to collect data before
    # a batch is processed
    # batch_size: the amount of data that is sampled every n_steps from the replay buffer
    # total samples = num_envs * iterations
    tensorboard_callback = TensorboardCallback(save_dir=save_dir)
    checkpoint_callback = CheckpointCallback(save_freq=args.save_frequency, save_path=save_dir)
    callback = CallbackList([tensorboard_callback, checkpoint_callback])


    policy_kwargs = dict(net_arch=args.mlp_dims)

    if args.model_path:
        model = PPO.load(args.model_path,
                    env, 
                    n_steps=args.num_steps, 
                    verbose=1, 
                    device='cuda:0' if torch.cuda.is_available() else "cpu", 
                    tensorboard_log=save_dir,
                    batch_size=args.batch_size,
                    learning_rate=args.learning_rate,
                    policy_kwargs=policy_kwargs)
    else:
        model = PPO("MlpPolicy", 
                    env, 
                    n_steps=args.num_steps, 
                    verbose=1, 
                    device='cuda:0' if torch.cuda.is_available() else "cpu", 
                    tensorboard_log=save_dir,
                    batch_size=args.batch_size,
                    learning_rate=args.learning_rate,
                    clip_range=args.clip_range,
                    policy_kwargs=policy_kwargs)
    
    # total_timesteps = n_steps * num_envs * iterations
    model.learn(total_timesteps=args.num_timesteps, callback=callback)
    model.save(Path(save_dir, "ppo_matsim"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train a PPO model on the MatsimGraphEnv.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('matsim_config', type=str, help='path to the matsim config.xml file')
    parser.add_argument('--num_timesteps', type=int, default=1_000_000, help='The total number of timesteps to train, \
                        num_timesteps = n_steps * num_envs * iterations')
    parser.add_argument('--num_envs', type=int, default=100, help='Number of environments to run in parallel.')
    parser.add_argument('--num_agents', type=int, default=-1, help='The number of vehicles to simulate in the \
                        matsim simulator, if num_agents<0, then the current plans.xml and vehicles.xml file will\
                        be used and not updated')
    parser.add_argument('--mlp_dims', default='256 128 64' , help='Dimensions of the multi layer perception given as ints separated\
                        by spaces, can be any number of layers, the default has 3 layers')
    parser.add_argument('--results_dir', type=str, default=Path(Path(__file__).parent, 'ppo_results'), \
                        help='where to save tensorboard logs and model checkpoints.')
    parser.add_argument('--num_steps', type=int, default=1, help='the number of steps each environment takes before \
                        the policy and value function are updated')
    parser.add_argument('--batch_size', type=int, default=25, help='the number of samples PPO should pull from the \
                        replay buffer when updating the policy and value function')
    parser.add_argument('--learning_rate', type=float, default=0.00001, help='the learning rate for the optimizer, if \
                        you are running into errors where your actor is outputing nans from the mlp network\
                        then you probably need to  make this smaller')
    parser.add_argument('--model_path', default=None, help='path to the saved model.zip file if you saved your model previously\
                        and wish to keep training')
    parser.add_argument('--save_frequency', default=10000, help='how often to save the model weights')
    parser.add_argument('--clip_range', default=0.2, type=float, help='the clip range for the PPO algorithm')
    
    parser.print_help()
    args = parser.parse_args()
    args.mlp_dims = [int(x) for x in args.mlp_dims.split(' ')]

    main(args)





