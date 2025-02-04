import gymnasium as gym
import evsim.envs
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
from stable_baselines3.common.callbacks import BaseCallback
import argparse
import os
from datetime import datetime
from pathlib import Path

class TensorboardCallback(BaseCallback):
    """
    Custom callback for plotting additional values in tensorboard.
    """

    def __init__(self, verbose=0):
        super(TensorboardCallback, self).__init__(verbose)

    def _on_step(self) -> bool:
        avg_reward = 0
        for i, infos in enumerate(self.locals['infos']):
            avg_reward += infos['reward']

        self.logger.record('Avg Reward', (avg_reward/(i+1)))
        return True


def main(args: argparse.Namespace):
    if not os.path.exists(args.results_dir):
        os.makedirs(args.results_dir)

    def make_env():
        return gym.make("MatsimGraphEnv-v0", config_path = args.matsim_config)

    env = SubprocVecEnv([make_env for _ in range(args.num_envs)])

    model = PPO("MlpPolicy", 
                env, 
                n_steps=1, 
                verbose=1, 
                device='cpu', 
                tensorboard_log=f"{args.results_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}/",
                batch_size=2,
                learning_rate=0.00001)

    model.learn(total_timesteps=10, callback=TensorboardCallback())
    model.save("ppo_matsim")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train a PPO model on the MatsimGraphEnv.')
    parser.add_argument('--num_envs', type=int, default=2, help='Number of environments to run in parallel.')
    parser.add_argument('--results_dir', type=str, default=Path(Path(__file__).parent, 'ppo_results'), \
                        help='where to save tensorboard logs and model checkpoints.')
    parser.add_argument('--matsim_config', type=str, help='path to the matsim config.xml file')

    args = parser.parse_args()

    main(args)