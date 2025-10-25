"""Player state, economy and deck management."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .models import Unit


@dataclass
class PlayerState:
    player_id: int
    hp: int = 100
    gold: int = 10
    level: int = 1
    deck: List[Unit] = field(default_factory=list)
    bench: List[Unit] = field(default_factory=list)

    win_streak: int = 0
    lose_streak: int = 0
    rounds_survived: int = 0
    total_damage_dealt: int = 0
    total_damage_taken: int = 0
    placement: int = 0
    is_eliminated: bool = False

    def get_max_deck_size(self) -> int:
        return min(self.level + 2, 10)

    def get_interest(self) -> int:
        return min(5, self.gold // 10)

    def get_streak_bonus(self) -> int:
        return min(3, max(self.win_streak, self.lose_streak))

    def earn_gold(self, base: int = 5) -> int:
        total = base + self.get_interest() + self.get_streak_bonus()
        self.gold += total
        return total

    def can_level_up(self) -> bool:
        return self.gold >= 4 and self.level < 8

    def level_up(self) -> bool:
        if self.can_level_up():
            self.gold -= 4
            self.level += 1
            return True
        return False

    def take_damage(self, damage: int) -> None:
        self.hp -= damage
        self.total_damage_taken += damage
        if self.hp <= 0:
            self.hp = 0
            self.is_eliminated = True

    def add_to_deck(self, unit: Unit) -> bool:
        if len(self.deck) < self.get_max_deck_size():
            self.deck.append(unit)
            return True
        return False

    def remove_from_deck(self, idx: int) -> Unit | None:
        if 0 <= idx < len(self.deck):
            return self.deck.pop(idx)
        return None
