# Deck Battler Command Center

Welcome to the lovingly rebuilt Deck Battler project. This repository delivers a playable auto-battler sandbox, a modern web dashboard, and the foundations for AI experimentation. Every subsystem has been rewritten for clarity and joy – from the combat rules to the development workflow.

## Project Highlights

- **Modular Python engine** – the new `deck_battler` package cleanly separates cards, combat, game state, and agent logic so you can tweak systems without spelunking through a monolith.
- **FastAPI backend** – a lightweight real-time API with WebSocket updates keeps the UI in sync with every shop reroll, combat round, and AI move.
- **React + Tailwind UI** – a polished command center where you can manage your deck, follow combat logs, and monitor both players’ boards in real time.
- **Self-play sandbox** – simulate matches between heuristic agents with `SelfPlaySession` to generate data or baseline behaviours for future reinforcement learning experiments.

## Repository Layout

```
.
├── backend.py               # FastAPI application
├── deck_battler/            # Core engine package
│   ├── agent.py             # Heuristic AI
│   ├── cards.py             # Card database and ability definitions
│   ├── combat.py            # Tick-based combat simulator
│   ├── enums.py             # Shared enums
│   ├── game.py              # Game orchestration and serialization helpers
│   ├── models.py            # Card/unit dataclasses
│   ├── player.py            # Economy + deck management
│   └── training.py          # Self-play helpers
├── deck-battler-ui/         # Vite + React front-end
│   ├── index.html
│   ├── package.json
│   └── src/
│       ├── App.jsx          # Main dashboard
│       ├── index.css        # Tailwind entrypoint
│       └── main.jsx         # React bootstrapping
├── requirements.txt         # Python dependencies
└── README.md
```

## Prerequisites

- **Python 3.11+** (virtual environments highly recommended)
- **Node.js 18+** (ships with npm)

## Backend – FastAPI Service

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Launch the server:

   ```bash
   uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
   ```

   The API is now live at <http://localhost:8000>. Open <http://localhost:8000/docs> for interactive Swagger documentation.

### Useful Endpoints

- `POST /api/game/create` – start a new human vs AI game.
- `POST /api/game/action` – send shop actions (buy, sell, level, reroll).
- `POST /api/game/{game_id}/ai-turn` – trigger the AI’s shop phase.
- `POST /api/game/{game_id}/combat` – resolve combat for the current round.
- `WS /ws/game/{game_id}` – subscribe to real-time updates (shop refreshes, combat status, AI events).

## Front-end – React Dashboard

1. Install dependencies:

   ```bash
   cd deck-battler-ui
   npm install
   ```

2. Start the Vite dev server:

   ```bash
   npm run dev
   ```

3. Visit the UI at the URL shown in the console (default: <http://localhost:5173>). The dashboard expects the backend to run at `http://localhost:8000`.

### Front-end Features

- Full-screen command center styled with Tailwind.
- Dynamic shop management (reroll, buy, sell, level) with WebSocket-powered updates.
- Combat log stream and side-by-side board visualisation.
- Status bars for HP, gold, streaks, and sect synergies.

## Playing a Match

1. Start both the backend and frontend servers.
2. Open the UI and hit **START GAME**.
3. During the shop phase:
   - Click cards in the shop to buy them (cost and deck capacity enforced).
   - Click your units to sell them for a partial refund.
   - Use **Level Up** (4 gold) and **Reroll** (2 gold) to sculpt your board.
4. Hit **END TURN & FIGHT** to let the AI take its turn and then watch combat.
5. After combat resolves, start the next round to receive income and a fresh shop.

Victory is achieved by reducing the AI’s HP to zero before yours hits zero.

## AI & Self-Play Sandbox

The current AI is a deterministic heuristic that focuses on building cohesive sects and levelling when it can afford to. Use `SelfPlaySession` to simulate games:

```python
from deck_battler.training import SelfPlaySession

session = SelfPlaySession(episodes=20)
results = session.run()

for idx, result in enumerate(results, start=1):
    print(f"Episode {idx}: winner={result.winner}, rounds={result.rounds}, damage={result.damage_dealt}")
```

This provides a foundation for plugging in reinforcement learning or imitation learning in the future. The modular architecture keeps combat, economy, and card logic isolated, making it straightforward to integrate PPO, population-based training, or curriculum systems down the road.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Front-end cannot connect to API | Confirm the backend is running on port 8000 and CORS is configured for your origin. |
| WebSocket disconnects immediately | Ensure you are using `ws://localhost:8000/ws/game/{game_id}` and that the game exists. |
| Tailwind classes not applied | Run `npm run dev` inside `deck-battler-ui`; Tailwind compiles on the fly. |
| Reroll button does nothing | You must have at least 2 gold; otherwise the action is rejected and the backend sends an error message. |

## Roadmap Ideas

- Expand the card pool with talents and suppressions alongside units.
- Upgrade the AI to a PPO agent trained via self-play using the provided combat simulator.
- Add analytics overlays (damage charts, synergy matrices) to the UI.
- Persist training runs and deck histories in a database for meta-analysis.

---

Enjoy crafting the ultimate deck battler laboratory. Tinker, iterate, and have fun! 💜
