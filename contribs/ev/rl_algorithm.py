import gymnasium as gym
import evsim.envs
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv
import argparse

def main(args: argparse.Namespace):
    def make_env():
        return gym.make("MatsimGraphEnv-v0")

    env = SubprocVecEnv([make_env for _ in range(args.num_envs)])

    model = PPO("MlpPolicy", env, verbose=1, device='cpu')

    model.learn(total_timesteps=10)
    model.save("ppo_matsim")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train a PPO model on the MatsimGraphEnv.')
    parser.add_argument('--num_envs', type=int, default=10, help='Number of environments to run in parallel.')
    args = parser.parse_args()

    main(args)