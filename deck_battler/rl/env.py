"""Gymnasium environment that exposes the full Deck Battler action space."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from ..enums import Rarity, Sect
from ..game import GameState
from ..models import Card, Unit
from ..player import PlayerState
from ..synergies import get_synergy_levels
from ..strategic import StrategicOption
from .opponents import ScriptedOpponent, TrainingOpponent


MAX_SHOP_SIZE = 5
MAX_DECK_SIZE = 10
MAX_STRATEGIC_OPTIONS = 3
_CARD_FEATURES = 8
_UNIT_FEATURES = 9
_PLAYER_FEATURES = 15
_SYNERGY_FEATURES = len(list(Sect))
_STRATEGIC_FEATURES = 5


@dataclass
class RewardConfig:
    """Configurable reward shaping parameters."""

    buy_reward: float = 0.05
    sell_reward: float = 0.02
    merge_bonus: float = 0.25
    reroll_penalty: float = -0.01
    level_reward: float = 0.08
    lock_reward: float = 0.0
    strategic_reward: float = 0.1
    focus_reward: float = 0.05
    training_reward: float = 0.12
    artifact_reward: float = 0.18
    expedition_success_bonus: float = 0.25
    expedition_failure_penalty: float = -0.15
    invalid_action_penalty: float = -0.1
    failed_action_penalty: float = -0.05
    gold_scale: float = 0.01
    board_value_scale: float = 0.001
    combat_damage_scale: float = 0.1
    win_bonus: float = 1.0
    loss_penalty: float = 0.5
    elimination_bonus: float = 3.0
    elimination_penalty: float = 3.0


class DeckBattlerEnv(gym.Env):
    """Single-agent environment that wraps a two-player Deck Battler match."""

    metadata = {"render_modes": []}

    def __init__(
        self,
        *,
        opponent: Optional[TrainingOpponent] = None,
        reward_config: Optional[RewardConfig] = None,
        max_rounds: int = 30,
        seed: Optional[int] = None,
    ) -> None:
        super().__init__()
        self.opponent = opponent or ScriptedOpponent()
        self.reward_config = reward_config or RewardConfig()
        self.max_rounds = max_rounds

        self.game: Optional[GameState] = None
        self.prev_board_value: float = 0.0

        self._sect_to_idx = {sect: idx for idx, sect in enumerate(Sect)}

        obs_dim = (
            MAX_SHOP_SIZE * _CARD_FEATURES
            + MAX_DECK_SIZE * _UNIT_FEATURES
            + _PLAYER_FEATURES * 2
            + _SYNERGY_FEATURES * 2
            + MAX_STRATEGIC_OPTIONS * _STRATEGIC_FEATURES
            + 2
        )
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
        )

        self.buy_offset = 0
        self.sell_offset = self.buy_offset + MAX_SHOP_SIZE
        self.reroll_index = self.sell_offset + MAX_DECK_SIZE
        self.level_index = self.reroll_index + 1
        self.lock_index = self.level_index + 1
        self.end_turn_index = self.lock_index + 1
        self.strategic_offset = self.end_turn_index + 1
        self.action_space = spaces.Discrete(self.strategic_offset + MAX_STRATEGIC_OPTIONS)

    # ------------------------------------------------------------------
    # Gym API
    # ------------------------------------------------------------------

    def reset(self, *, seed: Optional[int] = None, options: Optional[Dict] = None):
        super().reset(seed=seed)

        self.game = GameState(num_players=2)
        self.game.start_round()
        self.game.generate_shop(0)
        self.game.generate_shop(1)

        self.prev_board_value = self._board_value(self.player)

        observation = self._build_observation()
        info = {"action_mask": self._action_mask(), "round": self.game.current_round}
        return observation, info

    def step(self, action: int):
        if self.game is None:
            raise RuntimeError("Environment has not been reset")

        reward = 0.0
        terminated = False
        truncated = False
        info: Dict[str, object] = {"round": self.game.current_round}

        mask = self._action_mask()
        if not mask[action]:
            reward += self.reward_config.invalid_action_penalty
            observation = self._build_observation()
            info["action_mask"] = mask
            info["invalid_action"] = True
            return observation, reward, terminated, truncated, info

        if action < self.sell_offset:
            reward += self._handle_buy(action)
        elif action < self.reroll_index:
            deck_idx = action - self.sell_offset
            reward += self._handle_sell(deck_idx)
        elif action == self.reroll_index:
            reward += self._handle_reroll()
        elif action == self.level_index:
            reward += self._handle_level()
        elif action == self.lock_index:
            reward += self._handle_lock()
        elif action == self.end_turn_index:
            round_reward, terminated = self._resolve_round()
            reward += round_reward
        elif action < self.action_space.n:
            option_idx = action - self.strategic_offset
            reward += self._handle_strategic(option_idx, info)

        self.prev_board_value = self._board_value(self.player)
        observation = self._build_observation()
        info["action_mask"] = self._action_mask()
        if terminated or (self.game and self.game.current_round >= self.max_rounds):
            terminated = True
        return observation, reward, terminated, truncated, info

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _handle_buy(self, card_idx: int) -> float:
        if self.game is None:
            return 0.0
        success, _, card, merge_events = self.game.buy_card(0, card_idx)
        if not success:
            return self.reward_config.failed_action_penalty
        reward = self.reward_config.buy_reward
        reward += len(merge_events) * self.reward_config.merge_bonus
        if card:
            reward += card.cost * self.reward_config.gold_scale
        return reward + self._board_delta_reward()

    def _handle_sell(self, deck_idx: int) -> float:
        if self.game is None:
            return 0.0
        success, _, refund = self.game.sell_unit(0, deck_idx)
        if not success:
            return self.reward_config.failed_action_penalty
        reward = self.reward_config.sell_reward + refund * self.reward_config.gold_scale
        return reward + self._board_delta_reward()

    def _handle_reroll(self) -> float:
        if self.game is None:
            return 0.0
        success, _ = self.game.reroll_shop(0)
        if not success:
            return self.reward_config.failed_action_penalty
        return self.reward_config.reroll_penalty

    def _handle_level(self) -> float:
        if self.game is None:
            return 0.0
        success, _ = self.game.level_up(0)
        if not success:
            return self.reward_config.failed_action_penalty
        return self.reward_config.level_reward

    def _handle_lock(self) -> float:
        if self.game is None:
            return 0.0
        self.game.lock_shop(0)
        return self.reward_config.lock_reward

    def _handle_strategic(self, option_idx: int, info: Dict[str, object]) -> float:
        if self.game is None:
            return 0.0
        success, message, metadata = self.game.choose_strategic_option(0, option_idx)
        metadata = metadata or {}
        metadata["message"] = message
        metadata["option_index"] = option_idx
        info["strategic_outcome"] = metadata
        if not success:
            info["strategic_failed"] = True
            return self.reward_config.failed_action_penalty

        reward = self.reward_config.strategic_reward
        option_type = metadata.get("option_type")
        if option_type == "focus":
            reward += self.reward_config.focus_reward
        elif option_type == "training":
            reward += self.reward_config.training_reward
            if metadata.get("failed"):
                reward += self.reward_config.failed_action_penalty
        elif option_type == "artifact":
            reward += self.reward_config.artifact_reward
        elif option_type == "expedition":
            if metadata.get("expedition_success"):
                reward += self.reward_config.expedition_success_bonus
            else:
                reward += self.reward_config.expedition_failure_penalty

        reward += metadata.get("gold_gain", 0) * self.reward_config.gold_scale
        return reward + self._board_delta_reward()

    def _resolve_round(self) -> Tuple[float, bool]:
        if self.game is None:
            return 0.0, True

        player = self.player
        opponent = self.opponent_player
        prev_hp = player.hp
        prev_opponent_hp = opponent.hp

        opponent_actions = self.opponent.play_round(self.game, 1)
        for action in opponent_actions:
            self._execute_opponent_action(action)

        winner, _ = self.game.run_combat(0, 1)
        damage_to_opponent = prev_opponent_hp - opponent.hp
        damage_taken = prev_hp - player.hp

        reward = (
            (damage_to_opponent - damage_taken) * self.reward_config.combat_damage_scale
        )
        if winner == 0:
            reward += self.reward_config.win_bonus
        else:
            reward -= self.reward_config.loss_penalty

        if opponent.is_eliminated:
            reward += self.reward_config.elimination_bonus
        if player.is_eliminated:
            reward -= self.reward_config.elimination_penalty

        terminated = player.is_eliminated or opponent.is_eliminated or self.game.is_game_over()

        if not terminated:
            self.game.start_round()
            if not player.shop_locked:
                self.game.generate_shop(0)
            if not opponent.shop_locked:
                self.game.generate_shop(1)
        return reward + self._board_delta_reward(), terminated

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _board_delta_reward(self) -> float:
        new_value = self._board_value(self.player)
        delta = new_value - self.prev_board_value
        return delta * self.reward_config.board_value_scale

    @property
    def player(self) -> PlayerState:
        if self.game is None:
            raise RuntimeError("Environment has not been reset")
        return self.game.players[0]

    @property
    def opponent_player(self) -> PlayerState:
        if self.game is None:
            raise RuntimeError("Environment has not been reset")
        return self.game.players[1]

    def _build_observation(self) -> np.ndarray:
        player = self.player
        opponent = self.opponent_player
        shop = self.game.shops.get(0, []) if self.game else []

        features: List[float] = []
        for idx in range(MAX_SHOP_SIZE):
            card = shop[idx] if idx < len(shop) else None
            features.extend(self._encode_card(card))

        for idx in range(MAX_DECK_SIZE):
            unit = player.deck[idx] if idx < len(player.deck) else None
            features.extend(self._encode_unit(unit))

        features.extend(self._encode_player(player))
        features.extend(self._encode_player(opponent))

        features.extend(self._encode_synergies(player.deck))
        features.extend(self._encode_synergies(opponent.deck))

        options = self.game.get_strategic_options(0) if self.game else []
        for idx in range(MAX_STRATEGIC_OPTIONS):
            option = options[idx] if idx < len(options) else None
            features.extend(self._encode_option(option, player))

        round_progress = self.game.current_round if self.game else 0
        features.append(round_progress / self.max_rounds)
        features.append(len(player.deck) / MAX_DECK_SIZE)

        return np.asarray(features, dtype=np.float32)

    def _encode_card(self, card: Optional[Card]) -> List[float]:
        if card is None:
            return [0.0] * _CARD_FEATURES
        sect_idx = self._sect_to_idx[card.sect] / max(1, len(self._sect_to_idx) - 1)
        unit = card.create_unit() if card.create_unit else None
        max_hp = unit.max_hp if unit else 0.0
        atk = unit.atk if unit else 0.0
        defense = unit.defense if unit else 0.0
        return [
            card.cost / 10,
            card.rarity.tier / len(Rarity),
            sect_idx,
            max_hp / 400,
            atk / 200,
            defense / 80,
            (unit.speed if unit else 0.0) / 3.0,
            1.0 if card.card_type.name == "UNIT" else 0.0,
        ]

    def _encode_unit(self, unit: Optional[Unit]) -> List[float]:
        if unit is None:
            return [0.0] * _UNIT_FEATURES
        sect_idx = self._sect_to_idx[unit.sect] / max(1, len(self._sect_to_idx) - 1)
        return [
            unit.max_hp / 400,
            unit.atk / 200,
            unit.defense / 80,
            unit.speed / 3.0,
            unit.star_level / 3.0,
            sect_idx,
            unit.rarity.tier / len(Rarity),
            unit.kills / 10.0,
            unit.damage_dealt / 500.0,
        ]

    def _encode_player(self, player: PlayerState) -> List[float]:
        focus_total = sum(player.focus_preferences.values())
        return [
            player.hp / 100,
            player.gold / 100,
            player.level / 8,
            player.get_interest() / 5,
            player.win_streak / 10,
            player.lose_streak / 10,
            1.0 if player.shop_locked else 0.0,
            len(player.deck) / MAX_DECK_SIZE,
            player.economy_bonus / 10,
            player.reroll_discount / 5,
            focus_total / 10,
            player.training_bonus / 10,
            player.expedition_safety / 10,
            len(player.artifacts) / 10,
            1.0 if player.strategic_choice_available else 0.0,
        ]

    def _encode_option(
        self, option: Optional[StrategicOption], player: PlayerState
    ) -> List[float]:
        if option is None:
            return [0.0] * _STRATEGIC_FEATURES
        type_map = {"focus": 0.0, "training": 1.0, "artifact": 2.0, "expedition": 3.0}
        option_type = type_map.get(option.option_type, 0.0) / 3.0
        cost = option.cost / 10.0
        if option.option_type == "focus":
            sect = option.payload.get("sect")
            duration = option.payload.get("duration", 0) + player.focus_duration_bonus
            sect_idx = 0.0
            if sect is not None:
                sect_idx = self._sect_to_idx[sect] / max(1, len(self._sect_to_idx) - 1)
            return [option_type, cost, sect_idx, duration / 6.0, 0.0]
        if option.option_type == "training":
            sect = option.payload.get("sect")
            stat = option.payload.get("stat", "atk")
            amount = option.payload.get("amount", 0)
            stat_map = {"atk": 0.0, "hp": 0.5, "speed": 1.0}
            sect_idx = 0.0
            if sect is not None:
                sect_idx = self._sect_to_idx[sect] / max(1, len(self._sect_to_idx) - 1)
            return [
                option_type,
                cost,
                sect_idx,
                stat_map.get(stat, 0.0),
                amount / 30.0,
            ]
        if option.option_type == "artifact":
            artifact = option.payload.get("artifact")
            power = getattr(artifact, "power", 1)
            return [
                option_type,
                cost,
                power / 5.0,
                len(player.artifacts) / 10.0,
                0.0,
            ]
        if option.option_type == "expedition":
            risk = option.payload.get("risk", 0)
            success = option.payload.get("success_chance", 0.5)
            reward_value = option.payload.get("reward_value", 0)
            return [
                option_type,
                cost,
                risk / 12.0,
                success,
                reward_value / 20.0,
            ]
        return [option_type, cost, 0.0, 0.0, 0.0]

    def _encode_synergies(self, units: List[Unit]) -> List[float]:
        levels = get_synergy_levels(units)
        vector = [0.0] * _SYNERGY_FEATURES
        for sect, level in levels.items():
            idx = self._sect_to_idx[sect]
            vector[idx] = level / 3.0
        return vector

    def _action_mask(self) -> np.ndarray:
        if self.game is None:
            return np.ones(self.action_space.n, dtype=np.int8)
        mask = np.zeros(self.action_space.n, dtype=np.int8)
        shop = self.game.shops.get(0, [])
        player = self.player

        for idx in range(MAX_SHOP_SIZE):
            if idx < len(shop):
                card = shop[idx]
                can_afford = player.gold >= card.cost
                can_add = self._can_add_card(player, card)
                mask[self.buy_offset + idx] = 1 if (can_afford and can_add) else 0
            else:
                mask[self.buy_offset + idx] = 0

        for idx in range(MAX_DECK_SIZE):
            mask[self.sell_offset + idx] = 1 if idx < len(player.deck) else 0

        mask[self.reroll_index] = 1 if player.gold >= 2 else 0
        mask[self.level_index] = 1 if player.can_level_up() else 0
        mask[self.lock_index] = 1
        mask[self.end_turn_index] = 1
        options = self.game.get_strategic_options(0)
        for idx in range(MAX_STRATEGIC_OPTIONS):
            action_idx = self.strategic_offset + idx
            if (
                idx < len(options)
                and player.strategic_choice_available
                and player.gold >= options[idx].cost
            ):
                mask[action_idx] = 1
            else:
                mask[action_idx] = 0
        return mask

    def _can_add_card(self, player: PlayerState, card: Card) -> bool:
        if len(player.deck) < player.get_max_deck_size():
            return True
        unit = card.create_unit() if card.create_unit else None
        if unit is None:
            return False
        duplicates = [
            existing
            for existing in player.deck
            if existing.name == unit.name and existing.star_level == unit.star_level
        ]
        return len(duplicates) >= 2

    def _board_value(self, player: PlayerState) -> float:
        value = float(player.gold) * 2.0
        value += player.economy_bonus * 12.0
        for unit in player.deck:
            value += unit.max_hp * 0.25
            value += unit.atk * 1.5
            value += unit.defense
            value += unit.star_level * 15.0
        synergy_levels = get_synergy_levels(player.deck)
        value += sum(level * 30.0 for level in synergy_levels.values())
        value += sum(player.focus_preferences.values()) * 8.0
        value += player.training_bonus * 15.0
        value += len(player.artifacts) * 40.0
        value += player.expedition_safety * 5.0
        return value

    def _execute_opponent_action(self, action: Dict[str, int | str]) -> None:
        if self.game is None:
            return
        action_type = action.get("type")
        if action_type == "buy":
            self.game.buy_card(1, int(action["card_idx"]))
        elif action_type == "sell":
            self.game.sell_unit(1, int(action["deck_idx"]))
        elif action_type == "reroll":
            self.game.reroll_shop(1)
        elif action_type == "level":
            self.game.level_up(1)
        elif action_type == "lock":
            self.game.lock_shop(1)

*** End Patch
