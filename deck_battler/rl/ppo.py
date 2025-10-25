"""Proximal Policy Optimisation trainer for Deck Battler."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import torch
from torch import Tensor, nn
from torch.distributions import Categorical
from torch.optim import Adam
from tqdm import trange

from .env import DeckBattlerEnv


@dataclass
class PPOConfig:
    """Hyper-parameters that control the PPO training loop."""

    rollout_steps: int = 2048
    minibatch_size: int = 256
    update_epochs: int = 10
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    learning_rate: float = 3e-4
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 0.5
    total_updates: int = 500
    device: str = "cpu"


class ActorCritic(nn.Module):
    """Shared backbone with separate policy and value heads."""

    def __init__(self, obs_dim: int, action_dim: int) -> None:
        super().__init__()
        hidden = 256
        self.backbone = nn.Sequential(
            nn.Linear(obs_dim, hidden),
            nn.LayerNorm(hidden),
            nn.Tanh(),
            nn.Linear(hidden, hidden),
            nn.Tanh(),
        )
        self.policy_head = nn.Linear(hidden, action_dim)
        self.value_head = nn.Linear(hidden, 1)

    def forward(self, obs: Tensor) -> Tuple[Tensor, Tensor]:
        x = self.backbone(obs)
        logits = self.policy_head(x)
        value = self.value_head(x)
        return logits, value.squeeze(-1)

    def act(self, obs: Tensor, mask: Tensor) -> Tuple[Tensor, Tensor, Tensor]:
        logits, value = self.forward(obs)
        masked_logits = logits.masked_fill(~mask, -1e9)
        dist = Categorical(logits=masked_logits)
        action = dist.sample()
        log_prob = dist.log_prob(action)
        return action, log_prob, value

    def evaluate_actions(
        self, obs: Tensor, mask: Tensor, actions: Tensor
    ) -> Tuple[Tensor, Tensor, Tensor]:
        logits, value = self.forward(obs)
        masked_logits = logits.masked_fill(~mask, -1e9)
        dist = Categorical(logits=masked_logits)
        log_prob = dist.log_prob(actions)
        entropy = dist.entropy()
        return log_prob, entropy, value


class PPOTrainer:
    """End-to-end PPO trainer with action masking support."""

    def __init__(self, env: DeckBattlerEnv, config: Optional[PPOConfig] = None) -> None:
        self.env = env
        self.config = config or PPOConfig()
        self.device = torch.device(self.config.device)

        obs_dim = int(np.prod(env.observation_space.shape))
        action_dim = env.action_space.n
        self.policy = ActorCritic(obs_dim, action_dim).to(self.device)
        self.optimizer = Adam(self.policy.parameters(), lr=self.config.learning_rate)

        self.training_returns: List[float] = []
        self.training_lengths: List[int] = []

    def train(self, total_updates: Optional[int] = None, *, progress_bar: bool = True) -> None:
        updates = total_updates or self.config.total_updates
        obs, info = self.env.reset()
        mask = info["action_mask"].astype(bool)
        last_done = False

        iterator: Iterable[int]
        update_desc = None
        if progress_bar:
            tqdm_iter = trange(updates)
            iterator = tqdm_iter
            update_desc = tqdm_iter.set_description
        else:
            iterator = range(updates)

        for _ in iterator:
            batch = self._collect_rollout(obs, mask)
            obs = batch["next_obs"]
            mask = batch["next_mask"]
            last_done = batch["next_done"]
            self._update_policy(batch)

            if update_desc:
                mean_return = np.mean(self.training_returns[-10:]) if self.training_returns else 0.0
                update_desc(f"Return {mean_return: .2f}")

        if last_done:
            self.env.reset()

    # ------------------------------------------------------------------
    # Data collection
    # ------------------------------------------------------------------

    def _collect_rollout(self, start_obs: np.ndarray, start_mask: np.ndarray) -> Dict[str, object]:
        obs_list: List[np.ndarray] = []
        action_list: List[int] = []
        log_prob_list: List[float] = []
        reward_list: List[float] = []
        value_list: List[float] = []
        done_list: List[bool] = []
        mask_list: List[np.ndarray] = []

        obs = start_obs.copy()
        mask = start_mask.copy()
        episode_return = 0.0
        episode_length = 0
        last_done = False

        for _ in range(self.config.rollout_steps):
            obs_tensor = torch.tensor(obs, dtype=torch.float32, device=self.device)
            mask_tensor = torch.tensor(mask, dtype=torch.bool, device=self.device)
            with torch.no_grad():
                action_tensor, log_prob_tensor, value_tensor = self.policy.act(obs_tensor, mask_tensor)
            action = int(action_tensor.item())

            next_obs, reward, terminated, truncated, info = self.env.step(action)
            next_mask = info.get("action_mask")
            if next_mask is None:
                next_mask = np.ones(self.env.action_space.n, dtype=np.int8)
            next_mask = next_mask.astype(bool)

            obs_list.append(obs.copy())
            action_list.append(action)
            log_prob_list.append(float(log_prob_tensor.item()))
            reward_list.append(float(reward))
            value_list.append(float(value_tensor.item()))
            done = terminated or truncated
            done_list.append(done)
            mask_list.append(mask.copy())

            obs = next_obs
            mask = next_mask
            episode_return += reward
            episode_length += 1
            last_done = done

            if done:
                self.training_returns.append(episode_return)
                self.training_lengths.append(episode_length)
                episode_return = 0.0
                episode_length = 0
                obs, info = self.env.reset()
                mask = info["action_mask"].astype(bool)

        obs_tensor = torch.tensor(obs, dtype=torch.float32, device=self.device)
        mask_tensor = torch.tensor(mask, dtype=torch.bool, device=self.device)
        with torch.no_grad():
            _, _, next_value_tensor = self.policy.act(obs_tensor, mask_tensor)
        next_value = float(next_value_tensor.item())

        advantages, returns = self._compute_gae(
            rewards=reward_list,
            values=value_list,
            dones=done_list,
            next_value=next_value,
        )

        batch = {
            "obs": np.stack(obs_list),
            "actions": np.asarray(action_list, dtype=np.int64),
            "log_probs": np.asarray(log_prob_list, dtype=np.float32),
            "values": np.asarray(value_list, dtype=np.float32),
            "advantages": advantages,
            "returns": returns,
            "masks": np.stack(mask_list),
            "next_obs": obs.copy(),
            "next_mask": mask.copy(),
            "next_done": last_done,
        }
        return batch

    def _compute_gae(
        self,
        *,
        rewards: List[float],
        values: List[float],
        dones: List[bool],
        next_value: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        advantages = np.zeros(len(rewards), dtype=np.float32)
        gae = 0.0
        values_ext = values + [next_value]
        for step in reversed(range(len(rewards))):
            mask = 1.0 - float(dones[step])
            delta = rewards[step] + self.config.gamma * values_ext[step + 1] * mask - values_ext[step]
            gae = delta + self.config.gamma * self.config.gae_lambda * mask * gae
            advantages[step] = gae
        returns = advantages + np.asarray(values, dtype=np.float32)
        return advantages, returns

    # ------------------------------------------------------------------
    # Optimisation step
    # ------------------------------------------------------------------

    def _update_policy(self, batch: Dict[str, object]) -> None:
        obs = torch.tensor(batch["obs"], dtype=torch.float32, device=self.device)
        actions = torch.tensor(batch["actions"], dtype=torch.int64, device=self.device)
        old_log_probs = torch.tensor(batch["log_probs"], dtype=torch.float32, device=self.device)
        returns = torch.tensor(batch["returns"], dtype=torch.float32, device=self.device)
        advantages = torch.tensor(batch["advantages"], dtype=torch.float32, device=self.device)
        masks = torch.tensor(batch["masks"], dtype=torch.bool, device=self.device)

        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        batch_size = obs.shape[0]

        for _ in range(self.config.update_epochs):
            indices = torch.randperm(batch_size, device=self.device)
            for start in range(0, batch_size, self.config.minibatch_size):
                end = start + self.config.minibatch_size
                mb_idx = indices[start:end]

                mb_obs = obs[mb_idx]
                mb_actions = actions[mb_idx]
                mb_old_log_probs = old_log_probs[mb_idx]
                mb_returns = returns[mb_idx]
                mb_advantages = advantages[mb_idx]
                mb_masks = masks[mb_idx]

                new_log_probs, entropy, values = self.policy.evaluate_actions(
                    mb_obs, mb_masks, mb_actions
                )

                ratio = (new_log_probs - mb_old_log_probs).exp()
                surrogate_1 = ratio * mb_advantages
                surrogate_2 = torch.clamp(
                    ratio, 1.0 - self.config.clip_range, 1.0 + self.config.clip_range
                ) * mb_advantages
                actor_loss = -torch.min(surrogate_1, surrogate_2).mean()

                value_loss = (mb_returns - values).pow(2).mean()
                entropy_loss = entropy.mean()

                loss = (
                    actor_loss
                    + self.config.value_coef * value_loss
                    - self.config.entropy_coef * entropy_loss
                )

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.policy.parameters(), self.config.max_grad_norm)
                self.optimizer.step()

    # ------------------------------------------------------------------
    # Evaluation helpers
    # ------------------------------------------------------------------

    def evaluate(self, episodes: int = 10) -> Dict[str, float]:
        returns: List[float] = []
        lengths: List[int] = []
        obs, info = self.env.reset()
        mask = info["action_mask"].astype(bool)

        for _ in range(episodes):
            done = False
            episode_return = 0.0
            episode_length = 0
            while not done:
                obs_tensor = torch.tensor(obs, dtype=torch.float32, device=self.device)
                mask_tensor = torch.tensor(mask, dtype=torch.bool, device=self.device)
                with torch.no_grad():
                    action_tensor, _, _ = self.policy.act(obs_tensor, mask_tensor)
                action = int(action_tensor.item())
                obs, reward, terminated, truncated, info = self.env.step(action)
                mask = info.get("action_mask", np.ones(self.env.action_space.n, dtype=np.int8)).astype(bool)
                done = terminated or truncated
                episode_return += reward
                episode_length += 1
                if done:
                    returns.append(episode_return)
                    lengths.append(episode_length)
                    obs, info = self.env.reset()
                    mask = info["action_mask"].astype(bool)

        return {
            "mean_return": float(np.mean(returns) if returns else 0.0),
            "mean_length": float(np.mean(lengths) if lengths else 0.0),
        }

    def save(self, path: str) -> None:
        torch.save(self.policy.state_dict(), path)

    def load(self, path: str) -> None:
        state_dict = torch.load(path, map_location=self.device)
        self.policy.load_state_dict(state_dict)
