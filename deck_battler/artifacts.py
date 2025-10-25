"""Definitions for strategic artifacts that grant persistent bonuses."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - for type checking only
    from .player import PlayerState


@dataclass(frozen=True)
class Artifact:
    """A long-term modifier that alters the player's economy or planning."""

    id: str
    name: str
    description: str
    power: int
    apply_effect: Callable[["PlayerState"], str]

    def apply(self, player: "PlayerState") -> str:
        """Apply the artifact to the player and return a flavor message."""

        return self.apply_effect(player)


def _treasury(player: "PlayerState") -> str:
    player.economy_bonus += 2
    return "+2 passive gold income each round."


def _clairvoyant_lens(player: "PlayerState") -> str:
    player.focus_duration_bonus += 1
    return "Focus choices last longer and have stronger weight."


def _war_college(player: "PlayerState") -> str:
    player.training_bonus += 2
    return "Training drills empower units with +2 additional stats."


def _trailblazer_compass(player: "PlayerState") -> str:
    player.reroll_discount = min(player.reroll_discount + 1, 3)
    return "Rerolls are discounted by 1 gold (stacking up to 3)."


def _aegis_banner(player: "PlayerState") -> str:
    player.expedition_safety += 2
    return "Expedition risks are reduced thanks to defensive scouting."


ARTIFACTS: Sequence[Artifact] = (
    Artifact(
        id="golden_treasury",
        name="Golden Treasury",
        description="Gain +2 passive gold income every round.",
        power=3,
        apply_effect=_treasury,
    ),
    Artifact(
        id="clairvoyant_lens",
        name="Clairvoyant Lens",
        description="Focus decisions persist an extra round and weigh more heavily.",
        power=2,
        apply_effect=_clairvoyant_lens,
    ),
    Artifact(
        id="war_college",
        name="War College",
        description="Training drills grant +2 additional stats to affected units.",
        power=3,
        apply_effect=_war_college,
    ),
    Artifact(
        id="trailblazer_compass",
        name="Trailblazer Compass",
        description="Rerolls cost 1 less gold (up to 3 stacks).",
        power=2,
        apply_effect=_trailblazer_compass,
    ),
    Artifact(
        id="aegis_banner",
        name="Aegis Banner",
        description="Reduce the damage suffered on failed expeditions.",
        power=2,
        apply_effect=_aegis_banner,
    ),
)

ARTIFACT_INDEX: Dict[str, Artifact] = {artifact.id: artifact for artifact in ARTIFACTS}


def pick_artifact(rng: random.Random, owned: Sequence[str]) -> Artifact:
    """Select an artifact, avoiding duplicates when possible."""

    available: List[Artifact] = [
        artifact for artifact in ARTIFACTS if artifact.id not in owned
    ]
    pool = available or list(ARTIFACTS)
    return rng.choice(pool)

