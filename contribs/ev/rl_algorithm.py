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
SAVE_DIR = ''

class TensorboardCallback(BaseCallback):
    """
    Custom callback for plotting additional values in tensorboard.
    """

    def __init__(self, verbose=0):
        super(TensorboardCallback, self).__init__(verbose)

    def _on_step(self) -> bool:
        best_env: MatsimGraphEnv = None
        max_reward = 0
        avg_reward = 0

        for i, infos in enumerate(self.locals['infos']):
            env_inst: MatsimGraphEnv = infos['graph_env_list']
            reward = env_inst.reward
            avg_reward += reward
            if reward > max_reward:
                max_reward = reward
                best_env = env_inst

        best_env.dataset.save_charger_config_to_csv(Path(SAVE_DIR, 'chargers.csv'))
        self.logger.record('Avg Reward', (avg_reward/(i+1)))
        return True


def main(args: argparse.Namespace):
    if not os.path.exists(args.results_dir):
        os.makedirs(args.results_dir)

    SAVE_DIR = f"{args.results_dir}/{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}/"

    def make_env():
        return gym.make("MatsimGraphEnv-v0", config_path = args.matsim_config)

    env = SubprocVecEnv([make_env for _ in range(args.num_envs)])
    # n_steps: refers to the number of steps for each environment to collect data before
    # a batch is processed
    # batch_size: the amount of data that is sampled every n_steps from the replay buffer
    model = PPO("MlpPolicy", 
                env, 
                n_steps=1, 
                verbose=1, 
                device='cpu', 
                tensorboard_log=SAVE_DIR,
                batch_size=2,
                learning_rate=0.00001)
    
    # total_timesteps = n_steps * num_envs * iterations
    model.learn(total_timesteps=10, callback=TensorboardCallback())
    model.save(Path(args.results_dir, "ppo_matsim"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train a PPO model on the MatsimGraphEnv.')
    parser.add_argument('--num_envs', type=int, default=2, help='Number of environments to run in parallel.')
    parser.add_argument('--results_dir', type=str, default=Path(Path(__file__).parent, 'ppo_results'), \
                        help='where to save tensorboard logs and model checkpoints.')
    parser.add_argument('--matsim_config', type=str, help='path to the matsim config.xml file')

    args = parser.parse_args()

    main(args)