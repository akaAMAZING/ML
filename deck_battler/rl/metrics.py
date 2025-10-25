"""Lightweight metric helpers for reinforcement learning workflows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


def explained_variance(y_pred: Iterable[float], y_true: Iterable[float]) -> float:
    """Compute the explained variance between predictions and targets.

    Returns values in ``(-inf, 1]`` where ``1`` indicates perfect prediction and
    ``0`` matches the variance of the baseline that always predicts ``y_true``'s
    mean. ``nan`` inputs gracefully degrade to ``0`` so downstream consumers can
    rely on a numeric output during the very first iterations of training.
    """

    y_pred_arr = np.asarray(list(y_pred), dtype=np.float64)
    y_true_arr = np.asarray(list(y_true), dtype=np.float64)
    if y_pred_arr.size == 0 or y_true_arr.size == 0:
        return 0.0
    var_y = np.var(y_true_arr)
    if var_y == 0:
        return 0.0
    cov = np.var(y_true_arr - y_pred_arr)
    if np.isnan(cov):
        return 0.0
    return max(float(1.0 - cov / var_y), -1.0)


@dataclass
class UpdateMetrics:
    """Aggregated statistics captured for a single PPO update step."""

    actor_loss: float
    value_loss: float
    entropy: float
    approx_kl: float
    clip_fraction: float
    value_explained_variance: float

    def to_dict(self) -> dict[str, float]:
        return {
            "actor_loss": self.actor_loss,
            "value_loss": self.value_loss,
            "entropy": self.entropy,
            "approx_kl": self.approx_kl,
            "clip_fraction": self.clip_fraction,
            "value_explained_variance": self.value_explained_variance,
        }
