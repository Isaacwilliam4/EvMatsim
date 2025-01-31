import gymnasium as gym
import evsim.envs
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv

def main():
    num_envs = 2

    def make_env():
        return gym.make("MatsimGraphEnv-v0")

    # Create a vectorized environment with 4 parallel environments
    env = SubprocVecEnv([make_env for _ in range(num_envs)])

    # Instantiate the PPO agent
    model = PPO("MlpPolicy", env, verbose=1, device='cpu')

    # Train the agent
    model.learn(total_timesteps=10)
    model.save("ppo_matsim")

if __name__ == "__main__":
    main()