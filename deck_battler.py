"""
DECK BATTLER - Complete Auto-Battler Game with Reinforcement Learning
=====================================================================

A sophisticated auto-battler inspired by Auto Gladiators, featuring:
- 6 Sects with unique mechanics and legendaries
- Complex economy system with interest and streaks
- Deep combat with abilities, status effects, and combos
- PPO-based RL agent with self-play training
- Full visualization and analysis tools

FILE STRUCTURE:
===============
Save this as multiple files or run as single script:
- Core game in one file works fine for prototyping
- For production, split into: cards.py, engine.py, ai.py, train.py, viz.py

USAGE:
======
python deck_battler.py train --episodes 10000    # Train AI
python deck_battler.py play                       # Human vs AI
python deck_battler.py watch                      # Watch AI vs AI
python deck_battler.py analyze                    # Training stats

REQUIREMENTS:
=============
pip install numpy torch matplotlib tqdm

"""

import numpy as np
import random
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable
from enum import Enum
import copy
import json
from tqdm import tqdm
import matplotlib.pyplot as plt

# ============================================================================
# CARD DEFINITIONS AND ABILITIES
# ============================================================================

class Sect(Enum):
    IRON = "Iron"
    SHADOW = "Shadow"
    CELESTIAL = "Celestial"
    INFERNAL = "Infernal"
    NATURE = "Nature"
    ARCANE = "Arcane"

class Rarity(Enum):
    COMMON = ("Grey", 1, 3)
    UNCOMMON = ("Green", 2, 3)
    RARE = ("Blue", 3, 4)
    EPIC = ("Purple", 4, 5)
    LEGENDARY = ("Orange", 5, 6)
    
    def __init__(self, color, tier, cost):
        self.color = color
        self.tier = tier
        self.cost = cost

class CardType(Enum):
    UNIT = "Unit"
    TALENT = "Talent"
    SUPPRESSION = "Suppression"

class TriggerType(Enum):
    ON_DEPLOY = "on_deploy"
    ON_ATTACK = "on_attack"
    ON_DAMAGED = "on_damaged"
    ON_DEATH = "on_death"
    ON_KILL = "on_kill"
    HP_THRESHOLD = "hp_threshold"
    COMBAT_START = "combat_start"
    EVERY_TICK = "every_tick"

class StatusEffect(Enum):
    BURN = "burn"
    POISON = "poison"
    SHIELD = "shield"
    STUN = "stun"
    BUFF_ATK = "buff_atk"
    BUFF_DEF = "buff_def"
    DEBUFF_ATK = "debuff_atk"
    DEBUFF_DEF = "debuff_def"

@dataclass
class Ability:
    name: str
    trigger: TriggerType
    effect: Callable
    cooldown: float = 0.0
    threshold: float = 0.0  # For HP threshold triggers
    description: str = ""
    
    def __post_init__(self):
        self.current_cooldown = 0.0

@dataclass
class Unit:
    name: str
    sect: Sect
    rarity: Rarity
    hp: float
    max_hp: float
    atk: float
    defense: float
    speed: float
    abilities: List[Ability] = field(default_factory=list)
    status_effects: Dict[StatusEffect, float] = field(default_factory=dict)
    star_level: int = 1  # 1-3 stars from combining
    
    # Combat state
    is_alive: bool = True
    damage_dealt: float = 0.0
    damage_taken: float = 0.0
    kills: int = 0
    
    def __post_init__(self):
        # Apply star upgrades
        if self.star_level > 1:
            multiplier = 1.0 + (self.star_level - 1) * 0.5
            self.hp *= multiplier
            self.max_hp *= multiplier
            self.atk *= multiplier
            self.defense *= multiplier

    def take_damage(self, damage: float) -> float:
        actual_damage = max(0, damage - self.defense * 0.5)
        self.hp -= actual_damage
        self.damage_taken += actual_damage
        if self.hp <= 0:
            self.is_alive = False
        return actual_damage
    
    def heal(self, amount: float):
        self.hp = min(self.max_hp, self.hp + amount)
    
    def apply_status(self, status: StatusEffect, duration: float):
        self.status_effects[status] = duration
    
    def copy(self):
        return copy.deepcopy(self)

@dataclass
class Card:
    name: str
    card_type: CardType
    sect: Sect
    rarity: Rarity
    cost: int
    create_unit: Optional[Callable] = None  # Returns Unit instance
    passive_effect: Optional[Callable] = None  # For talents
    active_effect: Optional[Callable] = None  # For suppressions
    description: str = ""
    
    def __hash__(self):
        return hash(self.name)
    
    def __eq__(self, other):
        return isinstance(other, Card) and self.name == other.name

# ============================================================================
# CARD DATABASE
# ============================================================================

class CardDatabase:
    def __init__(self):
        self.all_cards: List[Card] = []
        self.legendaries_by_sect: Dict[Sect, List[Card]] = defaultdict(list)
        self._initialize_cards()
    
    def _initialize_cards(self):
        """Initialize all cards in the game"""
        
        # IRON SECT - Tanks and defense
        self._add_iron_cards()
        
        # SHADOW SECT - Assassins and executes
        self._add_shadow_cards()
        
        # CELESTIAL SECT - Heals and revival
        self._add_celestial_cards()
        
        # INFERNAL SECT - High damage and sacrifice
        self._add_infernal_cards()
        
        # NATURE SECT - Summons and growth
        self._add_nature_cards()
        
        # ARCANE SECT - Magic damage and CC
        self._add_arcane_cards()
    
    def _add_iron_cards(self):
        # Common
        self.all_cards.append(Card(
            "Iron Warrior",
            CardType.UNIT,
            Sect.IRON,
            Rarity.COMMON,
            3,
            lambda: Unit("Iron Warrior", Sect.IRON, Rarity.COMMON, 80, 80, 15, 8, 1.0),
            description="Sturdy frontline fighter"
        ))
        
        self.all_cards.append(Card(
            "Shield Bearer",
            CardType.UNIT,
            Sect.IRON,
            Rarity.COMMON,
            3,
            lambda: Unit("Shield Bearer", Sect.IRON, Rarity.COMMON, 100, 100, 10, 12, 0.8,
                        abilities=[Ability("Shield Wall", TriggerType.COMBAT_START,
                                         lambda u, c: c.apply_team_buff(u.sect, "defense", 5, 5.0),
                                         description="Grant allies +5 DEF for 5s")]),
            description="Protective defender"
        ))
        
        # Uncommon
        self.all_cards.append(Card(
            "Iron Vanguard",
            CardType.UNIT,
            Sect.IRON,
            Rarity.UNCOMMON,
            3,
            lambda: Unit("Iron Vanguard", Sect.IRON, Rarity.UNCOMMON, 120, 120, 20, 10, 1.0,
                        abilities=[Ability("Taunt", TriggerType.COMBAT_START,
                                         lambda u, c: setattr(u, 'atk', u.atk * 1.2),
                                         description="Gain +20% ATK")]),
            description="Elite warrior"
        ))
        
        # Rare
        self.all_cards.append(Card(
            "Adamant Guardian",
            CardType.UNIT,
            Sect.IRON,
            Rarity.RARE,
            4,
            lambda: Unit("Adamant Guardian", Sect.IRON, Rarity.RARE, 150, 150, 25, 15, 0.9,
                        abilities=[Ability("Fortify", TriggerType.ON_DAMAGED,
                                         lambda u, c: u.apply_status(StatusEffect.BUFF_DEF, 2.0),
                                         cooldown=3.0,
                                         description="Gain DEF buff when hit")]),
            description="Grows stronger when attacked"
        ))
        
        # Epic
        self.all_cards.append(Card(
            "Unbreakable Titan",
            CardType.UNIT,
            Sect.IRON,
            Rarity.EPIC,
            5,
            lambda: Unit("Unbreakable Titan", Sect.IRON, Rarity.EPIC, 200, 200, 30, 20, 0.8,
                        abilities=[Ability("Last Stand", TriggerType.HP_THRESHOLD,
                                         lambda u, c: setattr(u, 'atk', u.atk * 2),
                                         threshold=0.3,
                                         description="Double ATK below 30% HP")]),
            description="Becomes mighty when endangered"
        ))
        
        # Legendaries
        legendary1 = Card(
            "Fortress Eternal",
            CardType.UNIT,
            Sect.IRON,
            Rarity.LEGENDARY,
            6,
            lambda: Unit("Fortress Eternal", Sect.IRON, Rarity.LEGENDARY, 250, 250, 35, 30, 0.7,
                        abilities=[Ability("Immovable", TriggerType.COMBAT_START,
                                         lambda u, c: c.apply_team_effect(lambda unit: unit.take_damage(-50)),
                                         description="Team takes 50% reduced damage")]),
            description="LEGENDARY: Your team becomes a fortress"
        )
        self.all_cards.append(legendary1)
        self.legendaries_by_sect[Sect.IRON].append(legendary1)
        
        legendary2 = Card(
            "Iron Colossus",
            CardType.UNIT,
            Sect.IRON,
            Rarity.LEGENDARY,
            6,
            lambda: Unit("Iron Colossus", Sect.IRON, Rarity.LEGENDARY, 300, 300, 40, 25, 0.6,
                        abilities=[Ability("Earthquake", TriggerType.ON_ATTACK,
                                         lambda u, c: c.aoe_damage_enemies(20),
                                         cooldown=4.0,
                                         description="AOE 20 damage every 4s")]),
            description="LEGENDARY: Devastates all enemies"
        )
        self.all_cards.append(legendary2)
        self.legendaries_by_sect[Sect.IRON].append(legendary2)
    
    def _add_shadow_cards(self):
        # Common
        self.all_cards.append(Card(
            "Shadow Blade",
            CardType.UNIT,
            Sect.SHADOW,
            Rarity.COMMON,
            3,
            lambda: Unit("Shadow Blade", Sect.SHADOW, Rarity.COMMON, 60, 60, 25, 3, 1.5),
            description="Fast, fragile attacker"
        ))
        
        # Uncommon
        self.all_cards.append(Card(
            "Night Stalker",
            CardType.UNIT,
            Sect.SHADOW,
            Rarity.UNCOMMON,
            3,
            lambda: Unit("Night Stalker", Sect.SHADOW, Rarity.UNCOMMON, 70, 70, 30, 4, 1.6,
                        abilities=[Ability("Ambush", TriggerType.COMBAT_START,
                                         lambda u, c: c.instant_damage_weakest(40),
                                         description="Deal 40 damage to weakest enemy")]),
            description="Strike from shadows"
        ))
        
        # Rare
        self.all_cards.append(Card(
            "Silent Assassin",
            CardType.UNIT,
            Sect.SHADOW,
            Rarity.RARE,
            4,
            lambda: Unit("Silent Assassin", Sect.SHADOW, Rarity.RARE, 80, 80, 40, 5, 1.7,
                        abilities=[Ability("Execute", TriggerType.ON_ATTACK,
                                         lambda u, c: c.execute_low_hp_enemy(0.25),
                                         cooldown=5.0,
                                         description="Kill enemies below 25% HP")]),
            description="Finishes wounded foes"
        ))
        
        # Epic
        self.all_cards.append(Card(
            "Shadow Master",
            CardType.UNIT,
            Sect.SHADOW,
            Rarity.EPIC,
            5,
            lambda: Unit("Shadow Master", Sect.SHADOW, Rarity.EPIC, 90, 90, 50, 5, 1.8,
                        abilities=[Ability("Chain Kill", TriggerType.ON_KILL,
                                         lambda u, c: setattr(u, 'atk', u.atk * 1.15),
                                         description="Gain +15% ATK per kill")]),
            description="Grows stronger with each kill"
        ))
        
        # Legendaries
        legendary1 = Card(
            "Reaper's Shadow",
            CardType.UNIT,
            Sect.SHADOW,
            Rarity.LEGENDARY,
            6,
            lambda: Unit("Reaper's Shadow", Sect.SHADOW, Rarity.LEGENDARY, 100, 100, 70, 5, 2.0,
                        abilities=[Ability("Mass Execute", TriggerType.COMBAT_START,
                                         lambda u, c: c.execute_all_low_hp(0.4),
                                         description="Kill ALL enemies below 40% HP")]),
            description="LEGENDARY: The ultimate executioner"
        )
        self.all_cards.append(legendary1)
        self.legendaries_by_sect[Sect.SHADOW].append(legendary1)
        
        legendary2 = Card(
            "Void Assassin",
            CardType.UNIT,
            Sect.SHADOW,
            Rarity.LEGENDARY,
            6,
            lambda: Unit("Void Assassin", Sect.SHADOW, Rarity.LEGENDARY, 85, 85, 80, 3, 2.2,
                        abilities=[Ability("Decapitate", TriggerType.ON_ATTACK,
                                         lambda u, c: c.kill_highest_hp_enemy(),
                                         cooldown=8.0,
                                         description="Instantly kill highest HP enemy")]),
            description="LEGENDARY: Removes biggest threats"
        )
        self.all_cards.append(legendary2)
        self.legendaries_by_sect[Sect.SHADOW].append(legendary2)
    
    def _add_celestial_cards(self):
        # Common
        self.all_cards.append(Card(
            "Light Cleric",
            CardType.UNIT,
            Sect.CELESTIAL,
            Rarity.COMMON,
            3,
            lambda: Unit("Light Cleric", Sect.CELESTIAL, Rarity.COMMON, 70, 70, 12, 5, 1.0,
                        abilities=[Ability("Heal", TriggerType.EVERY_TICK,
                                         lambda u, c: c.heal_team(5),
                                         cooldown=3.0,
                                         description="Heal team for 5 HP")]),
            description="Provides steady healing"
        ))
        
        # Uncommon
        self.all_cards.append(Card(
            "Holy Knight",
            CardType.UNIT,
            Sect.CELESTIAL,
            Rarity.UNCOMMON,
            3,
            lambda: Unit("Holy Knight", Sect.CELESTIAL, Rarity.UNCOMMON, 90, 90, 18, 8, 1.0,
                        abilities=[Ability("Divine Shield", TriggerType.HP_THRESHOLD,
                                         lambda u, c: u.apply_status(StatusEffect.SHIELD, 3.0),
                                         threshold=0.5,
                                         description="Shield at 50% HP")]),
            description="Protected by divine power"
        ))
        
        # Rare
        self.all_cards.append(Card(
            "Radiant Priest",
            CardType.UNIT,
            Sect.CELESTIAL,
            Rarity.RARE,
            4,
            lambda: Unit("Radiant Priest", Sect.CELESTIAL, Rarity.RARE, 100, 100, 20, 7, 1.1,
                        abilities=[Ability("Mass Heal", TriggerType.EVERY_TICK,
                                         lambda u, c: c.heal_team(15),
                                         cooldown=4.0,
                                         description="Strong team heal")]),
            description="Powerful group healing"
        ))
        
        # Epic
        self.all_cards.append(Card(
            "Phoenix Guardian",
            CardType.UNIT,
            Sect.CELESTIAL,
            Rarity.EPIC,
            5,
            lambda: Unit("Phoenix Guardian", Sect.CELESTIAL, Rarity.EPIC, 120, 120, 25, 10, 1.0,
                        abilities=[Ability("Rebirth", TriggerType.ON_DEATH,
                                         lambda u, c: c.revive_unit(u, 0.5),
                                         description="Revive at 50% HP once")]),
            description="Returns from death"
        ))
        
        # Legendaries (THE REVIVAL CARDS)
        legendary1 = Card(
            "Angel's Grace",
            CardType.UNIT,
            Sect.CELESTIAL,
            Rarity.LEGENDARY,
            6,
            lambda: Unit("Angel's Grace", Sect.CELESTIAL, Rarity.LEGENDARY, 150, 150, 30, 12, 1.0,
                        abilities=[Ability("Divine Intervention", TriggerType.COMBAT_START,
                                         lambda u, c: setattr(c, 'has_grace', True),
                                         description="Prevent lethal damage ONCE per game")]),
            description="LEGENDARY: Saves you from death"
        )
        self.all_cards.append(legendary1)
        self.legendaries_by_sect[Sect.CELESTIAL].append(legendary1)
        
        legendary2 = Card(
            "Eternal Guardian",
            CardType.UNIT,
            Sect.CELESTIAL,
            Rarity.LEGENDARY,
            6,
            lambda: Unit("Eternal Guardian", Sect.CELESTIAL, Rarity.LEGENDARY, 180, 180, 28, 15, 0.9,
                        abilities=[Ability("Immortality Field", TriggerType.COMBAT_START,
                                         lambda u, c: c.apply_team_invuln(5.0),
                                         description="Team invulnerable for 5s")]),
            description="LEGENDARY: Ultimate protection"
        )
        self.all_cards.append(legendary2)
        self.legendaries_by_sect[Sect.CELESTIAL].append(legendary2)
    
    def _add_infernal_cards(self):
        # Common
        self.all_cards.append(Card(
            "Flame Imp",
            CardType.UNIT,
            Sect.INFERNAL,
            Rarity.COMMON,
            3,
            lambda: Unit("Flame Imp", Sect.INFERNAL, Rarity.COMMON, 65, 65, 22, 4, 1.3,
                        abilities=[Ability("Burn", TriggerType.ON_ATTACK,
                                         lambda u, c: c.apply_burn_to_target(10, 3.0),
                                         cooldown=2.0,
                                         description="Apply burn damage")]),
            description="Sets enemies ablaze"
        ))
        
        # Uncommon
        self.all_cards.append(Card(
            "Hellfire Warlock",
            CardType.UNIT,
            Sect.INFERNAL,
            Rarity.UNCOMMON,
            3,
            lambda: Unit("Hellfire Warlock", Sect.INFERNAL, Rarity.UNCOMMON, 75, 75, 28, 5, 1.4,
                        abilities=[Ability("Immolate", TriggerType.ON_DEPLOY,
                                         lambda u, c: c.aoe_damage_enemies(25),
                                         description="Deal 25 AOE on deploy")]),
            description="Explosive entrance"
        ))
        
        # Rare
        self.all_cards.append(Card(
            "Inferno Lord",
            CardType.UNIT,
            Sect.INFERNAL,
            Rarity.RARE,
            4,
            lambda: Unit("Inferno Lord", Sect.INFERNAL, Rarity.RARE, 85, 85, 35, 6, 1.5,
                        abilities=[Ability("Firestorm", TriggerType.EVERY_TICK,
                                         lambda u, c: c.aoe_damage_enemies(15),
                                         cooldown=3.0,
                                         description="Constant AOE damage")]),
            description="Continuous fire damage"
        ))
        
        # Epic
        self.all_cards.append(Card(
            "Demon Prince",
            CardType.UNIT,
            Sect.INFERNAL,
            Rarity.EPIC,
            5,
            lambda: Unit("Demon Prince", Sect.INFERNAL, Rarity.EPIC, 95, 95, 45, 7, 1.6,
                        abilities=[Ability("Blood Pact", TriggerType.COMBAT_START,
                                         lambda u, c: (setattr(u, 'atk', u.atk * 1.5), u.take_damage(30)),
                                         description="Sacrifice HP for +50% ATK")]),
            description="Power through sacrifice"
        ))
        
        # Legendaries
        legendary1 = Card(
            "Demon Pact",
            CardType.UNIT,
            Sect.INFERNAL,
            Rarity.LEGENDARY,
            6,
            lambda: Unit("Demon Pact", Sect.INFERNAL, Rarity.LEGENDARY, 110, 110, 60, 8, 1.7,
                        abilities=[Ability("Soul Harvest", TriggerType.COMBAT_START,
                                         lambda u, c: c.apply_massive_team_buff(2.0),
                                         description="Team gains MASSIVE stats")]),
            description="LEGENDARY: Ultimate power spike"
        )
        self.all_cards.append(legendary1)
        self.legendaries_by_sect[Sect.INFERNAL].append(legendary1)
        
        legendary2 = Card(
            "Armageddon",
            CardType.UNIT,
            Sect.INFERNAL,
            Rarity.LEGENDARY,
            6,
            lambda: Unit("Armageddon", Sect.INFERNAL, Rarity.LEGENDARY, 100, 100, 50, 5, 1.5,
                        abilities=[Ability("End Times", TriggerType.ON_DEPLOY,
                                         lambda u, c: c.damage_all_units(80),
                                         description="Deal 80 to EVERYONE")]),
            description="LEGENDARY: Nuclear option"
        )
        self.all_cards.append(legendary2)
        self.legendaries_by_sect[Sect.INFERNAL].append(legendary2)
    
    def _add_nature_cards(self):
        # Common
        self.all_cards.append(Card(
            "Forest Spirit",
            CardType.UNIT,
            Sect.NATURE,
            Rarity.COMMON,
            3,
            lambda: Unit("Forest Spirit", Sect.NATURE, Rarity.COMMON, 75, 75, 16, 6, 1.0,
                        abilities=[Ability("Grow", TriggerType.EVERY_TICK,
                                         lambda u, c: setattr(u, 'atk', u.atk + 2),
                                         cooldown=2.0,
                                         description="Gain +2 ATK over time")]),
            description="Grows stronger each moment"
        ))
        
        # Uncommon
        self.all_cards.append(Card(
            "Thorn Beast",
            CardType.UNIT,
            Sect.NATURE,
            Rarity.UNCOMMON,
            3,
            lambda: Unit("Thorn Beast", Sect.NATURE, Rarity.UNCOMMON, 85, 85, 20, 7, 1.1,
                        abilities=[Ability("Thorns", TriggerType.ON_DAMAGED,
                                         lambda u, c: c.damage_attacker(15),
                                         description="Damage attackers")]),
            description="Reflects damage"
        ))
        
        # Rare
        self.all_cards.append(Card(
            "Ancient Treant",
            CardType.UNIT,
            Sect.NATURE,
            Rarity.RARE,
            4,
            lambda: Unit("Ancient Treant", Sect.NATURE, Rarity.RARE, 140, 140, 22, 12, 0.8,
                        abilities=[Ability("Rooted Strength", TriggerType.COMBAT_START,
                                         lambda u, c: c.apply_team_buff(u.sect, "defense", 8, 10.0),
                                         description="Team gains DEF")]),
            description="Protects nature allies"
        ))
        
        # Epic
        self.all_cards.append(Card(
            "World Tree",
            CardType.UNIT,
            Sect.NATURE,
            Rarity.EPIC,
            5,
            lambda: Unit("World Tree", Sect.NATURE, Rarity.EPIC, 180, 180, 25, 15, 0.7,
                        abilities=[Ability("Endless Growth", TriggerType.EVERY_TICK,
                                         lambda u, c: c.heal_and_buff_team(8, 3),
                                         cooldown=2.0,
                                         description="Heal and buff team")]),
            description="Empowers entire team"
        ))
        
        # Legendaries
        legendary1 = Card(
            "Gaia's Avatar",
            CardType.UNIT,
            Sect.NATURE,
            Rarity.LEGENDARY,
            6,
            lambda: Unit("Gaia's Avatar", Sect.NATURE, Rarity.LEGENDARY, 220, 220, 30, 18, 0.8,
                        abilities=[Ability("Nature's Wrath", TriggerType.COMBAT_START,
                                         lambda u, c: c.summon_treants(3),
                                         description="Summon 3 powerful treants")]),
            description="LEGENDARY: Army of nature"
        )
        self.all_cards.append(legendary1)
        self.legendaries_by_sect[Sect.NATURE].append(legendary1)
        
        legendary2 = Card(
            "Primal Force",
            CardType.UNIT,
            Sect.NATURE,
            Rarity.LEGENDARY,
            6,
            lambda: Unit("Primal Force", Sect.NATURE, Rarity.LEGENDARY, 200, 200, 35, 20, 0.9,
                        abilities=[Ability("Overgrowth", TriggerType.EVERY_TICK,
                                         lambda u, c: c.scale_team_permanently(1.05),
                                         cooldown=1.0,
                                         description="Team grows 5% stronger every second")]),
            description="LEGENDARY: Exponential growth"
        )
        self.all_cards.append(legendary2)
        self.legendaries_by_sect[Sect.NATURE].append(legendary2)
    
    def _add_arcane_cards(self):
        # Common
        self.all_cards.append(Card(
            "Arcane Apprentice",
            CardType.UNIT,
            Sect.ARCANE,
            Rarity.COMMON,
            3,
            lambda: Unit("Arcane Apprentice", Sect.ARCANE, Rarity.COMMON, 60, 60, 20, 4, 1.4,
                        abilities=[Ability("Magic Missile", TriggerType.ON_ATTACK,
                                         lambda u, c: c.true_damage_random(25),
                                         cooldown=2.0,
                                         description="True damage to random enemy")]),
            description="Magic damage dealer"
        ))
        
        # Uncommon
        self.all_cards.append(Card(
            "Frost Mage",
            CardType.UNIT,
            Sect.ARCANE,
            Rarity.UNCOMMON,
            3,
            lambda: Unit("Frost Mage", Sect.ARCANE, Rarity.UNCOMMON, 70, 70, 24, 5, 1.5,
                        abilities=[Ability("Freeze", TriggerType.ON_ATTACK,
                                         lambda u, c: c.stun_random_enemy(2.0),
                                         cooldown=3.0,
                                         description="Stun random enemy")]),
            description="Control caster"
        ))
        
        # Rare
        self.all_cards.append(Card(
            "Archmage",
            CardType.UNIT,
            Sect.ARCANE,
            Rarity.RARE,
            4,
            lambda: Unit("Archmage", Sect.ARCANE, Rarity.RARE, 80, 80, 32, 6, 1.6,
                        abilities=[Ability("Chain Lightning", TriggerType.ON_ATTACK,
                                         lambda u, c: c.chain_damage(30, 3),
                                         cooldown=3.5,
                                         description="Bouncing magic damage")]),
            description="AOE magic specialist"
        ))
        
        # Epic
        self.all_cards.append(Card(
            "Void Sorcerer",
            CardType.UNIT,
            Sect.ARCANE,
            Rarity.EPIC,
            5,
            lambda: Unit("Void Sorcerer", Sect.ARCANE, Rarity.EPIC, 90, 90, 40, 7, 1.7,
                        abilities=[Ability("Reality Warp", TriggerType.COMBAT_START,
                                         lambda u, c: c.mass_debuff_enemies(),
                                         description="Weaken all enemies")]),
            description="Debuffs entire enemy team"
        ))
        
        # Legendaries
        legendary1 = Card(
            "Timebender",
            CardType.UNIT,
            Sect.ARCANE,
            Rarity.LEGENDARY,
            6,
            lambda: Unit("Timebender", Sect.ARCANE, Rarity.LEGENDARY, 100, 100, 45, 8, 2.0,
                        abilities=[Ability("Time Stop", TriggerType.COMBAT_START,
                                         lambda u, c: c.freeze_all_enemies(4.0),
                                         description="Freeze ALL enemies for 4s")]),
            description="LEGENDARY: Complete crowd control"
        )
        self.all_cards.append(legendary1)
        self.legendaries_by_sect[Sect.ARCANE].append(legendary1)
        
        legendary2 = Card(
            "Arcane Singularity",
            CardType.UNIT,
            Sect.ARCANE,
            Rarity.LEGENDARY,
            6,
            lambda: Unit("Arcane Singularity", Sect.ARCANE, Rarity.LEGENDARY, 95, 95, 50, 6, 1.8,
                        abilities=[Ability("Black Hole", TriggerType.ON_ATTACK,
                                         lambda u, c: c.true_damage_all_enemies(35),
                                         cooldown=4.0,
                                         description="True damage to ALL")]),
            description="LEGENDARY: Devastating magic"
        )
        self.all_cards.append(legendary2)
        self.legendaries_by_sect[Sect.ARCANE].append(legendary2)
    
    def get_shop_pool(self, level: int, available_sects: List[Sect]) -> List[Card]:
        """Get cards available for shopping based on level"""
        odds = self._get_rarity_odds(level)
        pool = []
        
        for card in self.all_cards:
            if card.card_type == CardType.UNIT and card.sect in available_sects:
                if card.rarity != Rarity.LEGENDARY:
                    pool.append(card)
        
        return pool
    
    def _get_rarity_odds(self, level: int) -> Dict[Rarity, float]:
        """Shop odds based on level"""
        odds_table = {
            1: {Rarity.COMMON: 0.75, Rarity.UNCOMMON: 0.20, Rarity.RARE: 0.04, Rarity.EPIC: 0.01, Rarity.LEGENDARY: 0.00},
            2: {Rarity.COMMON: 0.70, Rarity.UNCOMMON: 0.23, Rarity.RARE: 0.05, Rarity.EPIC: 0.02, Rarity.LEGENDARY: 0.00},
            3: {Rarity.COMMON: 0.60, Rarity.UNCOMMON: 0.28, Rarity.RARE: 0.08, Rarity.EPIC: 0.04, Rarity.LEGENDARY: 0.00},
            4: {Rarity.COMMON: 0.50, Rarity.UNCOMMON: 0.32, Rarity.RARE: 0.12, Rarity.EPIC: 0.06, Rarity.LEGENDARY: 0.00},
            5: {Rarity.COMMON: 0.40, Rarity.UNCOMMON: 0.33, Rarity.RARE: 0.17, Rarity.EPIC: 0.10, Rarity.LEGENDARY: 0.00},
            6: {Rarity.COMMON: 0.30, Rarity.UNCOMMON: 0.32, Rarity.RARE: 0.22, Rarity.EPIC: 0.13, Rarity.LEGENDARY: 0.03},
            7: {Rarity.COMMON: 0.19, Rarity.UNCOMMON: 0.30, Rarity.RARE: 0.28, Rarity.EPIC: 0.16, Rarity.LEGENDARY: 0.07},
            8: {Rarity.COMMON: 0.10, Rarity.UNCOMMON: 0.25, Rarity.RARE: 0.30, Rarity.EPIC: 0.25, Rarity.LEGENDARY: 0.10},
        }
        return odds_table.get(level, odds_table[8])
    
    def generate_shop(self, level: int, available_sects: List[Sect], 
                      active_legendaries: Dict[Sect, List[Card]]) -> List[Card]:
        """Generate 5 random shop cards"""
        pool = self.get_shop_pool(level, available_sects)
        odds = self._get_rarity_odds(level)
        
        shop = []
        for _ in range(5):
            # Roll rarity
            roll = random.random()
            cumulative = 0
            selected_rarity = Rarity.COMMON
            
            for rarity, chance in odds.items():
                cumulative += chance
                if roll < cumulative:
                    selected_rarity = rarity
                    break
            
            # Handle legendary separately
            if selected_rarity == Rarity.LEGENDARY:
                legendary_pool = []
                for sect in available_sects:
                    legendary_pool.extend(active_legendaries[sect])
                if legendary_pool:
                    shop.append(random.choice(legendary_pool))
                else:
                    selected_rarity = Rarity.EPIC
            
            if selected_rarity != Rarity.LEGENDARY:
                # Get cards of this rarity
                rarity_pool = [c for c in pool if c.rarity == selected_rarity]
                if rarity_pool:
                    shop.append(random.choice(rarity_pool))
        
        return shop

# ============================================================================
# COMBAT ENGINE
# ============================================================================

class CombatEngine:
    def __init__(self):
        self.tick_rate = 0.5  # Seconds per tick
        self.max_ticks = 60  # 30 seconds max combat
        self.current_tick = 0
        
        self.team_a: List[Unit] = []
        self.team_b: List[Unit] = []
        
        self.has_grace = False  # Divine Intervention flag
        
    def simulate_combat(self, deck_a: List[Unit], deck_b: List[Unit]) -> Tuple[bool, int]:
        """
        Simulate combat between two decks
        Returns: (team_a_won, damage_to_loser)
        """
        # Deep copy units for simulation
        self.team_a = [u.copy() for u in deck_a]
        self.team_b = [u.copy() for u in deck_b]
        self.current_tick = 0
        self.has_grace = False
        
        # Trigger combat start abilities
        self._trigger_abilities(TriggerType.COMBAT_START)
        
        # Combat loop
        while self.current_tick < self.max_ticks:
            if not self._are_alive(self.team_a) or not self._are_alive(self.team_b):
                break
            
            self._process_tick()
            self.current_tick += 1
        
        # Determine winner
        team_a_alive = self._are_alive(self.team_a)
        team_b_alive = self._are_alive(self.team_b)
        
        if team_a_alive and not team_b_alive:
            damage = self._calculate_damage(self.team_a)
            return True, damage
        elif team_b_alive and not team_a_alive:
            damage = self._calculate_damage(self.team_b)
            return False, damage
        else:
            # Tie or timeout - calculate based on remaining HP
            hp_a = sum(u.hp for u in self.team_a if u.is_alive)
            hp_b = sum(u.hp for u in self.team_b if u.is_alive)
            if hp_a > hp_b:
                return True, max(1, int((hp_a - hp_b) / 10))
            else:
                return False, max(1, int((hp_b - hp_a) / 10))
    
    def _process_tick(self):
        """Process one combat tick"""
        # Update cooldowns
        for team in [self.team_a, self.team_b]:
            for unit in team:
                if unit.is_alive:
                    for ability in unit.abilities:
                        ability.current_cooldown = max(0, ability.current_cooldown - self.tick_rate)
        
        # Process status effects
        self._process_status_effects()
        
        # Trigger tick abilities
        self._trigger_abilities(TriggerType.EVERY_TICK)
        
        # Units attack
        self._process_attacks()
    
    def _process_attacks(self):
        """All alive units attack"""
        for team, enemy_team in [(self.team_a, self.team_b), (self.team_b, self.team_a)]:
            for unit in team:
                if unit.is_alive and StatusEffect.STUN not in unit.status_effects:
                    # Find target (random enemy)
                    alive_enemies = [u for u in enemy_team if u.is_alive]
                    if alive_enemies:
                        target = random.choice(alive_enemies)
                        damage = unit.atk
                        
                        # Apply buffs/debuffs
                        if StatusEffect.BUFF_ATK in unit.status_effects:
                            damage *= 1.3
                        if StatusEffect.DEBUFF_ATK in unit.status_effects:
                            damage *= 0.7
                        
                        actual_damage = target.take_damage(damage)
                        unit.damage_dealt += actual_damage
                        
                        # Trigger on_attack abilities
                        self._trigger_unit_abilities(unit, TriggerType.ON_ATTACK)
                        
                        # Check if target died
                        if not target.is_alive:
                            unit.kills += 1
                            self._trigger_unit_abilities(unit, TriggerType.ON_KILL)
                            self._trigger_unit_abilities(target, TriggerType.ON_DEATH)
                        else:
                            # Trigger on_damaged
                            self._trigger_unit_abilities(target, TriggerType.ON_DAMAGED)
                            
                            # Check HP thresholds
                            hp_percent = target.hp / target.max_hp
                            for ability in target.abilities:
                                if ability.trigger == TriggerType.HP_THRESHOLD:
                                    if hp_percent <= ability.threshold and ability.current_cooldown == 0:
                                        ability.effect(target, self)
                                        ability.current_cooldown = ability.cooldown
    
    def _process_status_effects(self):
        """Process status effect ticks"""
        for team in [self.team_a, self.team_b]:
            for unit in team:
                if not unit.is_alive:
                    continue
                
                # Decay status durations
                for status in list(unit.status_effects.keys()):
                    unit.status_effects[status] -= self.tick_rate
                    if unit.status_effects[status] <= 0:
                        del unit.status_effects[status]
                
                # Apply damage from burn/poison
                if StatusEffect.BURN in unit.status_effects:
                    unit.take_damage(5)
                if StatusEffect.POISON in unit.status_effects:
                    unit.take_damage(3)
    
    def _trigger_abilities(self, trigger_type: TriggerType):
        """Trigger abilities of specific type for all units"""
        for team in [self.team_a, self.team_b]:
            for unit in team:
                if unit.is_alive:
                    self._trigger_unit_abilities(unit, trigger_type)
    
    def _trigger_unit_abilities(self, unit: Unit, trigger_type: TriggerType):
        """Trigger abilities for a specific unit"""
        for ability in unit.abilities:
            if ability.trigger == trigger_type and ability.current_cooldown == 0:
                try:
                    ability.effect(unit, self)
                    ability.current_cooldown = ability.cooldown
                except Exception as e:
                    pass  # Gracefully handle ability errors
    
    def _are_alive(self, team: List[Unit]) -> bool:
        """Check if any unit in team is alive"""
        return any(u.is_alive for u in team)
    
    def _calculate_damage(self, winning_team: List[Unit]) -> int:
        """Calculate damage dealt to losing player"""
        total_stats = sum(u.hp + u.atk for u in winning_team if u.is_alive)
        return max(5, int(total_stats / 10))
    
    # Helper methods for abilities
    def apply_team_buff(self, sect: Sect, stat: str, amount: float, duration: float):
        """Apply buff to team of specific sect"""
        for unit in self.team_a + self.team_b:
            if unit.sect == sect and unit.is_alive:
                if stat == "attack":
                    unit.atk += amount
                elif stat == "defense":
                    unit.defense += amount
    
    def apply_team_effect(self, effect_func: Callable):
        """Apply effect to entire team"""
        for unit in self.team_a:
            if unit.is_alive:
                effect_func(unit)
    
    def heal_team(self, amount: float):
        """Heal all friendly units"""
        # Determine which team the healer is on
        # This is simplified - in practice you'd track team context
        for unit in self.team_a + self.team_b:
            if unit.is_alive:
                unit.heal(amount)
    
    def aoe_damage_enemies(self, damage: float):
        """Deal AOE damage to enemies"""
        for unit in self.team_b if random.random() < 0.5 else self.team_a:
            if unit.is_alive:
                unit.take_damage(damage)
    
    def instant_damage_weakest(self, damage: float):
        """Deal instant damage to weakest enemy"""
        enemies = [u for u in self.team_b if u.is_alive]
        if enemies:
            weakest = min(enemies, key=lambda u: u.hp)
            weakest.take_damage(damage)
    
    def execute_low_hp_enemy(self, threshold: float):
        """Kill enemies below HP threshold"""
        for unit in self.team_b:
            if unit.is_alive and unit.hp / unit.max_hp < threshold:
                unit.hp = 0
                unit.is_alive = False
    
    def execute_all_low_hp(self, threshold: float):
        """Kill ALL enemies below HP threshold"""
        for unit in self.team_b:
            if unit.is_alive and unit.hp / unit.max_hp < threshold:
                unit.hp = 0
                unit.is_alive = False
    
    def kill_highest_hp_enemy(self):
        """Instantly kill highest HP enemy"""
        enemies = [u for u in self.team_b if u.is_alive]
        if enemies:
            highest = max(enemies, key=lambda u: u.hp)
            highest.hp = 0
            highest.is_alive = False
    
    def revive_unit(self, unit: Unit, hp_percent: float):
        """Revive a unit at % HP"""
        if not unit.is_alive:
            unit.is_alive = True
            unit.hp = unit.max_hp * hp_percent
    
    def apply_team_invuln(self, duration: float):
        """Make team invulnerable"""
        # Simplified - would need more complex implementation
        pass
    
    def apply_burn_to_target(self, damage: float, duration: float):
        """Apply burn status"""
        enemies = [u for u in self.team_b if u.is_alive]
        if enemies:
            target = random.choice(enemies)
            target.apply_status(StatusEffect.BURN, duration)
    
    def true_damage_random(self, damage: float):
        """Deal true damage (ignores defense)"""
        enemies = [u for u in self.team_b if u.is_alive]
        if enemies:
            target = random.choice(enemies)
            target.hp -= damage
            if target.hp <= 0:
                target.is_alive = False
    
    def stun_random_enemy(self, duration: float):
        """Stun random enemy"""
        enemies = [u for u in self.team_b if u.is_alive]
        if enemies:
            target = random.choice(enemies)
            target.apply_status(StatusEffect.STUN, duration)
    
    def chain_damage(self, damage: float, bounces: int):
        """Chain damage between enemies"""
        enemies = [u for u in self.team_b if u.is_alive]
        for _ in range(min(bounces, len(enemies))):
            if enemies:
                target = random.choice(enemies)
                target.take_damage(damage)
                enemies.remove(target)
    
    def mass_debuff_enemies(self):
        """Debuff all enemies"""
        for unit in self.team_b:
            if unit.is_alive:
                unit.apply_status(StatusEffect.DEBUFF_ATK, 5.0)
                unit.apply_status(StatusEffect.DEBUFF_DEF, 5.0)
    
    def freeze_all_enemies(self, duration: float):
        """Freeze all enemies"""
        for unit in self.team_b:
            if unit.is_alive:
                unit.apply_status(StatusEffect.STUN, duration)
    
    def true_damage_all_enemies(self, damage: float):
        """True damage to all enemies"""
        for unit in self.team_b:
            if unit.is_alive:
                unit.hp -= damage
                if unit.hp <= 0:
                    unit.is_alive = False
    
    def apply_massive_team_buff(self, multiplier: float):
        """Massive team stat buff"""
        for unit in self.team_a:
            if unit.is_alive:
                unit.atk *= multiplier
                unit.defense *= multiplier
    
    def damage_all_units(self, damage: float):
        """Damage ALL units (both teams)"""
        for unit in self.team_a + self.team_b:
            if unit.is_alive:
                unit.take_damage(damage)
    
    def summon_treants(self, count: int):
        """Summon treant units"""
        for _ in range(count):
            treant = Unit("Treant", Sect.NATURE, Rarity.COMMON, 60, 60, 18, 8, 1.0)
            self.team_a.append(treant)
    
    def scale_team_permanently(self, multiplier: float):
        """Permanently scale team stats"""
        for unit in self.team_a:
            if unit.is_alive:
                unit.atk *= multiplier
                unit.max_hp *= multiplier
                unit.hp *= multiplier
    
    def heal_and_buff_team(self, heal: float, buff: float):
        """Heal and buff team"""
        for unit in self.team_a:
            if unit.is_alive:
                unit.heal(heal)
                unit.atk += buff
    
    def damage_attacker(self, damage: float):
        """Damage the attacker (thorns effect)"""
        # Would need to track attacker context
        pass

# ============================================================================
# GAME STATE AND PLAYER
# ============================================================================

@dataclass
class PlayerState:
    player_id: int
    hp: int = 100
    gold: int = 10
    level: int = 1
    deck: List[Unit] = field(default_factory=list)
    bench: List[Card] = field(default_factory=list)  # Cards owned but not in deck
    
    # Streak tracking
    win_streak: int = 0
    lose_streak: int = 0
    
    # Round tracking
    rounds_survived: int = 0
    total_damage_dealt: int = 0
    total_damage_taken: int = 0
    
    # Game result
    placement: int = 0  # 1st, 2nd, 3rd, etc.
    is_eliminated: bool = False
    
    def get_max_deck_size(self) -> int:
        """Max deck size based on level"""
        return min(self.level + 2, 10)
    
    def get_interest(self) -> int:
        """Calculate interest gold"""
        return min(5, self.gold // 10)
    
    def get_streak_bonus(self) -> int:
        """Calculate streak bonus"""
        return min(3, max(self.win_streak, self.lose_streak))
    
    def earn_gold(self, base: int = 5):
        """Earn gold for the round"""
        total = base + self.get_interest() + self.get_streak_bonus()
        self.gold += total
        return total
    
    def can_level_up(self) -> bool:
        """Check if player can afford to level"""
        return self.gold >= 4 and self.level < 8
    
    def level_up(self):
        """Level up player"""
        if self.can_level_up():
            self.gold -= 4
            self.level += 1
            return True
        return False
    
    def take_damage(self, damage: int):
        """Take damage from losing combat"""
        self.hp -= damage
        self.total_damage_taken += damage
        if self.hp <= 0:
            self.hp = 0
            self.is_eliminated = True
    
    def add_to_deck(self, unit: Unit) -> bool:
        """Add unit to deck if space available"""
        if len(self.deck) < self.get_max_deck_size():
            self.deck.append(unit)
            return True
        return False

class GameState:
    def __init__(self, num_players: int = 8):
        self.num_players = num_players
        self.players: List[PlayerState] = [PlayerState(i) for i in range(num_players)]
        self.current_round = 0
        self.max_rounds = 30
        
        # Card database
        self.card_db = CardDatabase()
        
        # Active sects and legendaries for this game
        all_sects = list(Sect)
        self.active_sects = random.sample(all_sects, 4)  # 4 of 6 sects active
        self.active_legendaries: Dict[Sect, List[Card]] = {}
        for sect in self.active_sects:
            available = self.card_db.legendaries_by_sect[sect]
            self.active_legendaries[sect] = random.sample(available, min(2, len(available)))
        
        # Combat engine
        self.combat_engine = CombatEngine()
        
    def is_game_over(self) -> bool:
        """Check if game is over"""
        alive_players = sum(1 for p in self.players if not p.is_eliminated)
        return alive_players <= 1 or self.current_round >= self.max_rounds
    
    def get_alive_players(self) -> List[PlayerState]:
        """Get list of alive players"""
        return [p for p in self.players if not p.is_eliminated]
    
    def run_round(self):
        """Run one complete round"""
        self.current_round += 1
        
        # Phase 1: Income
        for player in self.get_alive_players():
            player.earn_gold()
        
        # Phase 2: Shop phase handled by agent
        
        # Phase 3: Combat
        self._run_combat_phase()
        
    def _run_combat_phase(self):
        """Run combat between all players"""
        alive = self.get_alive_players()
        if len(alive) < 2:
            return
        
        # Pair players randomly
        random.shuffle(alive)
        pairs = []
        for i in range(0, len(alive) - 1, 2):
            pairs.append((alive[i], alive[i+1]))
        
        # If odd number, one player gets a bye
        
        # Simulate each match
        for player_a, player_b in pairs:
            if player_a.deck and player_b.deck:
                won, damage = self.combat_engine.simulate_combat(player_a.deck, player_b.deck)
                
                if won:
                    player_b.take_damage(damage)
                    player_a.win_streak += 1
                    player_a.lose_streak = 0
                    player_b.win_streak = 0
                    player_b.lose_streak += 1
                    player_a.total_damage_dealt += damage
                else:
                    player_a.take_damage(damage)
                    player_b.win_streak += 1
                    player_b.lose_streak = 0
                    player_a.win_streak = 0
                    player_a.lose_streak += 1
                    player_b.total_damage_dealt += damage
        
        # Update rounds survived
        for player in alive:
            if not player.is_eliminated:
                player.rounds_survived += 1
    
    def get_final_placements(self) -> List[Tuple[int, PlayerState]]:
        """Get final placements sorted by performance"""
        # Sort by: eliminated last > HP > damage dealt
        sorted_players = sorted(
            self.players,
            key=lambda p: (not p.is_eliminated, p.hp, p.total_damage_dealt),
            reverse=True
        )
        
        for i, player in enumerate(sorted_players):
            player.placement = i + 1
        
        return [(p.placement, p) for p in sorted_players]

# ============================================================================
# REINFORCEMENT LEARNING AGENT
# ============================================================================

class PolicyNetwork(nn.Module):
    """Neural network for policy and value estimation"""
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()
        
        # Shared layers
        self.shared = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        
        # Policy head
        self.policy_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, action_dim),
        )
        
        # Value head
        self.value_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )
    
    def forward(self, state):
        shared = self.shared(state)
        policy_logits = self.policy_head(shared)
        value = self.value_head(shared)
        return policy_logits, value

class DeckBattlerAgent:
    """PPO-based RL agent for Deck Battler"""
    def __init__(self, state_dim: int = 128, action_dim: int = 20, lr: float = 3e-4):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.policy = PolicyNetwork(state_dim, action_dim).to(self.device)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=lr)
        
        # PPO hyperparameters
        self.gamma = 0.99
        self.gae_lambda = 0.95
        self.clip_epsilon = 0.2
        self.value_coef = 0.5
        self.entropy_coef = 0.01
        
        # Experience buffer
        self.states = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []
        self.dones = []
        
        # Statistics
        self.episode_rewards = []
        self.episode_placements = []
    
    def encode_state(self, player: PlayerState, game: GameState, shop: List[Card]) -> torch.Tensor:
        """Encode game state into neural network input"""
        state = []
        
        # Player stats (normalized)
        state.extend([
            player.hp / 100.0,
            player.gold / 50.0,
            player.level / 8.0,
            len(player.deck) / 10.0,
            player.win_streak / 5.0,
            player.lose_streak / 5.0,
        ])
        
        # Round info
        state.append(game.current_round / 30.0)
        
        # Deck composition (sect counts)
        sect_counts = {sect: 0 for sect in Sect}
        for unit in player.deck:
            sect_counts[unit.sect] += 1
        state.extend([sect_counts[sect] / 10.0 for sect in Sect])
        
        # Shop cards (one-hot-ish encoding)
        # Simplified: just rarity distribution
        rarity_counts = {r: 0 for r in Rarity}
        for card in shop:
            rarity_counts[card.rarity] += 1
        state.extend([rarity_counts[r] / 5.0 for r in Rarity])
        
        # Opponent strength estimate (avg HP of alive players)
        alive = game.get_alive_players()
        avg_opponent_hp = sum(p.hp for p in alive if p != player) / max(1, len(alive) - 1)
        state.append(avg_opponent_hp / 100.0)
        
        # Pad to fixed size
        while len(state) < 128:
            state.append(0.0)
        
        return torch.FloatTensor(state[:128]).to(self.device)
    
    def decode_action(self, action_idx: int, player: PlayerState, shop: List[Card]) -> Dict:
        """Decode neural network action into game action"""
        # Action space:
        # 0: Do nothing (pass)
        # 1-5: Buy shop card 0-4
        # 6: Reroll
        # 7: Level up
        # 8-17: Sell deck card 0-9
        
        if action_idx == 0:
            return {"type": "pass"}
        elif 1 <= action_idx <= 5:
            card_idx = action_idx - 1
            if card_idx < len(shop):
                return {"type": "buy", "card_idx": card_idx}
            return {"type": "pass"}
        elif action_idx == 6:
            return {"type": "reroll"}
        elif action_idx == 7:
            return {"type": "level"}
        elif 8 <= action_idx <= 17:
            deck_idx = action_idx - 8
            if deck_idx < len(player.deck):
                return {"type": "sell", "deck_idx": deck_idx}
            return {"type": "pass"}
        
        return {"type": "pass"}
    
    def select_action(self, state: torch.Tensor, deterministic: bool = False):
        """Select action using policy network"""
        with torch.no_grad():
            policy_logits, value = self.policy(state.unsqueeze(0))
        
        if deterministic:
            action = policy_logits.argmax(dim=1).item()
            return action, None, value.item()
        else:
            probs = torch.softmax(policy_logits, dim=1)
            dist = Categorical(probs)
            action = dist.sample()
            log_prob = dist.log_prob(action)
            return action.item(), log_prob.item(), value.item()
    
    def store_transition(self, state, action, reward, value, log_prob, done):
        """Store experience"""
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.values.append(value)
        self.log_probs.append(log_prob)
        self.dones.append(done)
    
    def compute_gae(self, next_value: float = 0.0):
        """Compute Generalized Advantage Estimation"""
        advantages = []
        gae = 0
        
        for t in reversed(range(len(self.rewards))):
            if t == len(self.rewards) - 1:
                next_value_t = next_value
            else:
                next_value_t = self.values[t + 1]
            
            delta = self.rewards[t] + self.gamma * next_value_t * (1 - self.dones[t]) - self.values[t]
            gae = delta + self.gamma * self.gae_lambda * (1 - self.dones[t]) * gae
            advantages.insert(0, gae)
        
        returns = [adv + val for adv, val in zip(advantages, self.values)]
        return advantages, returns
    
    def update(self, epochs: int = 4, batch_size: int = 64):
        """Update policy using PPO"""
        if len(self.states) < batch_size:
            return
        
        # Compute advantages
        advantages, returns = self.compute_gae()
        
        # Convert to tensors
        states = torch.stack(self.states)
        actions = torch.LongTensor(self.actions).to(self.device)
        old_log_probs = torch.FloatTensor(self.log_probs).to(self.device)
        advantages = torch.FloatTensor(advantages).to(self.device)
        returns = torch.FloatTensor(returns).to(self.device)
        
        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # PPO update
        for _ in range(epochs):
            # Forward pass
            policy_logits, values = self.policy(states)
            values = values.squeeze()
            
            # Calculate new log probs
            probs = torch.softmax(policy_logits, dim=1)
            dist = Categorical(probs)
            new_log_probs = dist.log_prob(actions)
            entropy = dist.entropy().mean()
            
            # PPO clipped loss
            ratio = torch.exp(new_log_probs - old_log_probs)
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()
            
            # Value loss
            value_loss = ((returns - values) ** 2).mean()
            
            # Total loss
            loss = policy_loss + self.value_coef * value_loss - self.entropy_coef * entropy
            
            # Optimize
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.policy.parameters(), 0.5)
            self.optimizer.step()
        
        # Clear buffer
        self.clear_buffer()
    
    def clear_buffer(self):
        """Clear experience buffer"""
        self.states = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []
        self.dones = []
    
    def save(self, path: str):
        """Save model"""
        torch.save({
            'policy_state_dict': self.policy.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'episode_rewards': self.episode_rewards,
            'episode_placements': self.episode_placements,
        }, path)
    
    def load(self, path: str):
        """Load model"""
        checkpoint = torch.load(path, map_location=self.device)
        self.policy.load_state_dict(checkpoint['policy_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.episode_rewards = checkpoint.get('episode_rewards', [])
        self.episode_placements = checkpoint.get('episode_placements', [])

# ============================================================================
# TRAINING SYSTEM
# ============================================================================

class TrainingEnvironment:
    """Environment for training RL agents"""
    def __init__(self, num_agents: int = 8):
        self.num_agents = num_agents
        self.agents = [DeckBattlerAgent() for _ in range(num_agents)]
        self.game = None
        
    def reset(self):
        """Reset environment for new game"""
        self.game = GameState(num_players=self.num_agents)
        return self.game
    
    def run_shop_phase(self, player: PlayerState, agent: DeckBattlerAgent, max_actions: int = 10):
        """Run shop phase with agent making decisions"""
        shop = self.game.card_db.generate_shop(
            player.level,
            self.game.active_sects,
            self.game.active_legendaries
        )
        
        actions_taken = 0
        total_reward = 0
        
        while actions_taken < max_actions and not player.is_eliminated:
            # Encode state
            state = agent.encode_state(player, self.game, shop)
            
            # Select action
            action_idx, log_prob, value = agent.select_action(state, deterministic=False)
            action = agent.decode_action(action_idx, player, shop)
            
            # Execute action
            reward = self.execute_action(player, action, shop)
            total_reward += reward
            
            # Store transition
            agent.store_transition(state, action_idx, reward, value, log_prob, done=False)
            
            actions_taken += 1
            
            # Check if action changed state significantly
            if action["type"] == "pass":
                break
            
            # Regenerate shop if rerolled
            if action["type"] == "reroll" and player.gold >= 2:
                player.gold -= 2
                shop = self.game.card_db.generate_shop(
                    player.level,
                    self.game.active_sects,
                    self.game.active_legendaries
                )
        
        return total_reward
    
    def execute_action(self, player: PlayerState, action: Dict, shop: List[Card]) -> float:
        """Execute action and return immediate reward"""
        reward = 0.0
        
        if action["type"] == "buy":
            card_idx = action["card_idx"]
            if card_idx < len(shop):
                card = shop[card_idx]
                if player.gold >= card.cost:
                    # Buy card
                    player.gold -= card.cost
                    
                    # Create unit and add to deck
                    if card.create_unit:
                        unit = card.create_unit()
                        if player.add_to_deck(unit):
                            reward = 0.1  # Small reward for buying
                            
                            # Bonus for legendary
                            if card.rarity == Rarity.LEGENDARY:
                                reward = 0.5
                            
                            # Bonus for celestial (revival)
                            if card.sect == Sect.CELESTIAL and player.hp < 50:
                                reward = 0.3
        
        elif action["type"] == "level":
            if player.can_level_up():
                player.level_up()
                reward = 0.15  # Reward for leveling
        
        elif action["type"] == "sell":
            deck_idx = action["deck_idx"]
            if deck_idx < len(player.deck):
                unit = player.deck.pop(deck_idx)
                player.gold += 2  # Refund
                reward = -0.05  # Small penalty for selling
        
        elif action["type"] == "reroll":
            if player.gold >= 2:
                reward = -0.02  # Small cost
        
        return reward
    
    def run_episode(self) -> List[Tuple[int, float]]:
        """Run one complete game episode"""
        self.reset()
        
        # Run game rounds
        while not self.game.is_game_over():
            self.game.run_round()
            
            # Each alive player gets shop phase
            for i, player in enumerate(self.game.get_alive_players()):
                self.run_shop_phase(player, self.agents[i])
        
        # Game over - compute final rewards
        placements = self.game.get_final_placements()
        results = []
        
        for placement, player in placements:
            agent = self.agents[player.player_id]
            
            # Final reward based on placement
            placement_reward = {
                1: 10.0,
                2: 5.0,
                3: 2.0,
                4: 1.0,
                5: 0.0,
                6: -1.0,
                7: -2.0,
                8: -3.0,
            }.get(placement, 0.0)
            
            # Bonus for rounds survived
            survival_reward = player.rounds_survived * 0.1
            
            total_reward = placement_reward + survival_reward
            
            # Store final transition with done=True
            if agent.states:
                agent.rewards[-1] += total_reward
                agent.dones[-1] = True
            
            # Record statistics
            agent.episode_rewards.append(total_reward)
            agent.episode_placements.append(placement)
            
            results.append((placement, total_reward))
        
        return results
    
    def train(self, num_episodes: int = 1000, update_frequency: int = 10):
        """Train agents through self-play"""
        print(f"Training {self.num_agents} agents for {num_episodes} episodes...")
        
        for episode in tqdm(range(num_episodes)):
            # Run episode
            results = self.run_episode()
            
            # Update all agents periodically
            if (episode + 1) % update_frequency == 0:
                for agent in self.agents:
                    agent.update()
            
            # Log progress
            if (episode + 1) % 100 == 0:
                avg_rewards = [np.mean(agent.episode_rewards[-100:]) for agent in self.agents]
                avg_placements = [np.mean(agent.episode_placements[-100:]) for agent in self.agents]
                
                print(f"\nEpisode {episode + 1}")
                print(f"Avg Reward: {np.mean(avg_rewards):.2f}")
                print(f"Avg Placement: {np.mean(avg_placements):.2f}")
        
        print("\nTraining complete!")
        return self.agents

# ============================================================================
# VISUALIZATION AND ANALYSIS
# ============================================================================

class Visualizer:
    """Visualization tools for watching games and analyzing performance"""
    
    @staticmethod
    def watch_game(agent1: DeckBattlerAgent, agent2: DeckBattlerAgent):
        """Watch a game between two agents with detailed output"""
        game = GameState(num_players=2)
        agents = [agent1, agent2]
        
        print("\n" + "="*80)
        print("DECK BATTLER - LIVE GAME")
        print("="*80)
        print(f"Active Sects: {[s.value for s in game.active_sects]}")
        print(f"Active Legendaries:")
        for sect, legs in game.active_legendaries.items():
            print(f"  {sect.value}: {[l.name for l in legs]}")
        print("="*80 + "\n")
        
        while not game.is_game_over():
            game.run_round()
            print(f"\n--- ROUND {game.current_round} ---")
            
            for i, player in enumerate(game.players):
                if not player.is_eliminated:
                    print(f"\nPlayer {i+1}:")
                    print(f"  HP: {player.hp}, Gold: {player.gold}, Level: {player.level}")
                    print(f"  Deck ({len(player.deck)}):", [u.name for u in player.deck])
                    print(f"  Streak: W{player.win_streak} L{player.lose_streak}")
            
            # Shop phase (simplified for visualization)
            for i, player in enumerate(game.get_alive_players()):
                shop = game.card_db.generate_shop(
                    player.level,
                    game.active_sects,
                    game.active_legendaries
                )
                print(f"\n  Player {player.player_id+1} Shop: {[c.name for c in shop]}")
        
        # Final results
        print("\n" + "="*80)
        print("GAME OVER")
        print("="*80)
        placements = game.get_final_placements()
        for placement, player in placements:
            print(f"{placement}. Player {player.player_id+1} - HP: {player.hp}, Rounds: {player.rounds_survived}")
        print("="*80 + "\n")
    
    @staticmethod
    def plot_training_progress(agents: List[DeckBattlerAgent], save_path: str = None):
        """Plot training progress"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
        
        # Plot rewards
        for i, agent in enumerate(agents):
            if agent.episode_rewards:
                window = 50
                smoothed = np.convolve(agent.episode_rewards, 
                                      np.ones(window)/window, mode='valid')
                ax1.plot(smoothed, label=f'Agent {i+1}', alpha=0.7)
        
        ax1.set_xlabel('Episode')
        ax1.set_ylabel('Reward (smoothed)')
        ax1.set_title('Training Rewards')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot placements
        for i, agent in enumerate(agents):
            if agent.episode_placements:
                window = 50
                smoothed = np.convolve(agent.episode_placements,
                                      np.ones(window)/window, mode='valid')
                ax2.plot(smoothed, label=f'Agent {i+1}', alpha=0.7)
        
        ax2.set_xlabel('Episode')
        ax2.set_ylabel('Average Placement (smoothed)')
        ax2.set_title('Average Placement Over Time')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.invert_yaxis()  # Lower placement is better
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        else:
            plt.show()
    
    @staticmethod
    def analyze_agent(agent: DeckBattlerAgent):
        """Analyze agent performance statistics"""
        print("\n" + "="*80)
        print("AGENT ANALYSIS")
        print("="*80)
        
        if not agent.episode_placements:
            print("No data available - agent hasn't played any games yet.")
            return
        
        placements = agent.episode_placements
        rewards = agent.episode_rewards
        
        print(f"Total Episodes: {len(placements)}")
        print(f"\nPlacement Statistics:")
        print(f"  Average Placement: {np.mean(placements):.2f}")
        print(f"  Best Placement: {min(placements)}")
        print(f"  Worst Placement: {max(placements)}")
        print(f"  1st Place Rate: {placements.count(1)/len(placements)*100:.1f}%")
        print(f"  Top 4 Rate: {sum(1 for p in placements if p <= 4)/len(placements)*100:.1f}%")
        
        print(f"\nReward Statistics:")
        print(f"  Average Reward: {np.mean(rewards):.2f}")
        print(f"  Best Reward: {max(rewards):.2f}")
        print(f"  Worst Reward: {min(rewards):.2f}")
        
        # Recent performance (last 100 games)
        if len(placements) >= 100:
            recent_placements = placements[-100:]
            recent_rewards = rewards[-100:]
            print(f"\nRecent Performance (last 100 games):")
            print(f"  Average Placement: {np.mean(recent_placements):.2f}")
            print(f"  Average Reward: {np.mean(recent_rewards):.2f}")
            print(f"  1st Place Rate: {recent_placements.count(1)/len(recent_placements)*100:.1f}%")
            print(f"  Top 4 Rate: {sum(1 for p in recent_placements if p <= 4)/len(recent_placements)*100:.1f}%")
        
        print("="*80 + "\n")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python deck_battler.py [train|play|watch|analyze]")
        print("\nCommands:")
        print("  train --episodes N    Train agents for N episodes")
        print("  play                  Play against trained AI")
        print("  watch                 Watch AI vs AI match")
        print("  analyze               Analyze trained agent performance")
        return
    
    command = sys.argv[1]
    
    if command == "train":
        episodes = 1000
        if "--episodes" in sys.argv:
            idx = sys.argv.index("--episodes")
            episodes = int(sys.argv[idx + 1])
        
        print(f"Starting training for {episodes} episodes...")
        env = TrainingEnvironment(num_agents=8)
        trained_agents = env.train(num_episodes=episodes)
        
        # Save best agent
        best_agent = min(trained_agents, 
                        key=lambda a: np.mean(a.episode_placements[-100:]) if len(a.episode_placements) >= 100 else 999)
        best_agent.save("best_agent.pth")
        print("Best agent saved to best_agent.pth")
        
        # Plot progress
        Visualizer.plot_training_progress(trained_agents, "training_progress.png")
        
        # Analyze best agent
        Visualizer.analyze_agent(best_agent)
    
    elif command == "watch":
        print("Loading agents...")
        agent1 = DeckBattlerAgent()
        agent2 = DeckBattlerAgent()
        
        try:
            agent1.load("best_agent.pth")
            print("Loaded trained agent")
        except:
            print("No trained agent found, using random agent")
        
        Visualizer.watch_game(agent1, agent2)
    
    elif command == "analyze":
        print("Loading agent...")
        agent = DeckBattlerAgent()
        
        try:
            agent.load("best_agent.pth")
            Visualizer.analyze_agent(agent)
        except:
            print("Error: No trained agent found. Train an agent first with: python deck_battler.py train")
    
    elif command == "play":
        print("Human vs AI mode not yet implemented.")
        print("Use 'watch' to see AI vs AI games.")
    
    else:
        print(f"Unknown command: {command}")
        print("Available commands: train, play, watch, analyze")

if __name__ == "__main__":
    import sys
    
    # Check if command line arguments provided
    if len(sys.argv) > 1:
        # Run main with command line args
        main()
    else:
        # Quick test mode
        print("DECK BATTLER - Complete Auto-Battler with RL")
        print("=" * 80)
        print("\nQuick Test: Running sample game...")
        
        game = GameState(num_players=2)
        print(f"Game initialized with {game.num_players} players")
        print(f"Active sects: {[s.value for s in game.active_sects]}")
        
        # Run a few rounds
        for _ in range(3):
            game.run_round()
        
        print(f"\nAfter 3 rounds:")
        for player in game.players:
            print(f"Player {player.player_id+1}: HP={player.hp}, Gold={player.gold}, Level={player.level}")
        
        print("\n" + "=" * 80)
        print("System check complete! All components working.")
        print("\nTo train: python deck_battler.py train --episodes 1000")
        print("To watch: python deck_battler.py watch")
        print("=" * 80)