import React, { useState, useEffect, useRef } from 'react';
import { Camera, Zap, Heart, Coins, TrendingUp, Swords, Shield, Sparkles } from 'lucide-react';

const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000';

// Card component with beautiful styling
const CardComponent = ({ card, onClick, disabled, isInDeck, showCost = true }) => {
  const rarityColors = {
    'Grey': 'from-gray-600 to-gray-800',
    'Green': 'from-green-600 to-green-800',
    'Blue': 'from-blue-600 to-blue-800',
    'Purple': 'from-purple-600 to-purple-800',
    'Orange': 'from-orange-500 to-red-600',
  };

  const sectIcons = {
    'Iron': <Shield className="w-4 h-4" />,
    'Shadow': <Zap className="w-4 h-4" />,
    'Celestial': <Sparkles className="w-4 h-4" />,
    'Infernal': <Sparkles className="w-4 h-4" />,
    'Nature': <Sparkles className="w-4 h-4" />,
    'Arcane': <Sparkles className="w-4 h-4" />,
  };

  return (
    <div
      onClick={!disabled ? onClick : undefined}
      className={`
        relative bg-gradient-to-br ${rarityColors[card.rarity] || 'from-gray-700 to-gray-900'}
        rounded-lg p-3 border-2 border-opacity-50
        ${!disabled ? 'cursor-pointer hover:scale-105 hover:shadow-2xl' : 'opacity-50'}
        transition-all duration-200
        ${isInDeck ? 'border-yellow-400' : 'border-white'}
      `}
    >
      {showCost && (
        <div className="absolute -top-2 -right-2 bg-yellow-500 text-black font-bold rounded-full w-8 h-8 flex items-center justify-center text-sm shadow-lg">
          {card.cost}
        </div>
      )}
      
      <div className="flex items-center gap-2 mb-2">
        <div className="text-yellow-400">
          {sectIcons[card.sect]}
        </div>
        <h3 className="text-white font-bold text-sm">{card.name}</h3>
      </div>
      
      <div className="text-xs text-gray-300 mb-1">
        {card.sect} · {card.rarity}
      </div>
      
      <p className="text-xs text-gray-400 line-clamp-2">
        {card.description}
      </p>
    </div>
  );
};

// Unit component for deck display
const UnitComponent = ({ unit, onClick, canSell }) => {
  const hpPercent = (unit.hp / unit.max_hp) * 100;
  
  return (
    <div
      onClick={canSell ? onClick : undefined}
      className={`
        relative bg-gradient-to-br from-gray-800 to-gray-900
        rounded-lg p-2 border border-gray-600
        ${canSell ? 'cursor-pointer hover:border-red-500' : ''}
        transition-all duration-200
      `}
    >
      {unit.star_level > 1 && (
        <div className="absolute -top-1 -right-1 flex gap-0.5">
          {[...Array(unit.star_level)].map((_, i) => (
            <Sparkles key={i} className="w-3 h-3 text-yellow-400 fill-yellow-400" />
          ))}
        </div>
      )}
      
      <h4 className="text-white font-semibold text-xs mb-1">{unit.name}</h4>
      
      <div className="space-y-1">
        <div className="flex items-center gap-1">
          <Heart className="w-3 h-3 text-red-500" />
          <div className="flex-1 bg-gray-700 rounded-full h-2 overflow-hidden">
            <div 
              className="bg-red-500 h-full transition-all duration-300"
              style={{ width: `${hpPercent}%` }}
            />
          </div>
          <span className="text-xs text-white">{Math.floor(unit.hp)}/{unit.max_hp}</span>
        </div>
        
        <div className="flex gap-2 text-xs">
          <span className="text-orange-400">⚔️ {unit.atk}</span>
          <span className="text-blue-400">🛡️ {unit.defense}</span>
          <span className="text-green-400">⚡ {unit.speed}</span>
        </div>
      </div>
    </div>
  );
};

// Main App Component
export default function DeckBattlerApp() {
  const [gameState, setGameState] = useState(null);
  const [gameId, setGameId] = useState(null);
  const [shop, setShop] = useState([]);
  const [phase, setPhase] = useState('menu'); // menu, shop, combat, gameOver
  const [message, setMessage] = useState('');
  const [combatLog, setCombatLog] = useState([]);
  const wsRef = useRef(null);

  // Create new game
  const createGame = async () => {
    try {
      const response = await fetch(`${API_URL}/api/game/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_name: 'You' })
      });
      const data = await response.json();
      setGameId(data.game_id);
      setGameState(data.game_state);
      connectWebSocket(data.game_id);
      
      // Generate initial shop
      await generateShop(data.game_id, 0);
      setPhase('shop');
      setMessage('Welcome! Buy cards and build your deck!');
    } catch (error) {
      console.error('Error creating game:', error);
      setMessage('Error creating game');
    }
  };

  // Connect WebSocket
  const connectWebSocket = (gId) => {
    const ws = new WebSocket(`${WS_URL}/ws/game/${gId}`);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('WS Message:', data);
      
      if (data.type === 'connected') {
        setGameState(data.game_state);
      } else if (data.type === 'action_result') {
        setGameState(data.game_state);
        setMessage(data.result.message);
      } else if (data.type === 'ai_thinking') {
        setMessage('AI is thinking...');
      } else if (data.type === 'ai_action') {
        setCombatLog(prev => [...prev, `AI ${data.action}: ${data.card?.name || ''}`]);
      } else if (data.type === 'ai_turn_complete') {
        setGameState(data.game_state);
        setMessage('AI finished its turn. Starting combat...');
        setTimeout(() => runCombat(), 2000);
      } else if (data.type === 'combat_start') {
        setPhase('combat');
        setCombatLog(['⚔️ COMBAT BEGINS!']);
      } else if (data.type === 'combat_tick') {
        // Update combat visualization
      } else if (data.type === 'combat_end') {
        const winner = data.winner === 0 ? 'You' : 'AI';
        setCombatLog(prev => [...prev, `${winner} won! Damage: ${data.damage}`]);
        setGameState(data.game_state);
        
        // Check game over
        if (data.game_state.players[0].hp <= 0) {
          setPhase('gameOver');
          setMessage('💀 You were eliminated!');
        } else if (data.game_state.players[1].hp <= 0) {
          setPhase('gameOver');
          setMessage('🎉 VICTORY! You defeated the AI!');
        } else {
          setTimeout(() => startNextRound(), 3000);
        }
      } else if (data.type === 'round_start') {
        setGameState(data.game_state);
        generateShop(gameId, 0);
        setPhase('shop');
        setMessage(`Round ${data.round} - Your turn!`);
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

  // Generate shop
  const generateShop = async (gId, playerId) => {
    try {
      const response = await fetch(`${API_URL}/api/game/${gId}/shop?player_id=${playerId}`, {
        method: 'POST'
      });
      const data = await response.json();
      setShop(data.shop);
    } catch (error) {
      console.error('Error generating shop:', error);
    }
  };

  // Buy card
  const buyCard = async (cardIdx) => {
    if (!gameId) return;
    
    try {
      await fetch(`${API_URL}/api/game/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          player_id: 0,
          action: { type: 'buy', card_idx: cardIdx, shop: shop }
        })
      });
    } catch (error) {
      console.error('Error buying card:', error);
    }
  };

  // Level up
  const levelUp = async () => {
    if (!gameId) return;
    
    try {
      await fetch(`${API_URL}/api/game/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          player_id: 0,
          action: { type: 'level' }
        })
      });
    } catch (error) {
      console.error('Error leveling up:', error);
    }
  };

  // Sell unit
  const sellUnit = async (deckIdx) => {
    if (!gameId) return;
    
    try {
      await fetch(`${API_URL}/api/game/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: gameId,
          player_id: 0,
          action: { type: 'sell', deck_idx: deckIdx }
        })
      });
    } catch (error) {
      console.error('Error selling unit:', error);
    }
  };

  // End turn (start AI turn and combat)
  const endTurn = async () => {
    setMessage('Ending turn...');
    setPhase('waiting');
    
    try {
      // AI takes turn
      await fetch(`${API_URL}/api/game/${gameId}/ai-turn?player_id=1`, {
        method: 'POST'
      });
    } catch (error) {
      console.error('Error in AI turn:', error);
    }
  };

  // Run combat
  const runCombat = async () => {
    try {
      await fetch(`${API_URL}/api/game/${gameId}/combat`, {
        method: 'POST'
      });
    } catch (error) {
      console.error('Error in combat:', error);
    }
  };

  // Start next round
  const startNextRound = async () => {
    try {
      await fetch(`${API_URL}/api/game/${gameId}/round/start`, {
        method: 'POST'
      });
    } catch (error) {
      console.error('Error starting round:', error);
    }
  };

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const player = gameState?.players[0];
  const opponent = gameState?.players[1];

  // Menu screen
  if (phase === 'menu') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 flex items-center justify-center p-4">
        <div className="text-center space-y-8">
          <div className="space-y-4">
            <h1 className="text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 animate-pulse">
              DECK BATTLER
            </h1>
            <p className="text-2xl text-gray-300">Build. Battle. Dominate.</p>
          </div>
          
          <div className="flex gap-4 justify-center items-center">
            <Swords className="w-12 h-12 text-blue-400" />
            <Sparkles className="w-12 h-12 text-purple-400" />
            <Shield className="w-12 h-12 text-pink-400" />
          </div>
          
          <button
            onClick={createGame}
            className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-bold text-xl rounded-lg shadow-2xl transform hover:scale-105 transition-all duration-200"
          >
            START GAME
          </button>
          
          <div className="text-gray-400 text-sm space-y-2">
            <p>Face the AI in strategic auto-battler combat</p>
            <p>6 Sects • Legendary Cards • Deep Strategy</p>
          </div>
        </div>
      </div>
    );
  }

  // Game over screen
  if (phase === 'gameOver') {
    const isVictory = player?.hp > 0;
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 flex items-center justify-center p-4">
        <div className="text-center space-y-8 max-w-2xl">
          <h1 className={`text-6xl font-bold ${isVictory ? 'text-green-400' : 'text-red-400'}`}>
            {isVictory ? '🎉 VICTORY!' : '💀 DEFEATED'}
          </h1>
          
          <div className="bg-gray-800 bg-opacity-50 rounded-lg p-6 space-y-4">
            <h2 className="text-2xl text-white">Game Stats</h2>
            <div className="grid grid-cols-2 gap-4 text-lg">
              <div className="text-gray-300">
                <p>Rounds Survived</p>
                <p className="text-white font-bold text-2xl">{gameState?.current_round}</p>
              </div>
              <div className="text-gray-300">
                <p>Final HP</p>
                <p className="text-white font-bold text-2xl">{player?.hp}</p>
              </div>
            </div>
          </div>
          
          <button
            onClick={() => {
              setPhase('menu');
              setGameState(null);
              setGameId(null);
            }}
            className="px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-bold text-xl rounded-lg shadow-2xl transform hover:scale-105 transition-all duration-200"
          >
            PLAY AGAIN
          </button>
        </div>
      </div>
    );
  }

  // Main game screen
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 text-white p-4">
      {/* Header */}
      <div className="mb-4 flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">
            DECK BATTLER
          </h1>
          <div className="text-sm text-gray-400">
            Round {gameState?.current_round || 0}
          </div>
        </div>
        
        <div className="text-sm text-yellow-400 bg-gray-800 px-4 py-2 rounded-lg">
          {message}
        </div>
      </div>

      {/* Player Stats Row */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Your Stats */}
        <div className="bg-gradient-to-r from-blue-900 to-blue-800 rounded-lg p-4 border-2 border-blue-400">
          <h2 className="text-xl font-bold mb-3 flex items-center gap-2">
            <Camera className="w-5 h-5" />
            YOU
          </h2>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Heart className="w-5 h-5 text-red-500" />
              <div className="flex-1">
                <div className="bg-gray-700 rounded-full h-3 overflow-hidden">
                  <div 
                    className="bg-red-500 h-full transition-all duration-300"
                    style={{ width: `${(player?.hp / 100) * 100}%` }}
                  />
                </div>
              </div>
              <span className="font-bold">{player?.hp}/100</span>
            </div>
            
            <div className="flex items-center gap-2">
              <Coins className="w-5 h-5 text-yellow-500" />
              <span className="font-bold">{player?.gold}g</span>
              <span className="text-xs text-gray-400">(+{player?.interest} interest)</span>
            </div>
            
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-500" />
              <span>Level {player?.level}</span>
              <button
                onClick={levelUp}
                disabled={!player || player.gold < 4 || player.level >= 8}
                className="ml-auto px-2 py-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:opacity-50 rounded text-xs font-bold transition-all"
              >
                Level Up (4g)
              </button>
            </div>
            
            <div className="flex gap-2 text-sm">
              <span className="text-green-400">Win: {player?.win_streak || 0}</span>
              <span className="text-red-400">Loss: {player?.lose_streak || 0}</span>
            </div>
          </div>
        </div>

        {/* Opponent Stats */}
        <div className="bg-gradient-to-r from-red-900 to-red-800 rounded-lg p-4 border-2 border-red-400">
          <h2 className="text-xl font-bold mb-3 flex items-center gap-2">
            <Swords className="w-5 h-5" />
            AI OPPONENT
          </h2>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Heart className="w-5 h-5 text-red-500" />
              <div className="flex-1">
                <div className="bg-gray-700 rounded-full h-3 overflow-hidden">
                  <div 
                    className="bg-red-500 h-full transition-all duration-300"
                    style={{ width: `${(opponent?.hp / 100) * 100}%` }}
                  />
                </div>
              </div>
              <span className="font-bold">{opponent?.hp}/100</span>
            </div>
            
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-purple-500" />
              <span>Level {opponent?.level}</span>
            </div>
            
            <div className="flex gap-2 text-sm">
              <span className="text-green-400">Win: {opponent?.win_streak || 0}</span>
              <span className="text-red-400">Loss: {opponent?.lose_streak || 0}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left Side - Your Deck & Shop */}
        <div className="space-y-4">
          {/* Your Deck */}
          <div className="bg-gray-800 bg-opacity-50 rounded-lg p-4">
            <h3 className="text-lg font-bold mb-3 flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-400" />
              Your Deck ({player?.deck?.length || 0}/{player?.max_deck_size || 0})
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {player?.deck?.map((unit, idx) => (
                <UnitComponent
                  key={idx}
                  unit={unit}
                  onClick={() => sellUnit(idx)}
                  canSell={phase === 'shop'}
                />
              ))}
              {(!player?.deck || player.deck.length === 0) && (
                <div className="col-span-3 text-center text-gray-500 py-8">
                  No units yet - buy some cards!
                </div>
              )}
            </div>
          </div>

          {/* Shop */}
          {phase === 'shop' && (
            <div className="bg-gray-800 bg-opacity-50 rounded-lg p-4">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-bold flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-yellow-400" />
                  Shop
                </h3>
                <button
                  onClick={() => generateShop(gameId, 0)}
                  disabled={player?.gold < 2}
                  className="px-3 py-1 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:opacity-50 rounded text-sm font-bold transition-all"
                >
                  Reroll (2g)
                </button>
              </div>
              <div className="grid grid-cols-5 gap-2">
                {shop.map((card, idx) => (
                  <CardComponent
                    key={idx}
                    card={card}
                    onClick={() => buyCard(idx)}
                    disabled={!player || player.gold < card.cost || player.deck.length >= player.max_deck_size}
                  />
                ))}
              </div>
            </div>
          )}

          {/* End Turn Button */}
          {phase === 'shop' && (
            <button
              onClick={endTurn}
              className="w-full py-4 bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 text-white font-bold text-xl rounded-lg shadow-xl transform hover:scale-105 transition-all duration-200"
            >
              END TURN & FIGHT
            </button>
          )}
        </div>

        {/* Right Side - Opponent Deck & Combat Log */}
        <div className="space-y-4">
          {/* Opponent Deck */}
          <div className="bg-gray-800 bg-opacity-50 rounded-lg p-4">
            <h3 className="text-lg font-bold mb-3 flex items-center gap-2">
              <Swords className="w-5 h-5 text-red-400" />
              Opponent Deck ({opponent?.deck?.length || 0}/{opponent?.max_deck_size || 0})
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {opponent?.deck?.map((unit, idx) => (
                <UnitComponent
                  key={idx}
                  unit={unit}
                  canSell={false}
                />
              ))}
              {(!opponent?.deck || opponent.deck.length === 0) && (
                <div className="col-span-3 text-center text-gray-500 py-8">
                  AI has no units
                </div>
              )}
            </div>
          </div>

          {/* Combat Log */}
          <div className="bg-gray-800 bg-opacity-50 rounded-lg p-4">
            <h3 className="text-lg font-bold mb-3 flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-400" />
              Combat Log
            </h3>
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {combatLog.length > 0 ? (
                combatLog.map((log, idx) => (
                  <div key={idx} className="text-sm text-gray-300 bg-gray-900 bg-opacity-50 px-3 py-2 rounded">
                    {log}
                  </div>
                ))
              ) : (
                <div className="text-center text-gray-500 py-8">
                  No combat yet
                </div>
              )}
            </div>
          </div>

          {/* Game Info */}
          <div className="bg-gray-800 bg-opacity-50 rounded-lg p-4">
            <h3 className="text-lg font-bold mb-3">Active Sects</h3>
            <div className="flex flex-wrap gap-2">
              {gameState?.active_sects?.map(sect => (
                <span key={sect} className="px-3 py-1 bg-purple-600 rounded-full text-sm">
                  {sect}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}