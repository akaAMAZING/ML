"""Core enumerations used across the Deck Battler engine."""
from __future__ import annotations

from enum import Enum, auto


class Sect(Enum):
    """Factions that cards belong to."""

    IRON = "Iron"
    SHADOW = "Shadow"
    CELESTIAL = "Celestial"
    INFERNAL = "Infernal"
    NATURE = "Nature"
    ARCANE = "Arcane"


class Rarity(Enum):
    """Card rarities determine shop odds and cost."""

    COMMON = ("Grey", 1, 3)
    UNCOMMON = ("Green", 2, 3)
    RARE = ("Blue", 3, 4)
    EPIC = ("Purple", 4, 5)
    LEGENDARY = ("Orange", 5, 6)

    def __init__(self, color: str, tier: int, base_cost: int) -> None:
        self.color = color
        self.tier = tier
        self.base_cost = base_cost


class CardType(Enum):
    """Types of cards that can appear in the shop."""

    UNIT = auto()
    TALENT = auto()
    SUPPRESSION = auto()


class TriggerType(Enum):
    """When abilities are triggered during a fight."""

    ON_DEPLOY = auto()
    COMBAT_START = auto()
    ON_ATTACK = auto()
    ON_DAMAGED = auto()
    ON_DEATH = auto()
    ON_KILL = auto()
    EVERY_TICK = auto()
    HP_THRESHOLD = auto()


class StatusEffect(Enum):
    """Timed effects that can be present on a unit."""

    BURN = auto()
    POISON = auto()
    SHIELD = auto()
    STUN = auto()
    BUFF_ATK = auto()
    BUFF_DEF = auto()
    DEBUFF_ATK = auto()
    DEBUFF_DEF = auto()
