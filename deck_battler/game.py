"""Game orchestration: shops, rounds and combat."""
from __future__ import annotations

import random
from typing import Dict, List, Tuple

from .cards import CardDatabase
from .combat import CombatEngine
from .enums import Sect
from .models import Card, Unit
from .player import PlayerState
from .synergies import summarize_synergies, serialize_synergy_definitions


class GameState:
    """Complete state for a match of Deck Battler."""

    def __init__(self, num_players: int = 2) -> None:
        self.num_players = num_players
        self.players: List[PlayerState] = [PlayerState(i) for i in range(num_players)]
        self.current_round = 0
        self.max_rounds = 30

        self.card_db = CardDatabase()
        self.combat_engine = CombatEngine()

        all_sects = list(Sect)
        self.active_sects = random.sample(all_sects, 4)
        self.active_legendaries: Dict[Sect, List[Card]] = {}
        for sect in self.active_sects:
            legends = self.card_db.legendaries_by_sect[sect]
            self.active_legendaries[sect] = random.sample(legends, min(2, len(legends)))

        self.shops: Dict[int, List[Card]] = {i: [] for i in range(num_players)}

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
            player.level, self.active_sects, self.active_legendaries, size=size
        )
        self.shops[player_id] = shop
        player.unlock_shop()
        return shop

    def reroll_shop(self, player_id: int, cost: int = 2) -> Tuple[bool, str]:
        player = self.players[player_id]
        if player.gold < cost:
            return False, "Not enough gold"
        player.gold -= cost
        player.unlock_shop()
        self.generate_shop(player_id)
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
        for player in self.get_alive_players():
            player.earn_gold()

    def run_combat(self, player_a: int = 0, player_b: int = 1) -> Tuple[int, int]:
        deck_a = self.players[player_a].deck
        deck_b = self.players[player_b].deck
        if not deck_a and not deck_b:
            return player_a, 0
        if not deck_a:
            winner, loser, damage = player_b, player_a, 5
        elif not deck_b:
            winner, loser, damage = player_a, player_b, 5
        else:
            won, damage = self.combat_engine.simulate_combat(deck_a, deck_b)
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

        lose_player.take_damage(damage)
        lose_player.win_streak = 0
        lose_player.lose_streak += 1

        for player in self.players:
            if not player.is_eliminated:
                player.rounds_survived += 1

    def is_game_over(self) -> bool:
        alive = sum(1 for p in self.players if not p.is_eliminated)
        return alive <= 1 or self.current_round >= self.max_rounds

    def get_alive_players(self) -> List[PlayerState]:
        return [p for p in self.players if not p.is_eliminated]

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
