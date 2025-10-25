"""Strategic layer that offers branching decisions each round."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .artifacts import Artifact, pick_artifact
from .enums import Rarity, Sect

if TYPE_CHECKING:  # pragma: no cover
    from .player import PlayerState


@dataclass(frozen=True)
class StrategicOption:
    """Represents a single choice offered to the player."""

    id: str
    name: str
    description: str
    cost: int
    option_type: str
    payload: Dict[str, Any]

    def serialize(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "cost": self.cost,
            "type": self.option_type,
        }
        if "sect" in self.payload:
            data["sect"] = self.payload["sect"].value
        if "stat" in self.payload:
            data["stat"] = self.payload["stat"]
        if "duration" in self.payload:
            data["duration"] = self.payload["duration"]
        if "risk" in self.payload:
            data["risk"] = self.payload["risk"]
        if "success_chance" in self.payload:
            data["success_chance"] = self.payload["success_chance"]
        if "reward_value" in self.payload:
            data["reward_value"] = self.payload["reward_value"]
        if "rarity" in self.payload and isinstance(self.payload["rarity"], Rarity):
            data["rarity"] = self.payload["rarity"].name
        if "artifact" in self.payload:
            artifact = self.payload["artifact"]
            if isinstance(artifact, Artifact):
                data["artifact"] = {
                    "id": artifact.id,
                    "name": artifact.name,
                    "description": artifact.description,
                    "power": artifact.power,
                }
        return data


class StrategicPlanner:
    """Generates option sets with meaningful variety each round."""

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)

    def generate_options(
        self,
        player: "PlayerState",
        active_sects: List[Sect],
    ) -> List[StrategicOption]:
        candidates: List[StrategicOption] = []

        candidates.append(self._make_focus_option(active_sects, player))
        candidates.append(self._make_training_option(player, active_sects))
        candidates.append(self._make_expedition_option(player, active_sects))
        candidates.append(self._make_artifact_option(player))

        # Ensure consistent variety and shuffle for randomness.
        filtered = [option for option in candidates if option is not None]
        self.rng.shuffle(filtered)
        return filtered[:3]

    # ------------------------------------------------------------------
    # Option factory helpers
    # ------------------------------------------------------------------

    def _make_focus_option(
        self, active_sects: List[Sect], player: "PlayerState"
    ) -> StrategicOption:
        sect = self.rng.choice(active_sects)
        duration = 3 + (1 if sect not in player.focus_preferences else 0)
        return StrategicOption(
            id=f"focus_{sect.name.lower()}",
            name=f"{sect.value} Research Mission",
            description=f"Boost shop odds for {sect.value} units for multiple rounds.",
            cost=0,
            option_type="focus",
            payload={"sect": sect, "duration": duration},
        )

    def _make_training_option(
        self, player: "PlayerState", active_sects: List[Sect]
    ) -> StrategicOption:
        stat = self.rng.choice(["atk", "hp", "speed"])
        amount = {"atk": 6, "hp": 20, "speed": 0.25}[stat]
        # Prefer sects already represented but fall back to active pool.
        deck_sects = {unit.sect for unit in player.deck}
        if deck_sects:
            sect = self.rng.choice(list(deck_sects))
        else:
            sect = self.rng.choice(active_sects)
        return StrategicOption(
            id=f"training_{sect.name.lower()}_{stat}",
            name=f"Elite Drills: {sect.value}",
            description=f"Spend gold to grant {stat.upper()} bonuses to {sect.value} troops.",
            cost=4,
            option_type="training",
            payload={"sect": sect, "stat": stat, "amount": amount},
        )

    def _make_artifact_option(self, player: "PlayerState") -> StrategicOption:
        artifact = pick_artifact(self.rng, player.artifacts)
        return StrategicOption(
            id=f"artifact_{artifact.id}",
            name=f"Secure Artifact: {artifact.name}",
            description=f"Acquire the {artifact.name} for a persistent bonus.",
            cost=6,
            option_type="artifact",
            payload={"artifact": artifact},
        )

    def _make_expedition_option(
        self, player: "PlayerState", active_sects: List[Sect]
    ) -> StrategicOption:
        risk = self.rng.randint(4, 9)
        success_chance = 0.55 + len(player.artifacts) * 0.03
        success_chance = min(success_chance, 0.9)
        reward_type = self.rng.choice(["gold", "card", "training"])
        reward_value = 6 if reward_type == "gold" else 12 if reward_type == "training" else 0
        rarity = self.rng.choice([Rarity.RARE, Rarity.EPIC])
        sect = self.rng.choice(active_sects)
        return StrategicOption(
            id=f"expedition_{reward_type}_{sect.name.lower()}",
            name="Frontier Expedition",
            description=(
                "Risk HP to attempt a high-impact objective that could bring back gold,"
                " rare recruits or intense field training."
            ),
            cost=0,
            option_type="expedition",
            payload={
                "risk": risk,
                "success_chance": success_chance,
                "reward": reward_type,
                "reward_value": reward_value,
                "rarity": rarity,
                "sect": sect,
            },
        )

