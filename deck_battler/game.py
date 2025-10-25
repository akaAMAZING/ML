"""Game orchestration: shops, rounds and combat."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

from .cards import CardDatabase
from .combat import CombatEngine
from .enums import Sect
from .models import Card, Unit
from .player import PlayerState
from .synergies import summarize_synergies, serialize_synergy_definitions
from .artifacts import ARTIFACT_INDEX
from .strategic import StrategicOption, StrategicPlanner


class GameState:
    """Complete state for a match of Deck Battler."""

    def __init__(self, num_players: int = 2) -> None:
        self.num_players = num_players
        self.players: List[PlayerState] = [PlayerState(i) for i in range(num_players)]
        self.current_round = 0
        self.max_rounds = 30

        self.card_db = CardDatabase()
        self.combat_engine = CombatEngine()
        self.strategic_planner = StrategicPlanner()

        all_sects = list(Sect)
        self.active_sects = random.sample(all_sects, 4)
        self.active_legendaries: Dict[Sect, List[Card]] = {}
        for sect in self.active_sects:
            legends = self.card_db.legendaries_by_sect[sect]
            self.active_legendaries[sect] = random.sample(legends, min(2, len(legends)))

        self.shops: Dict[int, List[Card]] = {i: [] for i in range(num_players)}
        self.strategic_options: Dict[int, List[StrategicOption]] = {
            i: [] for i in range(num_players)
        }

    # ------------------------------------------------------------------
    # Economy & shop
    # ------------------------------------------------------------------

    def open_shop(self, player_id: int, size: int = 5) -> List[Card]:
        """Return the current shop, generating a fresh one if empty."""

        existing = self.shops.get(player_id, [])
        if existing:
            return existing
        return self.generate_shop(player_id, size=size)

    def generate_shop(self, player_id: int, size: int = 5) -> List[Card]:
        player = self.players[player_id]
        shop = self.card_db.generate_shop(
            player.level,
            self.active_sects,
            self.active_legendaries,
            size=size,
            focus_preferences=player.focus_preferences,
        )
        self.shops[player_id] = shop
        player.unlock_shop()
        return shop

    def reroll_shop(self, player_id: int, cost: int = 2) -> Tuple[bool, str]:
        player = self.players[player_id]
        effective_cost = max(0, cost - player.reroll_discount)
        if player.gold < effective_cost:
            return False, "Not enough gold"
        player.gold -= effective_cost
        player.unlock_shop()
        self.generate_shop(player_id)
        if effective_cost < cost:
            discount = cost - effective_cost
            return True, f"Shop refreshed (saved {discount} gold)"
        return True, "Shop refreshed"

    def buy_card(
        self, player_id: int, card_idx: int
    ) -> Tuple[bool, str, Card | None, List[Dict[str, int]]]:
        player = self.players[player_id]
        shop = self.shops.get(player_id) or []
        if not (0 <= card_idx < len(shop)):
            return False, "Invalid card", None, []
        card = shop[card_idx]
        if player.gold < card.cost:
            return False, "Not enough gold", None, []
        if not card.create_unit:
            return False, "Card cannot be purchased", None, []
        unit = card.create_unit()
        success, merge_events = player.add_to_deck(unit)
        if not success:
            return False, "Deck full", None, []
        player.gold -= card.cost
        player.unlock_shop()
        del shop[card_idx]
        message = f"Bought {card.name}"
        if merge_events:
            upgrades = ", ".join(
                f"{event['name']} ascended to ★{event['star_level']}"
                for event in merge_events
            )
            message = f"{message} · {upgrades}"
        return True, message, card, merge_events

    def sell_unit(self, player_id: int, deck_idx: int) -> Tuple[bool, str, int]:
        player = self.players[player_id]
        unit = player.remove_from_deck(deck_idx)
        if not unit:
            return False, "Invalid unit", 0
        refund = max(1, unit.rarity.tier)
        player.gold += refund
        return True, f"Sold {unit.name}", refund

    def level_up(self, player_id: int) -> Tuple[bool, str]:
        player = self.players[player_id]
        if player.level_up():
            return True, f"Reached level {player.level}"
        return False, "Cannot level up"

    def lock_shop(self, player_id: int) -> bool:
        player = self.players[player_id]
        return player.toggle_shop_lock()

    def unlock_shop(self, player_id: int) -> None:
        self.players[player_id].unlock_shop()

    # ------------------------------------------------------------------
    # Round & combat
    # ------------------------------------------------------------------

    def start_round(self) -> None:
        self.current_round += 1
        for player in self.players:
            if player.is_eliminated:
                self.strategic_options[player.player_id] = []
                continue
            player.prepare_new_round()
            player.earn_gold()
        self._prepare_strategic_options()

    def run_combat(self, player_a: int = 0, player_b: int = 1) -> Tuple[int, int]:
        deck_a = self.players[player_a].deck
        deck_b = self.players[player_b].deck
        if not deck_a and not deck_b:
            for player in self.players:
                player.resolve_combat_end()
            return player_a, 0
        elif not deck_a:
            winner, loser = player_b, player_a
            modifier = self.players[winner].get_combat_modifiers()
            bonus = int(modifier.get("damage_bonus", 0))
            damage = max(1, 5 + bonus)
        elif not deck_b:
            winner, loser = player_a, player_b
            modifier = self.players[winner].get_combat_modifiers()
            bonus = int(modifier.get("damage_bonus", 0))
            damage = max(1, 5 + bonus)
        else:
            modifiers_a = self.players[player_a].get_combat_modifiers()
            modifiers_b = self.players[player_b].get_combat_modifiers()
            won, damage = self.combat_engine.simulate_combat(
                deck_a, deck_b, modifiers_a, modifiers_b
            )
            winner = player_a if won else player_b
            loser = player_b if won else player_a
        self._apply_combat_results(winner, loser, damage)
        return winner, damage

    def _apply_combat_results(self, winner: int, loser: int, damage: int) -> None:
        win_player = self.players[winner]
        lose_player = self.players[loser]

        win_player.win_streak += 1
        win_player.lose_streak = 0
        win_player.total_damage_dealt += damage
        win_player.adjust_morale(4 + win_player.win_streak // 2)

        lose_player.take_damage(damage)
        lose_player.win_streak = 0
        lose_player.lose_streak += 1
        lose_player.adjust_morale(-3 - lose_player.lose_streak // 2)

        for player in self.players:
            if not player.is_eliminated:
                player.rounds_survived += 1
            player.resolve_combat_end()

    def is_game_over(self) -> bool:
        alive = sum(1 for p in self.players if not p.is_eliminated)
        return alive <= 1 or self.current_round >= self.max_rounds

    def get_alive_players(self) -> List[PlayerState]:
        return [p for p in self.players if not p.is_eliminated]

    # ------------------------------------------------------------------
    # Strategic options
    # ------------------------------------------------------------------

    def _prepare_strategic_options(self) -> None:
        for player in self.get_alive_players():
            options = self.strategic_planner.generate_options(
                player, list(self.active_sects)
            )
            self.strategic_options[player.player_id] = options

    def get_strategic_options(self, player_id: int) -> List[StrategicOption]:
        return self.strategic_options.get(player_id, [])

    def choose_strategic_option(
        self, player_id: int, option_idx: int
    ) -> Tuple[bool, str, Dict[str, Any]]:
        player = self.players[player_id]
        options = self.get_strategic_options(player_id)
        if player.is_eliminated:
            return False, "Player eliminated", {}
        if not player.strategic_choice_available:
            return False, "Strategic choice already used", {}
        if not (0 <= option_idx < len(options)):
            return False, "Invalid strategic option", {}
        option = options[option_idx]
        morale_cost = option.payload.get("morale_cost", 0)
        if player.gold < option.cost:
            return False, "Not enough gold", {"option_type": option.option_type}
        if player.morale < morale_cost:
            return False, "Not enough morale", {"option_type": option.option_type, "morale_cost": morale_cost}

        player.gold -= option.cost
        player.strategic_choice_available = False
        metadata: Dict[str, Any] = {
            "option_type": option.option_type,
            "morale_spent": 0,
        }
        if option.option_type == "focus":
            message, meta = self._apply_focus_option(player, option)
        elif option.option_type == "training":
            message, meta = self._apply_training_option(player, option)
        elif option.option_type == "artifact":
            message, meta = self._apply_artifact_option(player, option)
        elif option.option_type == "expedition":
            message, meta = self._apply_expedition_option(player, option)
        elif option.option_type == "tactic":
            message, meta = self._apply_tactic_option(player, option, morale_cost)
        else:
            message, meta = "Nothing happens", {}
        if morale_cost and option.option_type != "tactic":
            player.adjust_morale(-morale_cost)
            metadata["morale_spent"] = morale_cost
        metadata.update(meta)
        return True, message, metadata

    def _apply_focus_option(
        self, player: PlayerState, option: StrategicOption
    ) -> Tuple[str, Dict[str, Any]]:
        sect = option.payload["sect"]
        duration = option.payload.get("duration", 3)
        player.add_focus(sect, duration)
        final_duration = player.focus_preferences.get(sect, duration)
        return (
            f"Research teams prioritize {sect.value} for {final_duration} rounds.",
            {"focus_value": final_duration},
        )

    def _apply_training_option(
        self, player: PlayerState, option: StrategicOption
    ) -> Tuple[str, Dict[str, Any]]:
        sect = option.payload["sect"]
        stat = option.payload["stat"]
        amount = option.payload["amount"] + player.training_bonus
        units = [unit for unit in player.deck if unit.sect == sect]
        if not units:
            return (
                "Training camp sat empty—no units of that sect to benefit.",
                {"training_applied": 0, "failed": True},
            )

        affected = 0
        for unit in units:
            if stat == "atk":
                unit.atk += amount
            elif stat == "hp":
                unit.max_hp += amount
                unit.hp = min(unit.hp + amount, unit.max_hp)
            elif stat == "speed":
                unit.speed += amount
            affected += 1

        return (
            f"{affected} {sect.value} units completed elite {stat.upper()} drills.",
            {"training_applied": affected, "amount": amount},
        )

    def _apply_artifact_option(
        self, player: PlayerState, option: StrategicOption
    ) -> Tuple[str, Dict[str, Any]]:
        artifact = option.payload["artifact"]
        effect_summary = player.add_artifact(artifact)
        return (
            f"Recovered {artifact.name}: {effect_summary}",
            {"artifact": artifact.id, "power": artifact.power},
        )

    def _apply_tactic_option(
        self, player: PlayerState, option: StrategicOption, morale_cost: int
    ) -> Tuple[str, Dict[str, Any]]:
        payload = option.payload
        tactic_id = payload.get("id", option.id)
        attack_bonus = float(payload.get("attack_bonus", 0.0))
        defense_bonus = float(payload.get("defense_bonus", 0.0))
        speed_bonus = float(payload.get("speed_bonus", 0.0))
        damage_bonus = int(payload.get("damage_bonus", 0))
        duration = int(payload.get("duration", 1))
        label = payload.get("label", option.name)

        player.activate_tactic(
            tactic_id,
            attack_bonus=attack_bonus,
            defense_bonus=defense_bonus,
            speed_bonus=speed_bonus,
            damage_bonus=damage_bonus,
            duration=duration,
            morale_cost=morale_cost,
        )
        message = (
            f"Battle plan '{label}' enacted for {duration} round(s)."
            if duration
            else f"Battle plan '{label}' enacted."
        )
        return message, {
            "tactic": label,
            "tactic_rounds": duration,
            "attack_bonus": attack_bonus,
            "defense_bonus": defense_bonus,
            "speed_bonus": speed_bonus,
            "damage_bonus": damage_bonus,
            "morale_spent": morale_cost,
        }

    def _apply_expedition_option(
        self, player: PlayerState, option: StrategicOption
    ) -> Tuple[str, Dict[str, Any]]:
        risk = option.payload["risk"]
        reward_type = option.payload["reward"]
        base_chance = option.payload["success_chance"]
        safety = min(0.95, base_chance + player.expedition_safety * 0.05)
        roll = random.random()
        metadata: Dict[str, Any] = {
            "expedition_roll": roll,
            "risk": risk,
            "reward_type": reward_type,
        }
        if roll <= safety:
            metadata["expedition_success"] = True
            message = self._resolve_expedition_success(player, option, metadata)
        else:
            metadata["expedition_success"] = False
            damage = max(1, risk - player.expedition_safety)
            player.take_damage(damage)
            metadata["damage"] = damage
            message = f"Expedition ambushed! You lost {damage} HP."
        return message, metadata

    def _resolve_expedition_success(
        self, player: PlayerState, option: StrategicOption, metadata: Dict[str, Any]
    ) -> str:
        reward_type = option.payload["reward"]
        reward_value = option.payload.get("reward_value", 0)
        sect = option.payload["sect"]
        if reward_type == "gold":
            player.gold += reward_value
            metadata["gold_gain"] = reward_value
            return f"Expedition returns with {reward_value} gold in spoils!"
        if reward_type == "card":
            rarity = option.payload.get("rarity")
            pool = [
                card
                for card in self.card_db.all_cards
                if card.sect == sect
                and (rarity is None or card.rarity.tier >= rarity.tier)
            ]
            if not pool:
                pool = [card for card in self.card_db.all_cards if card.sect == sect]
            reward_card = random.choice(pool)
            unit = reward_card.create_unit() if reward_card.create_unit else None
            if unit:
                success, events = player.add_to_deck(unit)
                metadata["card_added"] = reward_card.name
                metadata["merge_events"] = events
                if not success:
                    self.shops.setdefault(player.player_id, [])
                    self.shops[player.player_id].append(reward_card)
                    return (
                        f"No room on the board—{reward_card.name} was stored in the shop."
                    )
                return f"Recruited expedition veteran {reward_card.name}!"
            return "Expedition returned with blueprints but no recruit."
        if reward_type == "training":
            amount = reward_value or 10
            fake_option = StrategicOption(
                id="expedition_training",
                name="Field Lessons",
                description="",
                cost=0,
                option_type="training",
                payload={"sect": sect, "stat": "atk", "amount": amount},
            )
            message, extra = self._apply_training_option(player, fake_option)
            metadata.update(extra)
            return f"Field lessons inspire the troops. {message}"
        return "Expedition succeeded but yielded no tangible reward."

    # ------------------------------------------------------------------
    # Serialization helpers for API/frontend
    # ------------------------------------------------------------------

    def serialize_unit(self, unit: Unit) -> Dict:
        return {
            "name": unit.name,
            "sect": unit.sect.value,
            "rarity": unit.rarity.color,
            "hp": unit.hp,
            "max_hp": unit.max_hp,
            "atk": unit.atk,
            "defense": unit.defense,
            "speed": unit.speed,
            "is_alive": unit.is_alive,
            "star_level": unit.star_level,
            "abilities": [
                {"name": ability.name, "description": ability.description}
                for ability in unit.abilities
            ],
        }

    def serialize_card(self, card: Card) -> Dict:
        return {
            "name": card.name,
            "sect": card.sect.value,
            "rarity": card.rarity.color,
            "cost": card.cost,
            "description": card.description,
        }

    def serialize_player(self, player: PlayerState) -> Dict:
        tracked_sects = list(dict.fromkeys(list(self.active_sects) + [unit.sect for unit in player.deck]))
        return {
            "player_id": player.player_id,
            "hp": player.hp,
            "gold": player.gold,
            "level": player.level,
            "win_streak": player.win_streak,
            "lose_streak": player.lose_streak,
            "deck": [self.serialize_unit(unit) for unit in player.deck],
            "max_deck_size": player.get_max_deck_size(),
            "interest": player.get_interest(),
            "streak_bonus": player.get_streak_bonus(),
            "collection_inventory": player.get_collection_inventory(),
            "synergies": summarize_synergies(player.deck, tracked_sects),
            "focus_preferences": {
                sect.value: value for sect, value in player.focus_preferences.items()
            },
            "artifacts": [
                ARTIFACT_INDEX[artifact_id].name
                if artifact_id in ARTIFACT_INDEX
                else artifact_id
                for artifact_id in player.artifacts
            ],
            "economy_bonus": player.economy_bonus,
            "reroll_discount": player.reroll_discount,
            "training_bonus": player.training_bonus,
            "expedition_safety": player.expedition_safety,
            "focus_duration_bonus": player.focus_duration_bonus,
            "morale": player.morale,
            "max_morale": player.max_morale,
            "active_tactic": player.serialize_tactic(),
            "strategic_choice_available": player.strategic_choice_available,
            "strategic_options": [
                option.serialize() for option in self.get_strategic_options(player.player_id)
            ],
        }

    def to_public_dict(self) -> Dict:
        return {
            "game_id": id(self),
            "current_round": self.current_round,
            "max_rounds": self.max_rounds,
            "is_game_over": self.is_game_over(),
            "active_sects": [sect.value for sect in self.active_sects],
            "synergy_definitions": serialize_synergy_definitions(self.active_sects),
            "active_legendaries": {
                sect.value: [self.serialize_card(card) for card in cards]
                for sect, cards in self.active_legendaries.items()
            },
            "players": [self.serialize_player(player) for player in self.players],
            "shops": {
                str(pid): [self.serialize_card(card) for card in shop]
                for pid, shop in self.shops.items()
            },
        }
