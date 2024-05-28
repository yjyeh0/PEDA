# from audioop import avg
# import numpy as np
import torch
from modt.training.trainer import Trainer


class SACTrainer(Trainer):

    def train_step(self):
        # states, pref, actions, rewards, next_states, dones  = self.get_batch()
        batch = self.get_batch()
        # states = torch.squeeze(states)
        # next_states = torch.squeeze(next_states)
        # actions = torch.squeeze(actions)
        # rewards = torch.squeeze(rewards)
        # if len(avg_rtg.shape) == 1:
        #     avg_rtg = torch.unsqueeze(avg_rtg, dim=-1)
        #
        # states = torch.cat((states, avg_rtg), dim=1)

        loss = self.model.training_step(
            batch  # doesn't matter in source code
        )
        # self.optimizer.zero_grad()
        # loss.backward()
        # self.optimizer.step()

        return loss.detach().cpu().item()