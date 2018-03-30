
from torch_rl.envs.wrappers import *
import gym

# Use Monitor to write the environment rewards to file
from gym.wrappers import Monitor

# Actor-critic model to be used in training with PPO
from torch_rl.models.ppo import ActorCriticPPO
# Trainer with PPO training algorithm
from torch_rl.training.ppo import GPUPPOTrainer
from torch_rl.utils import *

# Use for logging in training
from torch_rl.utils import logger

# Use for logging of moving average episode rewards to console
from torch_rl.envs import EnvLogger
import sys

logger.configure(clear=False)
monitor = Monitor(EnvLogger(NormalisedActionsWrapper(gym.make("Pendulum-v0"))), directory="./stats", force=True, 
    video_callable=False, write_upon_reset=True)
env = BaselinesNormalize(monitor)
print(env.observation_space.shape)


with tor.cuda.device(1):
    network = ActorCriticPPO([env.observation_space.shape[0], 64, 64, env.action_space.shape[0]])
    network.apply(gauss_init(0, np.sqrt(2)))

    trainer = GPUPPOTrainer(network=network, env=env, n_update_steps=4, n_steps=40)
    trainer.train(horizon=100000, max_episode_len=500)

