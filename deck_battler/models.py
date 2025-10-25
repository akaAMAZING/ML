"""Dataclasses and helpers that describe cards, units and abilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from .enums import CardType, Rarity, Sect, StatusEffect, TriggerType

AbilityEffect = Callable[["Unit", "CombatContext"], None]


@dataclass
class Ability:
    """Description of an ability attached to a unit."""

    name: str
    trigger: TriggerType
    effect: AbilityEffect
    cooldown: float = 0.0
    threshold: float = 0.0
    description: str = ""

    def __post_init__(self) -> None:
        self.current_cooldown = 0.0


@dataclass
class Unit:
    """Runtime representation of a unit on the battlefield."""

    name: str
    sect: Sect
    rarity: Rarity
    hp: float
    max_hp: float
    atk: float
    defense: float
    speed: float
    abilities: list[Ability] = field(default_factory=list)
    status_effects: Dict[StatusEffect, float] = field(default_factory=dict)
    star_level: int = 1

    is_alive: bool = True
    damage_dealt: float = 0.0
    damage_taken: float = 0.0
    kills: int = 0

    base_hp: float = field(init=False)
    base_max_hp: float = field(init=False)
    base_atk: float = field(init=False)
    base_defense: float = field(init=False)
    base_speed: float = field(init=False)

    def __post_init__(self) -> None:
        multiplier = 1.0 + (self.star_level - 1) * 0.5
        self.base_hp = self.hp / multiplier if multiplier else self.hp
        self.base_max_hp = self.max_hp / multiplier if multiplier else self.max_hp
        self.base_atk = self.atk / multiplier if multiplier else self.atk
        self.base_defense = self.defense / multiplier if multiplier else self.defense
        self.base_speed = self.speed
        self._apply_star_scaling()

    def take_damage(self, damage: float) -> float:
        if damage < 0:
            self.heal(-damage)
            return 0.0
        mitigated = max(0.0, damage - self.defense * 0.5)
        self.hp -= mitigated
        self.damage_taken += mitigated
        if self.hp <= 0:
            self.is_alive = False
            self.hp = 0
        return mitigated

    def heal(self, amount: float) -> None:
        self.hp = min(self.max_hp, self.hp + amount)

    def apply_status(self, status: StatusEffect, duration: float) -> None:
        self.status_effects[status] = max(duration, self.status_effects.get(status, 0.0))

    def copy(self) -> "Unit":
        from copy import deepcopy

        return deepcopy(self)

    def promote(self) -> None:
        """Increase the star level of the unit and rescale its stats."""
        self.star_level += 1
        self._apply_star_scaling()
        self.refresh_state()

    def refresh_state(self) -> None:
        """Reset transient combat fields such as health, statuses and counters."""
        self.hp = self.max_hp
        self.is_alive = True
        self.status_effects.clear()
        self.damage_dealt = 0.0
        self.damage_taken = 0.0
        self.kills = 0

    def _apply_star_scaling(self) -> None:
        multiplier = 1.0 + (self.star_level - 1) * 0.5
        self.max_hp = self.base_max_hp * multiplier
        self.hp = self.max_hp
        self.atk = self.base_atk * multiplier
        self.defense = self.base_defense * multiplier
        self.speed = self.base_speed


@dataclass
class Card:
    """A shop item. Either creates a unit or provides an immediate effect."""

    name: str
    card_type: CardType
    sect: Sect
    rarity: Rarity
    cost: int
    create_unit: Optional[Callable[[], Unit]] = None
    passive_effect: Optional[Callable[["PlayerState"], None]] = None
    active_effect: Optional[AbilityEffect] = None
    description: str = ""

    def __hash__(self) -> int:  # pragma: no cover - stable identity by name
        return hash(self.name)

    def __eq__(self, other: object) -> bool:  # pragma: no cover - used in sets
        return isinstance(other, Card) and self.name == other.name


# Forward references for type checking only. These imports are intentionally
# placed at the bottom to avoid circular imports during runtime.
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - only for typing
    from .combat import CombatContext
    from .player import PlayerState
