import gymnasium as gym
import evsim.envs
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.callbacks import BaseCallback
import argparse
import os
from datetime import datetime
from pathlib import Path
from evsim.envs.matsim_graph_env import MatsimGraphEnv
import numpy as np

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
    if not os.path.exists(args.results_dir):
        os.makedirs(args.results_dir)

    save_dir = f"{args.results_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}/"

    def make_env():
        return gym.make("MatsimGraphEnv-v0", config_path=args.matsim_config, num_agents=1000)

    env = SubprocVecEnv([make_env for _ in range(args.num_envs)])
    # n_steps: refers to the number of steps for each environment to collect data before
    # a batch is processed
    # batch_size: the amount of data that is sampled every n_steps from the replay buffer
    # total samples = num_envs * iterations
    policy_kwargs = dict(net_arch=[2048, 1024, 512])

    model = PPO("MlpPolicy", 
                env, 
                n_steps=1, 
                verbose=1, 
                device='cuda:0', 
                tensorboard_log=save_dir,
                batch_size=5,
                learning_rate=0.000001,
                policy_kwargs=policy_kwargs)
    
    # total_timesteps = n_steps * num_envs * iterations
    model.learn(total_timesteps=10000, callback=TensorboardCallback(save_dir=save_dir))
    model.save(Path(args.results_dir, "ppo_matsim"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train a PPO model on the MatsimGraphEnv.')
    parser.add_argument('--num_envs', type=int, default=10, help='Number of environments to run in parallel.')
    parser.add_argument('--results_dir', type=str, default=Path(Path(__file__).parent, 'ppo_results'), \
                        help='where to save tensorboard logs and model checkpoints.')
    parser.add_argument('--matsim_config', type=str, help='path to the matsim config.xml file')

    args = parser.parse_args()

    main(args)