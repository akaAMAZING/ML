import React, { useState, useEffect, useRef } from 'react';
import {
  Camera,
  Zap,
  Heart,
  Coins,
  TrendingUp,
  Swords,
  Shield,
  Sparkles,
  Flame,
  Leaf,
  Moon,
  Sun,
  Wand2,
  Star,
  Trophy,
} from 'lucide-react';

const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000';

const rarityColors = {
  Grey: 'from-slate-700 to-slate-900',
  Green: 'from-emerald-600 to-emerald-800',
  Blue: 'from-sky-600 to-sky-800',
  Purple: 'from-purple-600 to-purple-800',
  Orange: 'from-orange-500 to-rose-600',
};

const sectIcons = {
  Iron: <Shield className="w-4 h-4 text-sky-300" />,
  Shadow: <Moon className="w-4 h-4 text-purple-300" />,
  Celestial: <Sun className="w-4 h-4 text-amber-200" />,
  Infernal: <Flame className="w-4 h-4 text-orange-400" />,
  Nature: <Leaf className="w-4 h-4 text-emerald-300" />,
  Arcane: <Wand2 className="w-4 h-4 text-indigo-300" />,
};

const sectAccent = {
  Iron: 'text-sky-300',
  Shadow: 'text-purple-300',
  Celestial: 'text-amber-200',
  Infernal: 'text-orange-400',
  Nature: 'text-emerald-300',
  Arcane: 'text-indigo-300',
};

const renderStars = (value) => {
  if (!value || value <= 0) {
    return <span className="text-xs text-slate-400">☆</span>;
  }
  return (
    <div className="flex items-center gap-0.5">
      {[...Array(value)].map((_, idx) => (
        <Star key={idx} className="w-3 h-3 text-yellow-400 fill-yellow-400" />
      ))}
    </div>
  );
};

const CardComponent = ({ card, onClick, disabled, collectionInfo, synergyInfo, showCost = true }) => {
  const info = collectionInfo || { currentStar: 0, currentCount: 0, progress: 0, nextGoal: 3 };
  const progressPercent = info.nextGoal ? Math.min(100, (info.progress / info.nextGoal) * 100) : 100;
  const rarityClass = rarityColors[card.rarity] || 'from-slate-700 to-slate-900';

  return (
    <div
      onClick={!disabled ? onClick : undefined}
      className={`relative bg-gradient-to-br ${rarityClass} rounded-xl p-3 border-2 border-slate-700/70 shadow-lg transition-all duration-200 ${
        !disabled ? 'cursor-pointer hover:-translate-y-1 hover:shadow-2xl' : 'opacity-50 cursor-not-allowed'
      }`}
    >
      {showCost && (
        <div className="absolute -top-2 -right-2 bg-yellow-400 text-slate-900 font-bold rounded-full w-9 h-9 flex items-center justify-center text-sm shadow-lg">
          {card.cost}
        </div>
      )}

      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-start gap-2">
          <div>{sectIcons[card.sect]}</div>
          <div>
            <h3 className="text-sm font-semibold text-white leading-tight">{card.name}</h3>
            <p className="text-[11px] uppercase tracking-wide text-slate-300/80">
              {card.sect} · {card.rarity}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 text-yellow-300">{renderStars(info.currentStar)}</div>
      </div>

      <p className="text-xs text-slate-100/90 leading-snug line-clamp-3 min-h-[48px]">{card.description}</p>

      {synergyInfo && (
        <p className="text-[11px] text-slate-300/80 mt-2 italic">{synergyInfo.tagline}</p>
      )}

      <div className="mt-3 space-y-1">
        <div className="flex justify-between text-[11px] text-slate-200/90">
          <span>
            {info.currentStar > 0 ? `Copies at ★${info.currentStar}: ${info.currentCount}` : 'No copies yet'}
          </span>
          <span>
            {info.nextGoal
              ? `${info.progress}/${info.nextGoal} to ★${info.currentStar + 1}`
              : 'Max rank achieved'}
          </span>
        </div>
        <div className="h-1.5 bg-slate-900/60 rounded-full overflow-hidden">
          <div
            className="h-full transition-all"
            style={{
              width: `${progressPercent}%`,
              background: 'linear-gradient(90deg, #facc15 0%, #f97316 100%)',
            }}
          />
        </div>
      </div>
    </div>
  );
};

const UnitComponent = ({ unit, onClick, canSell }) => {
  const hpPercent = (unit.hp / unit.max_hp) * 100;

  return (
    <div
      onClick={canSell ? onClick : undefined}
      className={`relative bg-slate-900/70 rounded-xl p-3 border border-slate-700/70 transition-all duration-200 shadow-inner ${
        canSell ? 'cursor-pointer hover:border-emerald-400/80 hover:shadow-emerald-500/20' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold text-white leading-tight">{unit.name}</h4>
          <div className="flex items-center gap-1 text-[11px]">
            <span className={sectAccent[unit.sect]}>{sectIcons[unit.sect]}</span>
            <span className={`uppercase tracking-wide ${sectAccent[unit.sect]}`}>{unit.sect}</span>
          </div>
        </div>
        <div className="flex items-center gap-1 text-yellow-300">
          {renderStars(unit.star_level)}
        </div>
      </div>

      <div className="mt-2 space-y-2 text-xs text-slate-200/90">
        <div className="flex items-center gap-2">
          <Heart className="w-3.5 h-3.5 text-rose-400" />
          <div className="flex-1 bg-slate-800/70 rounded-full h-2 overflow-hidden">
            <div
              className="bg-gradient-to-r from-emerald-400 to-cyan-400 h-full transition-all duration-300"
              style={{ width: `${hpPercent}%` }}
            />
          </div>
          <span>{Math.round(unit.hp)}/{Math.round(unit.max_hp)}</span>
        </div>
        <div className="flex justify-between text-[11px] text-slate-300/80">
          <span>⚔️ {Math.round(unit.atk)}</span>
          <span>🛡️ {Math.round(unit.defense)}</span>
          <span>⚡ {unit.speed.toFixed(2)}</span>
        </div>
      </div>

      {unit.abilities?.length > 0 && (
        <div className="mt-3 space-y-1">
          {unit.abilities.map((ability, idx) => (
            <div
              key={`${ability.name}-${idx}`}
              className="text-[11px] bg-slate-900/80 border border-slate-700/60 rounded-lg px-2 py-1 text-slate-200/90"
            >
              <span className="text-emerald-300 font-semibold">{ability.name}</span>
              {ability.description && <span className="text-slate-300 ml-1">— {ability.description}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const getSynergyProgress = (synergy) => {
  const levels = synergy.levels || [];
  const level = synergy.level || 0;
  const count = synergy.count || 0;
  if (level >= levels.length) {
    return 100;
  }
  const previous = level > 0 ? levels[level - 1].count : 0;
  const next = levels[level] || levels[levels.length - 1];
  const span = next.count - previous || 1;
  const progress = ((count - previous) / span) * 100;
  return Math.max(0, Math.min(100, progress));
};

const SynergyPanel = ({ synergies }) => {
  if (!synergies || synergies.length === 0) {
    return (
      <div className="bg-slate-900/70 border border-slate-700/70 rounded-xl p-4">
        <h3 className="text-lg font-semibold mb-2 flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-amber-300" />
          Faction Synergies
        </h3>
        <p className="text-sm text-slate-400">Recruit units to awaken your first synergy.</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/70 border border-slate-700/70 rounded-xl p-4 space-y-3">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        <Sparkles className="w-5 h-5 text-amber-300" />
        Faction Synergies
      </h3>
      <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
        {synergies.map((synergy) => {
          const progress = getSynergyProgress(synergy);
          const isDormant = (synergy.count || 0) === 0;
          return (
            <div
              key={synergy.sect}
              className={`rounded-lg border p-3 transition-all duration-200 ${
                isDormant ? 'border-slate-700/60 bg-slate-900/60 text-slate-400' : 'border-slate-600/70 bg-slate-900/80'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2">
                  <div>{sectIcons[synergy.sect]}</div>
                  <div>
                    <h4 className="text-sm font-semibold text-white">{synergy.name}</h4>
                    <p className="text-[11px] text-slate-300/80">{synergy.tagline}</p>
                  </div>
                </div>
                <div className="text-right text-xs text-slate-300/80">
                  <div>Level {synergy.level}</div>
                  <div>{synergy.count} units</div>
                </div>
              </div>

              <div className="mt-3 h-1.5 bg-slate-800/70 rounded-full overflow-hidden">
                <div
                  className="h-full"
                  style={{
                    width: `${progress}%`,
                    background: `linear-gradient(90deg, ${synergy.color} 0%, #ffffff 100%)`,
                  }}
                />
              </div>

              {synergy.active_bonuses?.length > 0 && (
                <ul className="mt-3 text-[11px] text-emerald-300 space-y-1">
                  {synergy.active_bonuses.map((bonus, idx) => (
                    <li key={idx} className="leading-snug">
                      ✅ {bonus}
                    </li>
                  ))}
                </ul>
              )}

              {synergy.next_threshold && (
                <div className="mt-2 text-[11px] text-slate-300/80">
                  <span className="font-semibold text-slate-100">Next ({synergy.next_threshold}): </span>
                  {synergy.next_bonus}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

const CollectionTracker = ({ inventory }) => {
  const entries = Object.entries(inventory || {}).sort(([a], [b]) => a.localeCompare(b));

  return (
    <div className="bg-slate-900/70 border border-slate-700/70 rounded-xl p-4">
      <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
        <Trophy className="w-5 h-5 text-yellow-400" />
        Collection Tracker
      </h3>
      {entries.length === 0 ? (
        <p className="text-sm text-slate-400">Purchase units to begin charting your mastery.</p>
      ) : (
        <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
          {entries.map(([name, starCounts]) => {
            const starEntries = Object.entries(starCounts)
              .map(([star, count]) => [Number(star), count])
              .sort((a, b) => a[0] - b[0]);
            const [highestStar, highestCount] = starEntries[starEntries.length - 1];
            const remainder = highestStar >= 3 ? 0 : highestCount % 3;
            const nextStar = highestStar >= 3 ? null : highestStar + 1;

            return (
              <div key={name} className="border border-slate-700/60 rounded-lg p-3 bg-slate-900/80">
                <div className="flex items-center justify-between gap-3">
                  <h4 className="text-sm font-semibold text-white">{name}</h4>
                  <div className="flex items-center gap-1 text-yellow-300">
                    {renderStars(highestStar)}
                    <span className="text-xs text-slate-300/80">★{highestStar}</span>
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-300/80">
                  {starEntries.map(([star, count]) => (
                    <span key={star} className="px-2 py-1 rounded bg-slate-800/70 border border-slate-700/60">
                      ★{star}: {count}
                    </span>
                  ))}
                </div>
                <div className="mt-2 text-[11px] text-emerald-300">
                  {nextStar ? (
                    <span>
                      {remainder}/3 copies towards ★{nextStar}
                    </span>
                  ) : (
                    <span>Legendary mastery achieved!</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

const CodexPanel = ({ definitions }) => {
  const entries = Object.entries(definitions || {});
  if (entries.length === 0) {
    return null;
  }

  return (
    <div className="bg-slate-900/70 border border-slate-700/70 rounded-xl p-4 space-y-3">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        <Shield className="w-5 h-5 text-sky-300" />
        Active Sect Codex
      </h3>
      <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
        {entries.map(([sect, info]) => (
          <div key={sect} className="border border-slate-700/60 rounded-lg p-3 bg-slate-900/80">
            <div className="flex items-start gap-2">
              <div>{sectIcons[sect]}</div>
              <div>
                <h4 className="text-sm font-semibold text-white">{info.name}</h4>
                <p className="text-[11px] text-slate-300/80">{info.tagline}</p>
              </div>
            </div>
            <ul className="mt-2 text-[11px] text-slate-200/90 space-y-1">
              {info.levels.map((level) => (
                <li key={`${sect}-${level.count}`}>
                  <span className="text-slate-100 font-semibold">[{level.count}] {level.title}:</span>{' '}
                  {level.description}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
};

const EventTicker = ({ highlights }) => {
  if (!highlights || highlights.length === 0) {
    return null;
  }
  return (
    <div className="bg-slate-900/70 border border-emerald-500/60 rounded-xl p-3 text-sm text-emerald-200 space-y-1 shadow-lg">
      {highlights.map((event, idx) => (
        <div key={`${event}-${idx}`} className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-emerald-300" />
          <span>{event}</span>
        </div>
      ))}
    </div>
  );
};

export default function DeckBattlerApp() {
  const [gameState, setGameState] = useState(null);
  const [gameId, setGameId] = useState(null);
  const [shop, setShop] = useState([]);
  const [phase, setPhase] = useState('menu');
  const [message, setMessage] = useState('');
  const [combatLog, setCombatLog] = useState([]);
  const [highlights, setHighlights] = useState([]);
  const wsRef = useRef(null);
  const gameIdRef = useRef(null);

  useEffect(() => {
    gameIdRef.current = gameId;
  }, [gameId]);

  const updateStateFromServer = (state) => {
    setGameState(state);
    if (state?.shops) {
      const playerShop = state.shops['0'] || state.shops[0] || [];
      setShop(playerShop);
    }
  };

  const createGame = async () => {
    try {
      const response = await fetch(`${API_URL}/api/game/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_name: 'You' }),
      });
      const data = await response.json();
      setGameId(data.game_id);
      gameIdRef.current = data.game_id;
      updateStateFromServer(data.game_state);
      connectWebSocket(data.game_id);
      setPhase('shop');
      setMessage('Welcome! Recruit units, chase synergies, and forge legends.');
      setCombatLog([]);
      setHighlights([]);
    } catch (error) {
      console.error('Error creating game:', error);
      setMessage('Error creating game');
    }
  };

  const connectWebSocket = (gId) => {
    const ws = new WebSocket(`${WS_URL}/ws/game/${gId}`);
    gameIdRef.current = gId;

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'connected') {
        updateStateFromServer(data.game_state);
      } else if (data.type === 'action_result') {
        updateStateFromServer(data.game_state);
        setMessage(data.result.message);
        if (data.result.fusion_events) {
          const fusionMessages = data.result.fusion_events.map(
            (evt) => `Fusion! ${evt.name} reached ★${evt.star_level}`,
          );
          setHighlights((prev) => [...fusionMessages, ...prev].slice(0, 6));
        }
      } else if (data.type === 'ai_thinking') {
        setMessage('AI is contemplating its master plan...');
      } else if (data.type === 'ai_action') {
        setCombatLog((prev) => [...prev, `AI ${data.action}: ${data.card?.name || ''}`]);
      } else if (data.type === 'ai_turn_complete') {
        updateStateFromServer(data.game_state);
        setMessage('AI finished its turn. Prepare for combat!');
        setTimeout(() => runCombat(), 1500);
      } else if (data.type === 'combat_start') {
        setPhase('combat');
        setCombatLog(['⚔️ COMBAT BEGINS!']);
      } else if (data.type === 'combat_tick') {
        // Hook for future real-time visualization.
      } else if (data.type === 'combat_end') {
        const winner = data.winner === 0 ? 'You' : 'AI';
        setCombatLog((prev) => [...prev, `${winner} won! Damage: ${data.damage}`]);
        updateStateFromServer(data.game_state);

        if (data.game_state.players[0].hp <= 0) {
          setPhase('gameOver');
          setMessage('💀 You were eliminated!');
        } else if (data.game_state.players[1].hp <= 0) {
          setPhase('gameOver');
          setMessage('🎉 VICTORY! You defeated the AI!');
        } else {
          setTimeout(() => startNextRound(), 2500);
        }
      } else if (data.type === 'round_start') {
        updateStateFromServer(data.game_state);
        setPhase('shop');
        setMessage(`Round ${data.round} - Your command phase begins.`);
        setCombatLog([]);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    wsRef.current = ws;
  };

  const buyCard = async (cardIdx) => {
    const id = gameIdRef.current;
    if (!id) return;

    try {
      await fetch(`${API_URL}/api/game/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: id,
          player_id: 0,
          action: { type: 'buy', card_idx: cardIdx },
        }),
      });
    } catch (error) {
      console.error('Error buying card:', error);
    }
  };

  const rerollShop = async () => {
    const id = gameIdRef.current;
    if (!id) return;
    try {
      await fetch(`${API_URL}/api/game/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: id,
          player_id: 0,
          action: { type: 'reroll' },
        }),
      });
    } catch (error) {
      console.error('Error rerolling shop:', error);
    }
  };

  const levelUp = async () => {
    const id = gameIdRef.current;
    if (!id) return;

    try {
      await fetch(`${API_URL}/api/game/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: id,
          player_id: 0,
          action: { type: 'level' },
        }),
      });
    } catch (error) {
      console.error('Error leveling up:', error);
    }
  };

  const sellUnit = async (deckIdx) => {
    const id = gameIdRef.current;
    if (!id) return;

    try {
      await fetch(`${API_URL}/api/game/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: id,
          player_id: 0,
          action: { type: 'sell', deck_idx: deckIdx },
        }),
      });
    } catch (error) {
      console.error('Error selling unit:', error);
    }
  };

  const endTurn = async () => {
    setMessage('Ending turn...');
    setPhase('waiting');

    try {
      const id = gameIdRef.current;
      if (!id) return;

      await fetch(`${API_URL}/api/game/${id}/ai-turn?player_id=1`, {
        method: 'POST',
      });
    } catch (error) {
      console.error('Error in AI turn:', error);
    }
  };

  const runCombat = async () => {
    try {
      const id = gameIdRef.current;
      if (!id) return;

      await fetch(`${API_URL}/api/game/${id}/combat`, {
        method: 'POST',
      });
    } catch (error) {
      console.error('Error in combat:', error);
    }
  };

  const startNextRound = async () => {
    try {
      const id = gameIdRef.current;
      if (!id) return;

      await fetch(`${API_URL}/api/game/${id}/round/start`, {
        method: 'POST',
      });
    } catch (error) {
      console.error('Error starting round:', error);
    }
  };

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const player = gameState?.players?.[0];
  const opponent = gameState?.players?.[1];
  const synergyDefinitions = gameState?.synergy_definitions || {};
  const inventory = player?.collection_inventory || {};
  const playerSynergies = player?.synergies || [];

  const getCollectionInfo = (name) => {
    const starCounts = inventory[name];
    if (!starCounts) {
      return { currentStar: 0, currentCount: 0, progress: 0, nextGoal: 3 };
    }
    const entries = Object.entries(starCounts)
      .map(([star, count]) => [Number(star), count])
      .sort((a, b) => a[0] - b[0]);
    const [currentStar, currentCount] = entries[entries.length - 1];
    const progress = currentStar >= 3 ? 0 : currentCount % 3;
    const nextGoal = currentStar >= 3 ? null : 3;
    return { currentStar, currentCount, progress, nextGoal };
  };

  const canPurchaseCard = (card) => {
    if (!player) return false;
    if (player.gold < card.cost) return false;
    if (!player.deck || player.deck.length < player.max_deck_size) return true;
    const duplicates = player.deck.filter((unit) => unit.name === card.name && unit.star_level === 1).length;
    return duplicates >= 2;
  };

  if (phase === 'menu') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-900 flex items-center justify-center p-4">
        <div className="text-center space-y-8 max-w-xl">
          <div className="space-y-4">
            <h1 className="text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-sky-400 via-purple-400 to-pink-400 animate-pulse">
              DECK BATTLER
            </h1>
            <p className="text-2xl text-slate-200">
              Build unstoppable combos, command sect synergies, and watch your deck ascend.
            </p>
          </div>

          <div className="flex gap-6 justify-center items-center text-slate-300">
            <Swords className="w-12 h-12 text-sky-400" />
            <Sparkles className="w-12 h-12 text-amber-300" />
            <Shield className="w-12 h-12 text-emerald-300" />
          </div>

          <button
            onClick={createGame}
            className="px-10 py-4 bg-gradient-to-r from-sky-600 to-purple-600 hover:from-sky-500 hover:to-purple-500 text-white font-bold text-xl rounded-xl shadow-2xl transform hover:scale-105 transition-all duration-200"
          >
            START YOUR ASCENT
          </button>

          <div className="text-slate-400 text-sm space-y-2">
            <p>Strategic auto-battler meets roguelite deck mastery.</p>
            <p>Fuse duplicates into star ascensions · Unlock sect boons · Survive 30 rounds to claim glory.</p>
          </div>
        </div>
      </div>
    );
  }

  if (phase === 'gameOver') {
    const isVictory = player?.hp > 0;
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-900 flex items-center justify-center p-4">
        <div className="text-center space-y-8 max-w-2xl">
          <h1 className={`text-6xl font-bold ${isVictory ? 'text-emerald-400' : 'text-rose-400'}`}>
            {isVictory ? '🎉 VICTORY!' : '💀 DEFEATED'}
          </h1>

          <div className="bg-slate-900/80 border border-slate-700/70 rounded-xl p-6 space-y-4 text-left">
            <h2 className="text-2xl text-white font-semibold">Campaign Summary</h2>
            <div className="grid grid-cols-2 gap-4 text-lg text-slate-200">
              <div>
                <p className="text-slate-400 text-sm uppercase tracking-wide">Rounds Survived</p>
                <p className="text-white font-bold text-3xl">{gameState?.current_round}</p>
              </div>
              <div>
                <p className="text-slate-400 text-sm uppercase tracking-wide">Final HP</p>
                <p className="text-white font-bold text-3xl">{player?.hp}</p>
              </div>
            </div>
          </div>

          <button
            onClick={() => {
              setPhase('menu');
              setGameState(null);
              setGameId(null);
              gameIdRef.current = null;
              setHighlights([]);
            }}
            className="px-8 py-4 bg-gradient-to-r from-sky-600 to-purple-600 hover:from-sky-500 hover:to-purple-500 text-white font-bold text-xl rounded-xl shadow-2xl transform hover:scale-105 transition-all duration-200"
          >
            PLAY AGAIN
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-900 text-white py-6 px-4">
      <div className="max-w-7xl mx-auto space-y-4">
        <div className="flex flex-wrap justify-between items-center gap-3">
          <div>
            <h1 className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-purple-500">
              Deck Battler Command Console
            </h1>
            <p className="text-sm text-slate-300">
              Round {gameState?.current_round || 0} / {gameState?.max_rounds || 30}
            </p>
          </div>
          <div className="text-sm text-amber-300 bg-slate-900/70 border border-amber-400/40 px-4 py-2 rounded-lg shadow-lg max-w-xl">
            {message}
          </div>
        </div>

        <EventTicker highlights={highlights} />

        <div className="grid xl:grid-cols-[1.25fr_0.75fr] gap-4">
          <div className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="bg-slate-900/70 border border-sky-500/60 rounded-xl p-4 space-y-3">
                <h2 className="text-xl font-bold flex items-center gap-2">
                  <Camera className="w-5 h-5 text-sky-300" />
                  You
                </h2>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <Heart className="w-5 h-5 text-rose-400" />
                    <div className="flex-1 bg-slate-800/70 rounded-full h-3 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-emerald-400 to-cyan-400 h-full transition-all duration-300"
                        style={{ width: `${Math.max(0, Math.min(100, (player?.hp || 0) / 100 * 100))}%` }}
                      />
                    </div>
                    <span className="font-bold">{player?.hp}/100</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Coins className="w-5 h-5 text-yellow-400" />
                    <span className="font-bold">{player?.gold}g</span>
                    <span className="text-xs text-slate-400">(+{player?.interest} interest)</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-emerald-400" />
                    <span>Level {player?.level}</span>
                    <button
                      onClick={levelUp}
                      disabled={!player || player.gold < 4 || player.level >= 8}
                      className="ml-auto px-3 py-1 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:opacity-50 rounded text-xs font-bold transition-all"
                    >
                      Level Up (4g)
                    </button>
                  </div>

                  <div className="flex gap-3 text-xs text-slate-300/80">
                    <span className="text-emerald-300">Win streak: {player?.win_streak || 0}</span>
                    <span className="text-rose-300">Lose streak: {player?.lose_streak || 0}</span>
                  </div>
                </div>
              </div>

              <div className="bg-slate-900/70 border border-rose-500/60 rounded-xl p-4 space-y-3">
                <h2 className="text-xl font-bold flex items-center gap-2">
                  <Swords className="w-5 h-5 text-rose-400" />
                  AI Opponent
                </h2>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <Heart className="w-5 h-5 text-rose-400" />
                    <div className="flex-1 bg-slate-800/70 rounded-full h-3 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-rose-500 to-red-500 h-full transition-all duration-300"
                        style={{ width: `${Math.max(0, Math.min(100, (opponent?.hp || 0) / 100 * 100))}%` }}
                      />
                    </div>
                    <span className="font-bold">{opponent?.hp}/100</span>
                  </div>

                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-purple-300" />
                    <span>Level {opponent?.level}</span>
                  </div>

                  <div className="flex gap-3 text-xs text-slate-300/80">
                    <span className="text-emerald-300">Win streak: {opponent?.win_streak || 0}</span>
                    <span className="text-rose-300">Lose streak: {opponent?.lose_streak || 0}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-slate-900/70 border border-slate-700/70 rounded-xl p-4">
              <h3 className="text-lg font-bold mb-3 flex items-center gap-2">
                <Shield className="w-5 h-5 text-sky-300" />
                Your Deck ({player?.deck?.length || 0}/{player?.max_deck_size || 0})
              </h3>
              <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-3">
                {player?.deck?.map((unit, idx) => (
                  <UnitComponent key={`${unit.name}-${idx}`} unit={unit} onClick={() => sellUnit(idx)} canSell={phase === 'shop'} />
                ))}
                {(!player?.deck || player.deck.length === 0) && (
                  <div className="col-span-full text-center text-slate-500 py-6">
                    No units yet – visit the shop to recruit your first hero.
                  </div>
                )}
              </div>
            </div>

            {phase === 'shop' && (
              <div className="grid lg:grid-cols-[1.2fr_0.8fr] gap-4">
                <div className="bg-slate-900/70 border border-slate-700/70 rounded-xl p-4">
                  <div className="flex justify-between items-center mb-3">
                    <h3 className="text-lg font-bold flex items-center gap-2">
                      <Sparkles className="w-5 h-5 text-yellow-300" />
                      Shop
                    </h3>
                    <button
                      onClick={rerollShop}
                      disabled={!player || player.gold < 2}
                      className="px-3 py-1 bg-purple-600 hover:bg-purple-500 disabled:bg-slate-700 disabled:opacity-50 rounded text-sm font-bold transition-all"
                    >
                      Reroll (2g)
                    </button>
                  </div>
                  <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-3">
                    {shop.map((card, idx) => (
                      <CardComponent
                        key={`${card.name}-${idx}`}
                        card={card}
                        onClick={() => buyCard(idx)}
                        disabled={!canPurchaseCard(card)}
                        collectionInfo={getCollectionInfo(card.name)}
                        synergyInfo={synergyDefinitions[card.sect]}
                      />
                    ))}
                  </div>
                </div>

                <CollectionTracker inventory={inventory} />
              </div>
            )}

            {phase === 'shop' && (
              <button
                onClick={endTurn}
                className="w-full py-4 bg-gradient-to-r from-emerald-600 to-sky-600 hover:from-emerald-500 hover:to-sky-500 text-white font-bold text-xl rounded-xl shadow-xl transform hover:scale-105 transition-all duration-200"
              >
                End Turn & Commence Battle
              </button>
            )}
          </div>

          <div className="space-y-4">
            <SynergyPanel synergies={playerSynergies} />

            <div className="bg-slate-900/70 border border-slate-700/70 rounded-xl p-4">
              <h3 className="text-lg font-bold mb-3 flex items-center gap-2">
                <Swords className="w-5 h-5 text-rose-400" />
                Opponent Deck ({opponent?.deck?.length || 0}/{opponent?.max_deck_size || 0})
              </h3>
              <div className="grid sm:grid-cols-2 gap-3">
                {opponent?.deck?.map((unit, idx) => (
                  <UnitComponent key={`${unit.name}-enemy-${idx}`} unit={unit} canSell={false} />
                ))}
                {(!opponent?.deck || opponent.deck.length === 0) && (
                  <div className="col-span-full text-center text-slate-500 py-6">AI has no units recruited.</div>
                )}
              </div>
            </div>

            <div className="bg-slate-900/70 border border-slate-700/70 rounded-xl p-4">
              <h3 className="text-lg font-bold mb-3 flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-300" />
                Combat Log
              </h3>
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {combatLog.length > 0 ? (
                  combatLog.map((log, idx) => (
                    <div key={`${log}-${idx}`} className="text-sm text-slate-200 bg-slate-900/80 px-3 py-2 rounded border border-slate-700/60">
                      {log}
                    </div>
                  ))
                ) : (
                  <div className="text-center text-slate-500 py-6">No combat yet. Assemble your forces and engage!</div>
                )}
              </div>
            </div>

            <CodexPanel definitions={synergyDefinitions} />
          </div>
        </div>
      </div>
    </div>
  );
}
