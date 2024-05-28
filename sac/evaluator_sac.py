from copy import deepcopy
import numpy as np
import torch
from modt.evaluation import Evaluator

# yjyeh: todo...
class EvaluatorSAC(Evaluator):


    def evaluate_(self, preference, ind):
        episodes = 10
        returns = np.empty((episodes, self.reward_num))
        preference = np.array(preference)
        for i in range(episodes):
            state = self.env.reset()
            episode_reward = np.zeros(self.reward_num)
            done = False
            trace = []
            actions = []
            while not done:
                action = self.exploit(state, preference)
                trace.append(list(state))
                actions.append(list(action))
                next_state, reward, done, _ = self.env.step(action)
                episode_reward += reward
                state = next_state

            returns[i] = episode_reward
            print(episode_reward)
        mean_return = np.mean(returns, axis=0)

        batch = self.memory.sample(self.batch_size)
        p = torch.tensor(preference, device=self.device, dtype=torch.float32)
        with torch.no_grad():
            q1_loss, q2_loss, errors, mean_q1, mean_q2 = \
                self.calc_critic_loss(batch, 1, p, 0)
        # monitor.update(self.steps/self.eval_interval, np.dot(preference,mean_return), *mean_return, q1_loss.mean().item())

        path = os.path.join(self.log_dir, 'summary')
        tot_path = os.path.join(path, f'{ind}total_log.npy')
        reward_path = os.path.join(path, f'{ind}reward_log.npy')
        self.tot_t[ind].append(np.dot(preference, mean_return))
        self.reward_v[ind].append(mean_return)

        np.save(tot_path, np.array(self.tot_t[ind]))
        np.save(reward_path, np.array(self.reward_v[ind]))

        print('-' * 60)
        print(f'preference ', preference,
              f'Num steps: {self.steps:<5}  '
              f'reward:', mean_return)
        print('-' * 60)


    def __call__(self, model, target_return, target_pref, cur_step):
        model.eval()
        model.to(device=self.device)

        with torch.no_grad():
            init_target_return = deepcopy(target_return)
            init_target_pref = deepcopy(target_pref)
            
            # state_mean = torch.from_numpy(self.state_mean).to(device=self.device, dtype=torch.float32)
            # state_std = torch.from_numpy(self.state_std).to(device=self.device, dtype=torch.float32)
            seed = np.random.randint(0, 10000)
            self.eval_env.seed(seed) # fixed seeding in evaluation to visualize
            state_np = self.eval_env.reset()
            # self.state_dim = self.eval_env.observation_space.shape[0]
            #state_np = np.concatenate((state_np, np.tile(init_target_pref, self.concat_state_pref)), axis=0)
            state_tensor = torch.from_numpy(state_np).to(device=self.device, dtype=torch.float32).reshape(1, self.state_dim)
            # state_tensor = torch.clip((state_tensor - state_mean) / state_std, -10, 10)

            actions = []
            
            # running_target_return_np = deepcopy(target_return)
            # running_target_return_tensor = torch.tensor(running_target_return_np).to(device=self.device, dtype=torch.float32)
            # avg_target_return = torch.tensor(running_target_return_tensor / self.max_ep_len, device=self.device, dtype=torch.float32).reshape(1, self.rtg_dim)
            
            pref_np = np.array(target_pref)

            # this is the minimum rtg, we don't want rtg to go below 0
            episode_return, episode_length = 0, 0
            unweighted_raw_reward_cumulative = np.zeros(shape=(self.pref_dim), dtype=np.float32)
            cum_r_original = np.zeros(shape=(self.pref_dim), dtype=np.float32) # no scaling, no normalization
            for t in range(self.max_ep_len):

                action = model.exploit(state_tensor.to(dtype=torch.float32), init_target_pref)
                # action = model.get_action(
                #     state_tensor.to(dtype=torch.float32),
                #     avg_target_return.to(dtype=torch.float32)
                # )
                action = np.multiply(action, self.act_scale)
                actions.append(action)

                state_np, _, done, info = self.eval_env.step(action)
                raw_rewards = info['obj'] / self.scale
                if self.normalize_reward:
                    raw_rewards = (info['obj'] - self.min_each_obj_step) / (self.max_each_obj_step - self.min_each_obj_step) / self.scale


                #state_np = np.concatenate((state_np, np.tile(init_target_pref, self.concat_state_pref)), axis=0)
                state_tensor = torch.from_numpy(state_np).to(device=self.device, dtype=torch.float32).reshape(1, self.state_dim)
                # state_tensor = torch.clip((state_tensor - state_mean) / state_std, -10, 10)

                unweighted_raw_reward_cumulative += raw_rewards
                cum_r_original += info['obj']
                final_reward = np.dot(raw_rewards, pref_np)
                episode_return += final_reward
                episode_length += 1
                
                if episode_length == self.max_ep_len or done:
                    break


                # if self.rtg_dim == 1: # use final-rtg
                #     running_target_return_np -= np.dot(raw_rewards, pref_np)
                # else: # use multi-obj rtg (based on weighted value to align with MODT)
                #     running_target_return_np -= np.multiply(raw_rewards, pref_np)
                #
                # running_target_return_tensor = torch.tensor(running_target_return_np).to(device=self.device, dtype=torch.float32).reshape(1, self.rtg_dim)
                # avg_target_return = running_target_return_tensor / (self.max_ep_len - episode_length)


            target_ret_scaled_back = np.round(init_target_return * self.scale, 3) # this is normalized
            weighted_raw_reward_cumulative_eval = np.round(np.multiply(unweighted_raw_reward_cumulative * self.scale, init_target_pref), 3)
            unweighted_raw_return_cumulative_eval = np.round(unweighted_raw_reward_cumulative * self.scale, 3)
            total_return_scaled_back_eval = np.round(np.sum(weighted_raw_reward_cumulative_eval), 3)
            if not self.eval_only:
                log_file_name = f'{self.logsdir}/step={cur_step}.txt'
                with open(log_file_name, 'a') as f:
                    f.write(f"\ntarget return: {target_ret_scaled_back} ------------> {weighted_raw_reward_cumulative_eval}\n")
                    f.write(f"target pref: {np.round(init_target_pref, 3)} ------------> {np.round(unweighted_raw_return_cumulative_eval / np.sum(unweighted_raw_return_cumulative_eval), 3)}\n")
                    f.write(f"\tunweighted raw returns: {unweighted_raw_return_cumulative_eval}\n")
                    f.write(f"\tweighted raw return: {weighted_raw_reward_cumulative_eval}\n")
                    f.write(f"\tweighted final return: {total_return_scaled_back_eval}\n")
                    f.write(f"\tlength: {episode_length}\n")
            # self.decide_save_video(np.multiply(actions.detach().cpu().numpy(), self.act_scale), raw_rewards_cumulative, init_target_return, init_target_pref, seed)
            return episode_return, episode_length, unweighted_raw_reward_cumulative, weighted_raw_reward_cumulative_eval, cum_r_original