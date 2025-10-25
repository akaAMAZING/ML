"""Player state, economy and deck management."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, TYPE_CHECKING

from .enums import Sect
from .models import Unit


if TYPE_CHECKING:  # pragma: no cover
    from .artifacts import Artifact


@dataclass
class PlayerState:
    player_id: int
    hp: int = 100
    gold: int = 10
    level: int = 1
    deck: List[Unit] = field(default_factory=list)
    bench: List[Unit] = field(default_factory=list)
    collection_inventory: Dict[str, Dict[int, int]] = field(default_factory=dict)
    shop_locked: bool = False

    focus_preferences: Dict[Sect, int] = field(default_factory=dict)
    focus_duration_bonus: int = 0
    training_bonus: int = 0
    expedition_safety: int = 0
    economy_bonus: int = 0
    reroll_discount: int = 0
    artifacts: List[str] = field(default_factory=list)
    strategic_choice_available: bool = False

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
        total = base + self.get_interest() + self.get_streak_bonus() + self.economy_bonus
        self.gold += total
        return total

    def prepare_new_round(self) -> None:
        """Reset transient round state and decay focus timers."""

        self.strategic_choice_available = True
        self.decay_focus_preferences()

    def toggle_shop_lock(self) -> bool:
        """Flip the persistent shop lock state."""

        self.shop_locked = not self.shop_locked
        return self.shop_locked

    def unlock_shop(self) -> None:
        self.shop_locked = False

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

    def add_to_deck(self, unit: Unit) -> tuple[bool, List[Dict[str, int]]]:
        """Add a unit to the deck and attempt automatic merges."""

        merge_events: List[Dict[str, int]] = []
        duplicates = [u for u in self.deck if u.name == unit.name and u.star_level == unit.star_level]
        if len(self.deck) >= self.get_max_deck_size() and len(duplicates) < 2:
            return False, merge_events

        self.apply_passives(unit)
        self.deck.append(unit)
        self._increment_inventory(unit)
        merge_events.extend(self._attempt_merge(unit))
        return True, merge_events

    def remove_from_deck(self, idx: int) -> Unit | None:
        if 0 <= idx < len(self.deck):
            unit = self.deck.pop(idx)
            self._decrement_inventory(unit.name, unit.star_level)
            return unit
        return None

    # ------------------------------------------------------------------
    # Collection helpers
    # ------------------------------------------------------------------

    def _increment_inventory(self, unit: Unit) -> None:
        star_counts = self.collection_inventory.setdefault(unit.name, {})
        star_counts[unit.star_level] = star_counts.get(unit.star_level, 0) + 1

    def _decrement_inventory(self, name: str, star_level: int, amount: int = 1) -> None:
        star_counts = self.collection_inventory.get(name)
        if not star_counts:
            return
        star_counts[star_level] = max(0, star_counts.get(star_level, 0) - amount)
        if star_counts[star_level] <= 0:
            star_counts.pop(star_level, None)
        if not star_counts:
            self.collection_inventory.pop(name, None)

    def _remove_unit_instance(self, unit: Unit) -> None:
        if unit in self.deck:
            self.deck.remove(unit)
        self._decrement_inventory(unit.name, unit.star_level)

    def _attempt_merge(self, unit: Unit) -> List[Dict[str, int]]:
        events: List[Dict[str, int]] = []
        current_unit = unit

        while True:
            if current_unit.star_level >= 3:
                break
            same_units = [u for u in self.deck if u.name == current_unit.name and u.star_level == current_unit.star_level]
            if len(same_units) < 3:
                break

            consumed = same_units[:3]
            for consumed_unit in consumed:
                self._remove_unit_instance(consumed_unit)

            template = consumed[0].copy()
            template.refresh_state()
            template.promote()

            self.apply_passives(template)

            self.deck.append(template)
            self._increment_inventory(template)
            events.append({"star_level": template.star_level, "name": template.name})

            current_unit = template

        return events

    # ------------------------------------------------------------------
    # Strategic systems
    # ------------------------------------------------------------------

    def decay_focus_preferences(self) -> None:
        expired: List[Sect] = []
        for sect, remaining in list(self.focus_preferences.items()):
            new_value = remaining - 1
            if new_value <= 0:
                expired.append(sect)
            else:
                self.focus_preferences[sect] = new_value
        for sect in expired:
            self.focus_preferences.pop(sect, None)

    def add_focus(self, sect: Sect, duration: int) -> None:
        enhanced = duration + self.focus_duration_bonus
        current = self.focus_preferences.get(sect, 0)
        self.focus_preferences[sect] = max(current, enhanced)

    def add_artifact(self, artifact: "Artifact") -> str:
        self.artifacts.append(artifact.id)
        return artifact.apply(self)

    def apply_passives(self, unit: Unit) -> None:
        """Apply persistent bonuses from artifacts or focus systems."""

        if self.training_bonus:
            unit.atk += self.training_bonus
            unit.max_hp += self.training_bonus * 2
            unit.hp = min(unit.hp + self.training_bonus * 2, unit.max_hp)

    def get_collection_inventory(self) -> Dict[str, Dict[str, int]]:
        return {
            name: {str(star): count for star, count in sorted(star_counts.items())}
            for name, star_counts in self.collection_inventory.items()
        }
