
from torch_rl.envs.wrappers import *
import gym

# Use Monitor to write the environment rewards to file
from gym.wrappers import Monitor

# Actor-critic model to be used in training with PPO
from torch_rl.models.ppo import ActorCriticPPO
from torch_rl.models.core import QNetwork

# Trainer with PPO training algorithm
from torch_rl.training.ipgppo import IPGGPUPPOTrainer
from torch_rl.utils import *
from torch_rl.utils import xavier_uniform_init
from torch_rl.memory import GeneralisedHindsightMemory

# Use for logging of moving average episode rewards to console
from torch_rl.envs import EnvLogger, GoalEnv
from torch_rl import config

import sys
import os
import roboschool

env_name = 'TRLRoboschoolReacher-v1'
# Interpolation parameter v * ppo_gradient + (1-v) * off_policy_gradient
v = 0.01
hindsight = True
sparse = True

np.random.seed(456)
tor.manual_seed(456)
goal_indices = [0,1]
precision = 1e-1

root_dir = 'torch_rl_her_ipgppo_' + env_name.lower().split("-")[0]
if sparse:
  root_dir += '_sparse'

if hindsight:
  root_dir += '_hindsight'


config.set_root(root_dir, force=True)
config.configure_logging(clear=False, output_formats=['tensorboard', 'stdout', 'json'])
replay_memory = GeneralisedHindsightMemory(limit=1000000, goal_indices=goal_indices) if hindsight else SequentialMemory(limit=1000000)

# config.start_tensorboard()

monitor = Monitor(EnvLogger(NormalisedActionsWrapper(gym.make(env_name))), 
    directory=os.path.join(config.root_path(), 'stats'), force=True, 
    video_callable=False, write_upon_reset=True)
env = RunningMeanStdNormalize(monitor)
env = GoalEnv(env, target_indices=goal_indices, curr_indices=[2,3], sparse=sparse, precision=precision)

num_observations = env.observation_space.shape[0]
num_actions = env.action_space.shape[0]

print('Action shape: ', num_actions, 'Observation shape: ', num_observations)

tanh, relu = tor.nn.Tanh(), tor.nn.ReLU()


tt = to_tensor

with tor.cuda.device(1):
    network = ActorCriticPPO([env.observation_space.shape[0], 64, 64, env.action_space.shape[0]])
    network.apply(xavier_uniform_init())

    # The Q network should be proportional in size to the policy, because the deteministic gradient becomes too big 
    critic = cuda_if_available(
    QNetwork(architecture=[num_observations + num_actions, 64, 64, 1],
                  activation_functions=[tanh, tanh, tanh]))
    critic.apply(xavier_uniform_init())
    
    # q = critic(tt(np.random.normal(0,1, num_observations).reshape(1,-1)), tt(np.random.normal(0,1, num_actions).reshape(1,-1)))
    # print(q)

    # sys.exit(1)


    trainer = IPGGPUPPOTrainer(policy_network=network, critic_network=critic, env=env, n_update_steps=5, 
        n_steps=2048, n_minibatches=32, lmda=.95, gamma=.99, lr=3e-4, epsilon=0.2, ent_coef=0.0,
        tau=100e-3, v=v, replay_memory=replay_memory)
    trainer.train(horizon=100000, max_episode_len=500)

