"""Opponent implementations used during RL training."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..agent import DeckBattlerAgent
from ..game import GameState
from ..models import Card


class TrainingOpponent:
    """Minimal interface for opponent controllers."""

    def play_round(self, game: GameState, player_id: int) -> List[dict]:
        raise NotImplementedError


@dataclass
class ScriptedOpponent(TrainingOpponent):
    """Wrap the heuristic agent so it can be used inside the environment."""

    agent: DeckBattlerAgent = DeckBattlerAgent()

    def play_round(self, game: GameState, player_id: int) -> List[dict]:
        shop = game.open_shop(player_id)
        actions = self.agent.select_actions(game, player_id, shop)

        player = game.players[player_id]
        if player.gold >= 2 and len(player.deck) < player.get_max_deck_size():
            high_cost = any(self._is_premium(card) for card in shop)
            if not high_cost:
                actions.append({"type": "reroll"})
        return actions

    def _is_premium(self, card: Card) -> bool:
        return card.rarity.tier >= 3
