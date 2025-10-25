"""FastAPI backend powering the Deck Battler UI."""
from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from deck_battler import CardDatabase, DeckBattlerAgent, GameState
from deck_battler.enums import Rarity, Sect

app = FastAPI(title="Deck Battler API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GameManager:
    """Keeps track of running games and websocket subscribers."""

    def __init__(self) -> None:
        self.active_games: Dict[str, GameState] = {}
        self.connections: Dict[str, List[WebSocket]] = defaultdict(list)
        self.agent = DeckBattlerAgent()
        self.card_db = CardDatabase()

    def create_game(self) -> str:
        game_id = str(uuid.uuid4())
        self.active_games[game_id] = GameState(num_players=2)
        return game_id

    def get_game(self, game_id: str) -> GameState:
        game = self.active_games.get(game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
        return game

    def serialize(self, game_id: str) -> Dict[str, Any]:
        game = self.get_game(game_id)
        state = game.to_public_dict()
        state["game_id"] = game_id
        return state

    async def broadcast(self, game_id: str, payload: Dict[str, Any]) -> None:
        recipients = self.connections.get(game_id, [])
        dead: List[WebSocket] = []
        for ws in recipients:
            try:
                await ws.send_json(payload)
            except WebSocketDisconnect:
                dead.append(ws)
            except Exception:
                dead.append(ws)
        for ws in dead:
            recipients.remove(ws)

    async def apply_action(self, game_id: str, player_id: int, action: Dict[str, Any]) -> Dict[str, Any]:
        game = self.get_game(game_id)
        action_type = action.get("type")
        result: Dict[str, Any] = {"success": False, "message": "Unknown action"}

        if action_type == "buy":
            success, message, card, events = game.buy_card(player_id, action.get("card_idx", -1))
            result = {"success": success, "message": message}
            if events:
                result["fusion_events"] = events
            if card:
                result["card"] = game.serialize_card(card)
        elif action_type == "sell":
            success, message, refund = game.sell_unit(player_id, action.get("deck_idx", -1))
            result = {"success": success, "message": message, "gold_refund": refund}
        elif action_type == "level":
            success, message = game.level_up(player_id)
            result = {"success": success, "message": message}
        elif action_type == "reroll":
            success, message = game.reroll_shop(player_id)
            result = {"success": success, "message": message}
        elif action_type == "strategic":
            success, message, metadata = game.choose_strategic_option(
                player_id, action.get("option_idx", -1)
            )
            result = {
                "success": success,
                "message": message,
                "metadata": metadata,
            }

        await self.broadcast(
            game_id,
            {
                "type": "action_result",
                "action": action,
                "result": result,
                "game_state": self.serialize(game_id),
            },
        )
        return result

    async def ai_turn(self, game_id: str, player_id: int) -> None:
        game = self.get_game(game_id)
        shop = game.generate_shop(player_id)
        await self.broadcast(
            game_id,
            {
                "type": "ai_thinking",
                "player_id": player_id,
                "shop": [game.serialize_card(card) for card in shop],
            },
        )

        actions = self.agent.select_actions(game, player_id, shop)
        for action in actions:
            await asyncio.sleep(0.3)
            await self.apply_action(game_id, player_id, action)

        await self.broadcast(
            game_id,
            {
                "type": "ai_turn_complete",
                "player_id": player_id,
                "game_state": self.serialize(game_id),
            },
        )

    async def run_combat(self, game_id: str) -> None:
        game = self.get_game(game_id)
        await self.broadcast(game_id, {"type": "combat_start", "round": game.current_round})
        await asyncio.sleep(0.5)
        winner, damage = game.run_combat(0, 1)
        await self.broadcast(
            game_id,
            {
                "type": "combat_end",
                "winner": winner,
                "damage": damage,
                "game_state": self.serialize(game_id),
            },
        )

    async def start_round(self, game_id: str) -> None:
        game = self.get_game(game_id)
        game.start_round()
        for player_id in range(game.num_players):
            game.generate_shop(player_id)
        await self.broadcast(
            game_id,
            {
                "type": "round_start",
                "round": game.current_round,
                "game_state": self.serialize(game_id),
            },
        )


manager = GameManager()


class ActionRequest(BaseModel):
    game_id: str
    player_id: int
    action: Dict[str, Any]


class CreateGameRequest(BaseModel):
    player_name: Optional[str] = None


@app.post("/api/game/create")
async def create_game(_: CreateGameRequest) -> Dict[str, Any]:
    game_id = manager.create_game()
    game = manager.get_game(game_id)
    for player_id in range(game.num_players):
        game.generate_shop(player_id)
    return {"game_id": game_id, "game_state": manager.serialize(game_id)}


@app.get("/api/game/{game_id}")
async def get_game(game_id: str) -> Dict[str, Any]:
    return manager.serialize(game_id)


@app.post("/api/game/action")
async def execute_action(request: ActionRequest) -> Dict[str, Any]:
    return await manager.apply_action(request.game_id, request.player_id, request.action)


@app.post("/api/game/{game_id}/shop")
async def generate_shop(game_id: str, player_id: int) -> Dict[str, Any]:
    game = manager.get_game(game_id)
    shop = game.generate_shop(player_id)
    return {"shop": [game.serialize_card(card) for card in shop]}


@app.post("/api/game/{game_id}/round/start")
async def start_round(game_id: str) -> Dict[str, Any]:
    await manager.start_round(game_id)
    return {"success": True}


@app.post("/api/game/{game_id}/ai-turn")
async def ai_turn(game_id: str, player_id: int) -> Dict[str, Any]:
    await manager.ai_turn(game_id, player_id)
    return {"success": True}


@app.post("/api/game/{game_id}/combat")
async def run_combat(game_id: str) -> Dict[str, Any]:
    await manager.run_combat(game_id)
    return {"success": True}


@app.get("/api/cards")
async def get_cards() -> Dict[str, Any]:
    db = manager.card_db
    return {
        "cards": [
            {
                "name": card.name,
                "sect": card.sect.value,
                "rarity": card.rarity.color,
                "cost": card.cost,
                "description": card.description,
            }
            for card in db.all_cards
        ],
        "sects": [sect.value for sect in Sect],
        "rarities": [rarity.color for rarity in Rarity],
    }


@app.websocket("/ws/game/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str) -> None:
    await websocket.accept()
    manager.connections[game_id].append(websocket)
    await websocket.send_json({"type": "connected", "game_state": manager.serialize(game_id)})

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.connections[game_id].remove(websocket)
    except Exception:
        if websocket in manager.connections[game_id]:
            manager.connections[game_id].remove(websocket)


@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "name": "Deck Battler API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "websocket": "/ws/game/{game_id}",
            "create_game": "POST /api/game/create",
            "cards": "GET /api/cards",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
