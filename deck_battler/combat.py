"""Combat simulation for the Deck Battler engine."""
from __future__ import annotations

import random
from typing import List, Tuple

from .enums import Sect, Rarity, TriggerType, StatusEffect
from .models import Unit


class CombatEngine:
    """Tick based combat simulator similar to classic auto-battlers."""

    def __init__(self) -> None:
        self.tick_rate = 0.5
        self.max_ticks = 60
        self.current_tick = 0
        self.team_a: List[Unit] = []
        self.team_b: List[Unit] = []
        self.has_grace = False

    def simulate_combat(self, deck_a: List[Unit], deck_b: List[Unit]) -> Tuple[bool, int]:
        """Simulate combat between the two decks."""
        self.team_a = [u.copy() for u in deck_a]
        self.team_b = [u.copy() for u in deck_b]
        self.current_tick = 0
        self.has_grace = False

        self._trigger_abilities(TriggerType.COMBAT_START)

        while self.current_tick < self.max_ticks:
            if not self._are_alive(self.team_a) or not self._are_alive(self.team_b):
                break

            self._process_tick()
            self.current_tick += 1

        team_a_alive = self._are_alive(self.team_a)
        team_b_alive = self._are_alive(self.team_b)

        if team_a_alive and not team_b_alive:
            return True, self._calculate_damage(self.team_a)
        if team_b_alive and not team_a_alive:
            return False, self._calculate_damage(self.team_b)

        hp_a = sum(u.hp for u in self.team_a if u.is_alive)
        hp_b = sum(u.hp for u in self.team_b if u.is_alive)
        if hp_a >= hp_b:
            return True, max(1, int((hp_a - hp_b) / 10))
        return False, max(1, int((hp_b - hp_a) / 10))

    # ------------------------------------------------------------------
    # Combat loop
    # ------------------------------------------------------------------

    def _process_tick(self) -> None:
        for team in [self.team_a, self.team_b]:
            for unit in team:
                if unit.is_alive:
                    for ability in unit.abilities:
                        ability.current_cooldown = max(0.0, ability.current_cooldown - self.tick_rate)

        self._process_status_effects()
        self._trigger_abilities(TriggerType.EVERY_TICK)
        self._process_attacks()

    def _process_attacks(self) -> None:
        for team, enemy_team in [(self.team_a, self.team_b), (self.team_b, self.team_a)]:
            for unit in team:
                if not unit.is_alive or StatusEffect.STUN in unit.status_effects:
                    continue

                alive_enemies = [u for u in enemy_team if u.is_alive]
                if not alive_enemies:
                    continue

                target = random.choice(alive_enemies)
                damage = unit.atk

                if StatusEffect.BUFF_ATK in unit.status_effects:
                    damage *= 1.3
                if StatusEffect.DEBUFF_ATK in unit.status_effects:
                    damage *= 0.7

                actual_damage = target.take_damage(damage)
                unit.damage_dealt += actual_damage

                self._trigger_unit_abilities(unit, TriggerType.ON_ATTACK)

                if not target.is_alive:
                    unit.kills += 1
                    self._trigger_unit_abilities(unit, TriggerType.ON_KILL)
                    self._trigger_unit_abilities(target, TriggerType.ON_DEATH)
                else:
                    self._trigger_unit_abilities(target, TriggerType.ON_DAMAGED)

                    hp_percent = target.hp / target.max_hp if target.max_hp else 0
                    for ability in target.abilities:
                        if ability.trigger == TriggerType.HP_THRESHOLD and ability.current_cooldown == 0:
                            if hp_percent <= ability.threshold:
                                ability.effect(target, self)
                                ability.current_cooldown = ability.cooldown

    def _process_status_effects(self) -> None:
        for team in [self.team_a, self.team_b]:
            for unit in team:
                if not unit.is_alive:
                    continue

                for status in list(unit.status_effects.keys()):
                    unit.status_effects[status] -= self.tick_rate
                    if unit.status_effects[status] <= 0:
                        del unit.status_effects[status]

                if StatusEffect.BURN in unit.status_effects:
                    unit.take_damage(5)
                if StatusEffect.POISON in unit.status_effects:
                    unit.take_damage(3)

    def _trigger_abilities(self, trigger: TriggerType) -> None:
        for team in [self.team_a, self.team_b]:
            for unit in team:
                if unit.is_alive:
                    self._trigger_unit_abilities(unit, trigger)

    def _trigger_unit_abilities(self, unit: Unit, trigger: TriggerType) -> None:
        for ability in unit.abilities:
            if ability.trigger == trigger and ability.current_cooldown == 0:
                ability.effect(unit, self)
                if ability.cooldown:
                    ability.current_cooldown = ability.cooldown

    def _are_alive(self, team: List[Unit]) -> bool:
        return any(unit.is_alive for unit in team)

    def _calculate_damage(self, team: List[Unit]) -> int:
        return max(1, int(sum(u.star_level for u in team if u.is_alive)))

    # ------------------------------------------------------------------
    # Ability helper API used by card definitions
    # ------------------------------------------------------------------

    def apply_team_buff(self, sect: Sect, stat: str, amount: float, duration: float) -> None:
        for unit in self.team_a:
            if unit.is_alive and unit.sect == sect:
                if stat == "defense":
                    unit.apply_status(StatusEffect.BUFF_DEF, duration)
                    unit.defense += amount
                elif stat == "attack":
                    unit.apply_status(StatusEffect.BUFF_ATK, duration)
                    unit.atk += amount

    def apply_team_effect(self, effect) -> None:
        for unit in self.team_a:
            if unit.is_alive:
                effect(unit)

    def aoe_damage_enemies(self, damage: float) -> None:
        for unit in self.team_b:
            if unit.is_alive:
                unit.take_damage(damage)

    def instant_damage_weakest(self, damage: float) -> None:
        alive = [u for u in self.team_b if u.is_alive]
        if not alive:
            return
        target = min(alive, key=lambda u: u.hp)
        target.take_damage(damage)

    def execute_low_hp_enemy(self, threshold: float) -> None:
        alive = [u for u in self.team_b if u.is_alive and (u.hp / u.max_hp) <= threshold]
        if alive:
            target = random.choice(alive)
            target.hp = 0
            target.is_alive = False

    def execute_all_low_hp(self, threshold: float) -> None:
        for unit in self.team_b:
            if unit.is_alive and (unit.hp / unit.max_hp) <= threshold:
                unit.hp = 0
                unit.is_alive = False

    def kill_highest_hp_enemy(self) -> None:
        alive = [u for u in self.team_b if u.is_alive]
        if alive:
            target = max(alive, key=lambda u: u.hp)
            target.hp = 0
            target.is_alive = False

    def heal_team(self, amount: float) -> None:
        for unit in self.team_a:
            if unit.is_alive:
                unit.heal(amount)

    def revive_unit(self, unit: Unit, ratio: float) -> None:
        graveyard = [u for u in self.team_a if not u.is_alive]
        if graveyard:
            revived = graveyard[0]
            revived.is_alive = True
            revived.hp = revived.max_hp * ratio

    def apply_team_invuln(self, duration: float) -> None:
        for unit in self.team_a:
            if unit.is_alive:
                unit.apply_status(StatusEffect.SHIELD, duration)

    def apply_burn_to_target(self, damage: float, duration: float) -> None:
        alive = [u for u in self.team_b if u.is_alive]
        if alive:
            target = random.choice(alive)
            target.apply_status(StatusEffect.BURN, duration)
            target.take_damage(damage)

    def damage_all_units(self, damage: float) -> None:
        for unit in self.team_a + self.team_b:
            if unit.is_alive:
                unit.take_damage(damage)

    def summon_treants(self, count: int) -> None:
        for _ in range(count):
            treant = Unit("Treant", Sect.NATURE, Rarity.COMMON, 60, 60, 18, 8, 1.0)
            self.team_a.append(treant)

    def scale_team_permanently(self, multiplier: float) -> None:
        for unit in self.team_a:
            if unit.is_alive:
                unit.atk *= multiplier
                unit.max_hp *= multiplier
                unit.hp *= multiplier

    def heal_and_buff_team(self, heal: float, buff: float) -> None:
        for unit in self.team_a:
            if unit.is_alive:
                unit.heal(heal)
                unit.atk += buff

    def true_damage_random(self, damage: float) -> None:
        alive = [u for u in self.team_b if u.is_alive]
        if alive:
            target = random.choice(alive)
            target.hp -= damage
            if target.hp <= 0:
                target.is_alive = False

    def stun_random_enemy(self, duration: float) -> None:
        alive = [u for u in self.team_b if u.is_alive]
        if alive:
            random.choice(alive).apply_status(StatusEffect.STUN, duration)

    def chain_damage(self, damage: float, jumps: int) -> None:
        alive = [u for u in self.team_b if u.is_alive]
        if not alive:
            return
        target = random.choice(alive)
        for _ in range(jumps):
            target.take_damage(damage)
            alive = [u for u in self.team_b if u.is_alive and u is not target]
            if not alive:
                break
            target = random.choice(alive)

    def mass_debuff_enemies(self) -> None:
        for unit in self.team_b:
            if unit.is_alive:
                unit.apply_status(StatusEffect.DEBUFF_ATK, 5.0)
                unit.apply_status(StatusEffect.DEBUFF_DEF, 5.0)

    def freeze_all_enemies(self, duration: float) -> None:
        for unit in self.team_b:
            if unit.is_alive:
                unit.apply_status(StatusEffect.STUN, duration)

    def true_damage_all_enemies(self, damage: float) -> None:
        for unit in self.team_b:
            if unit.is_alive:
                unit.hp -= damage
                if unit.hp <= 0:
                    unit.is_alive = False

    def apply_massive_team_buff(self, multiplier: float) -> None:
        for unit in self.team_a:
            if unit.is_alive:
                unit.atk *= multiplier
                unit.defense *= multiplier

