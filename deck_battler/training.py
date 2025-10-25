"""High level helpers for running PPO training for Deck Battler."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .rl import (
    DeckBattlerEnv,
    PPOConfig,
    PPOTrainer,
    RewardConfig,
    ScriptedOpponent,
)
from .rl.metrics import UpdateMetrics


@dataclass
class TrainingReport:
    """Summary statistics returned after a training run."""

    config: PPOConfig
    total_updates: int
    mean_return: float
    mean_length: float
    history: list[float] = field(default_factory=list)
    update_metrics: list[UpdateMetrics] = field(default_factory=list)


class RLTrainingSession:
    """Orchestrates environment creation and PPO training."""

    def __init__(
        self,
        *,
        config: Optional[PPOConfig] = None,
        reward_config: Optional[RewardConfig] = None,
        opponent: Optional[ScriptedOpponent] = None,
        env_kwargs: Optional[Dict] = None,
    ) -> None:
        env_kwargs = dict(env_kwargs or {})
        opponent = opponent or ScriptedOpponent()
        env = DeckBattlerEnv(
            opponent=opponent,
            reward_config=reward_config,
            **env_kwargs,
        )
        self.env = env
        self.trainer = PPOTrainer(env, config=config)

    def train(self, total_updates: Optional[int] = None, *, progress_bar: bool = True) -> TrainingReport:
        self.trainer.train(total_updates=total_updates, progress_bar=progress_bar)
        metrics = self.trainer.evaluate(episodes=10)
        return TrainingReport(
            config=self.trainer.config,
            total_updates=total_updates or self.trainer.config.total_updates,
            mean_return=metrics["mean_return"],
            mean_length=metrics["mean_length"],
            history=list(self.trainer.training_returns),
            update_metrics=list(self.trainer.update_metrics),
        )

    def save(self, path: str) -> None:
        self.trainer.save(path)

    def load(self, path: str) -> None:
        self.trainer.load(path)
