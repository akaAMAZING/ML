"""Lightweight heuristic agent used for self-play and the API opponent."""
from __future__ import annotations

import random
from typing import List

from .game import GameState
from .models import Card
from .player import PlayerState


class DeckBattlerAgent:
    """A pragmatic baseline agent that follows a handful of simple rules."""

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

    def select_actions(self, game: GameState, player_id: int, shop: List[Card]) -> List[dict]:
        player = game.players[player_id]
        preferred_sect = self._preferred_sect(player)
        actions: List[dict] = []

        available_gold = player.gold
        slots = player.get_max_deck_size() - len(player.deck)
        remaining_cards = list(shop)
        idx = 0
        while idx < len(remaining_cards):
            card = remaining_cards[idx]
            if card.cost > available_gold or slots <= 0:
                idx += 1
                continue

            score = self._score_card(card, preferred_sect)
            if score <= 0:
                idx += 1
                continue

            actions.append({"type": "buy", "card_idx": idx})
            available_gold -= card.cost
            slots -= 1
            remaining_cards.pop(idx)
            continue

        if player.can_level_up() and available_gold >= 6:
            actions.append({"type": "level"})

        return actions

    def _preferred_sect(self, player: PlayerState) -> str | None:
        if not player.deck:
            return None
        counts: dict[str, int] = {}
        for unit in player.deck:
            counts[unit.sect.value] = counts.get(unit.sect.value, 0) + 1
        return max(counts, key=counts.get)

    def _score_card(self, card: Card, preferred_sect: str | None) -> float:
        score = card.rarity.tier
        if preferred_sect and card.sect.value == preferred_sect:
            score += 2
        return score
