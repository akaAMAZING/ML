"""
DECK BATTLER - FastAPI WebSocket Backend
=========================================

Real-time game server with WebSocket support for live updates.

SETUP:
pip install fastapi uvicorn websockets python-multipart

RUN:
uvicorn backend:app --reload --host 0.0.0.0 --port 8000

ENDPOINTS:
- WS /ws/game/{game_id} - Real-time game updates
- POST /api/game/create - Create new game
- POST /api/game/action - Execute player action
- GET /api/cards - Get card database
- GET /api/agent/stats - Get AI statistics
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import asyncio
import json
import uuid
from collections import defaultdict

# Import our game engine
import sys
sys.path.append('.')
from deck_battler import (
    GameState, PlayerState, DeckBattlerAgent, CardDatabase, 
    CombatEngine, Card, Unit, Sect, Rarity
)

app = FastAPI(title="Deck Battler API")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# GAME MANAGER
# ============================================================================

class GameManager:
    """Manages active games and WebSocket connections"""
    def __init__(self):
        self.active_games: Dict[str, GameState] = {}
        self.game_connections: Dict[str, List[WebSocket]] = defaultdict(list)
        self.ai_agent = None
        self.card_db = CardDatabase()
        
    async def load_ai_agent(self):
        """Load trained AI agent"""
        if self.ai_agent is None:
            self.ai_agent = DeckBattlerAgent()
            try:
                self.ai_agent.load("best_agent.pth")
                print("✓ Loaded trained AI agent")
            except:
                print("⚠ No trained agent found, using random AI")
    
    def create_game(self, human_player_id: int = 0) -> str:
        """Create new game"""
        game_id = str(uuid.uuid4())
        game = GameState(num_players=2)  # Human vs AI
        self.active_games[game_id] = game
        return game_id
    
    async def broadcast(self, game_id: str, message: Dict):
        """Broadcast message to all connected clients"""
        if game_id in self.game_connections:
            dead_connections = []
            for ws in self.game_connections[game_id]:
                try:
                    await ws.send_json(message)
                except:
                    dead_connections.append(ws)
            
            # Clean up dead connections
            for ws in dead_connections:
                self.game_connections[game_id].remove(ws)
    
    def serialize_unit(self, unit: Unit) -> Dict:
        """Serialize unit for JSON"""
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
            "abilities": [{"name": a.name, "description": a.description} for a in unit.abilities],
        }
    
    def serialize_card(self, card: Card) -> Dict:
        """Serialize card for JSON"""
        return {
            "name": card.name,
            "sect": card.sect.value,
            "rarity": card.rarity.color,
            "cost": card.cost,
            "description": card.description,
        }
    
    def serialize_player(self, player: PlayerState) -> Dict:
        """Serialize player state"""
        return {
            "player_id": player.player_id,
            "hp": player.hp,
            "gold": player.gold,
            "level": player.level,
            "win_streak": player.win_streak,
            "lose_streak": player.lose_streak,
            "deck": [self.serialize_unit(u) for u in player.deck],
            "max_deck_size": player.get_max_deck_size(),
            "interest": player.get_interest(),
            "streak_bonus": player.get_streak_bonus(),
        }
    
    def get_game_state(self, game_id: str) -> Dict:
        """Get full game state"""
        game = self.active_games.get(game_id)
        if not game:
            return None
        
        return {
            "game_id": game_id,
            "current_round": game.current_round,
            "max_rounds": game.max_rounds,
            "is_game_over": game.is_game_over(),
            "active_sects": [s.value for s in game.active_sects],
            "active_legendaries": {
                sect.value: [self.serialize_card(c) for c in cards]
                for sect, cards in game.active_legendaries.items()
            },
            "players": [self.serialize_player(p) for p in game.players],
        }
    
    async def execute_action(self, game_id: str, player_id: int, action: Dict) -> Dict:
        """Execute player action and return result"""
        game = self.active_games.get(game_id)
        if not game:
            raise ValueError("Game not found")
        
        player = game.players[player_id]
        result = {"success": False, "message": ""}
        
        action_type = action.get("type")
        
        if action_type == "buy":
            card_idx = action.get("card_idx")
            shop = action.get("shop", [])
            if 0 <= card_idx < len(shop):
                card_data = shop[card_idx]
                # Reconstruct card from data
                for card in game.card_db.all_cards:
                    if card.name == card_data["name"]:
                        if player.gold >= card.cost:
                            player.gold -= card.cost
                            if card.create_unit:
                                unit = card.create_unit()
                                if player.add_to_deck(unit):
                                    result = {
                                        "success": True,
                                        "message": f"Bought {card.name}",
                                        "card": card_data
                                    }
                                else:
                                    player.gold += card.cost
                                    result = {"success": False, "message": "Deck full"}
                        else:
                            result = {"success": False, "message": "Not enough gold"}
                        break
        
        elif action_type == "level":
            if player.can_level_up():
                player.level_up()
                result = {"success": True, "message": f"Leveled up to {player.level}"}
            else:
                result = {"success": False, "message": "Cannot level up"}
        
        elif action_type == "sell":
            deck_idx = action.get("deck_idx")
            if 0 <= deck_idx < len(player.deck):
                unit = player.deck.pop(deck_idx)
                player.gold += 2
                result = {"success": True, "message": f"Sold {unit.name}", "gold_refund": 2}
            else:
                result = {"success": False, "message": "Invalid deck index"}
        
        elif action_type == "end_turn":
            result = {"success": True, "message": "Turn ended"}
        
        # Broadcast updated state
        await self.broadcast(game_id, {
            "type": "action_result",
            "action": action,
            "result": result,
            "game_state": self.get_game_state(game_id)
        })
        
        return result
    
    async def run_ai_turn(self, game_id: str, ai_player_id: int):
        """Let AI make decisions"""
        await self.load_ai_agent()
        game = self.active_games.get(game_id)
        if not game:
            return
        
        player = game.players[ai_player_id]
        
        # Generate shop
        shop = game.card_db.generate_shop(
            player.level,
            game.active_sects,
            game.active_legendaries
        )
        
        # Broadcast AI thinking
        await self.broadcast(game_id, {
            "type": "ai_thinking",
            "player_id": ai_player_id,
            "shop": [self.serialize_card(c) for c in shop]
        })
        
        # AI makes decisions (simplified for now)
        actions_taken = 0
        max_actions = 5
        
        while actions_taken < max_actions and player.gold > 0:
            # Encode state
            state = self.ai_agent.encode_state(player, game, shop)
            
            # Get AI action
            action_idx, _, _ = self.ai_agent.select_action(state, deterministic=True)
            action_dict = self.ai_agent.decode_action(action_idx, player, shop)
            
            if action_dict["type"] == "pass":
                break
            
            # Execute action
            if action_dict["type"] == "buy":
                card_idx = action_dict.get("card_idx")
                if card_idx < len(shop):
                    card = shop[card_idx]
                    if player.gold >= card.cost and len(player.deck) < player.get_max_deck_size():
                        player.gold -= card.cost
                        unit = card.create_unit()
                        player.add_to_deck(unit)
                        
                        await self.broadcast(game_id, {
                            "type": "ai_action",
                            "action": "buy",
                            "card": self.serialize_card(card),
                            "player_id": ai_player_id
                        })
                        
                        await asyncio.sleep(0.5)  # Dramatic pause
            
            elif action_dict["type"] == "level" and player.can_level_up():
                player.level_up()
                await self.broadcast(game_id, {
                    "type": "ai_action",
                    "action": "level",
                    "new_level": player.level,
                    "player_id": ai_player_id
                })
                await asyncio.sleep(0.3)
            
            actions_taken += 1
        
        # Broadcast AI turn complete
        await self.broadcast(game_id, {
            "type": "ai_turn_complete",
            "player_id": ai_player_id,
            "game_state": self.get_game_state(game_id)
        })
    
    async def run_combat(self, game_id: str):
        """Run combat phase with live updates"""
        game = self.active_games.get(game_id)
        if not game:
            return
        
        # Broadcast combat start
        await self.broadcast(game_id, {
            "type": "combat_start",
            "round": game.current_round
        })
        
        await asyncio.sleep(1)
        
        # Run combat
        player1 = game.players[0]
        player2 = game.players[1]
        
        if player1.deck and player2.deck:
            combat = CombatEngine()
            won, damage = combat.simulate_combat(player1.deck, player2.deck)
            
            # Send combat events
            await self.broadcast(game_id, {
                "type": "combat_tick",
                "team_a": [self.serialize_unit(u) for u in combat.team_a],
                "team_b": [self.serialize_unit(u) for u in combat.team_b],
            })
            
            await asyncio.sleep(2)  # Let combat play out
            
            # Apply results
            if won:
                player2.take_damage(damage)
                player1.win_streak += 1
                player1.lose_streak = 0
                player2.win_streak = 0
                player2.lose_streak += 1
            else:
                player1.take_damage(damage)
                player2.win_streak += 1
                player2.lose_streak = 0
                player1.win_streak = 0
                player1.lose_streak += 1
            
            # Broadcast result
            await self.broadcast(game_id, {
                "type": "combat_end",
                "winner": 0 if won else 1,
                "damage": damage,
                "game_state": self.get_game_state(game_id)
            })
        
        game.current_round += 1

# Global game manager
manager = GameManager()

# ============================================================================
# API MODELS
# ============================================================================

class ActionRequest(BaseModel):
    game_id: str
    player_id: int
    action: Dict[str, Any]

class CreateGameRequest(BaseModel):
    player_name: Optional[str] = "Player 1"

# ============================================================================
# REST API ENDPOINTS
# ============================================================================

@app.post("/api/game/create")
async def create_game(request: CreateGameRequest):
    """Create new game"""
    game_id = manager.create_game()
    game_state = manager.get_game_state(game_id)
    return {
        "game_id": game_id,
        "game_state": game_state
    }

@app.post("/api/game/action")
async def execute_action(request: ActionRequest):
    """Execute player action"""
    try:
        result = await manager.execute_action(
            request.game_id,
            request.player_id,
            request.action
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/cards")
async def get_cards():
    """Get all cards in database"""
    return {
        "cards": [manager.serialize_card(c) for c in manager.card_db.all_cards],
        "sects": [s.value for s in Sect],
        "rarities": [r.color for r in Rarity]
    }

@app.get("/api/game/{game_id}")
async def get_game(game_id: str):
    """Get game state"""
    state = manager.get_game_state(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    return state

@app.post("/api/game/{game_id}/shop")
async def generate_shop(game_id: str, player_id: int):
    """Generate shop for player"""
    game = manager.active_games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    player = game.players[player_id]
    shop = game.card_db.generate_shop(
        player.level,
        game.active_sects,
        game.active_legendaries
    )
    
    return {
        "shop": [manager.serialize_card(c) for c in shop]
    }

@app.post("/api/game/{game_id}/round/start")
async def start_round(game_id: str):
    """Start new round"""
    game = manager.active_games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Income phase
    for player in game.get_alive_players():
        player.earn_gold()
    
    await manager.broadcast(game_id, {
        "type": "round_start",
        "round": game.current_round + 1,
        "game_state": manager.get_game_state(game_id)
    })
    
    return {"success": True}

@app.post("/api/game/{game_id}/combat")
async def run_combat(game_id: str):
    """Run combat phase"""
    await manager.run_combat(game_id)
    return {"success": True}

@app.post("/api/game/{game_id}/ai-turn")
async def ai_turn(game_id: str, player_id: int):
    """Let AI take its turn"""
    await manager.run_ai_turn(game_id, player_id)
    return {"success": True}

# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws/game/{game_id}")
async def game_websocket(websocket: WebSocket, game_id: str):
    """WebSocket for real-time game updates"""
    await websocket.accept()
    manager.game_connections[game_id].append(websocket)
    
    try:
        # Send initial game state
        game_state = manager.get_game_state(game_id)
        if game_state:
            await websocket.send_json({
                "type": "connected",
                "game_state": game_state
            })
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            
            # Handle different message types
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
    except WebSocketDisconnect:
        manager.game_connections[game_id].remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in manager.game_connections[game_id]:
            manager.game_connections[game_id].remove(websocket)

@app.get("/")
async def root():
    return {
        "name": "Deck Battler API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "websocket": "/ws/game/{game_id}",
            "create_game": "POST /api/game/create",
            "cards": "GET /api/cards"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Deck Battler Backend Server")
    print("📡 WebSocket: ws://localhost:8000/ws/game/{game_id}")
    print("🌐 API Docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)