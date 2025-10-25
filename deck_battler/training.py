"""Utilities for running lightweight self-play training loops."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .agent import DeckBattlerAgent
from .game import GameState


@dataclass
class EpisodeResult:
    winner: int
    rounds: int
    damage_dealt: List[int]


class SelfPlaySession:
    """Simulate games between heuristic agents to bootstrap data."""

    def __init__(self, episodes: int = 10) -> None:
        self.episodes = episodes
        self.agent_pool = [DeckBattlerAgent(seed=i) for i in range(8)]

    def run(self) -> List[EpisodeResult]:
        results: List[EpisodeResult] = []
        for episode in range(self.episodes):
            game = GameState(num_players=2)
            agents = self.agent_pool[:2]

            while not game.is_game_over():
                game.start_round()
                for player_id, agent in enumerate(agents):
                    shop = game.generate_shop(player_id)
                    actions = agent.select_actions(game, player_id, shop)
                    for action in actions:
                        if action["type"] == "buy":
                            game.buy_card(player_id, action["card_idx"])
                        elif action["type"] == "level":
                            game.level_up(player_id)
                game.run_combat(0, 1)

            winner = max(range(2), key=lambda idx: game.players[idx].hp)
            results.append(
                EpisodeResult(
                    winner=winner,
                    rounds=game.current_round,
                    damage_dealt=[p.total_damage_dealt for p in game.players[:2]],
                )
            )
        return results
