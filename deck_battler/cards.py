"""Card database containing all units and abilities."""
from __future__ import annotations

import random
from collections import defaultdict
from typing import Dict, List

from .enums import CardType, Rarity, Sect, StatusEffect, TriggerType
from .models import Ability, Card, Unit


class CardDatabase:
    """Holds every card blueprint that can appear in the game."""

    def __init__(self) -> None:
        self.all_cards: List[Card] = []
        self.legendaries_by_sect: Dict[Sect, List[Card]] = defaultdict(list)
        self._initialize_cards()

    # ------------------------------------------------------------------
    # Card initialization helpers per sect
    # ------------------------------------------------------------------

    def _initialize_cards(self) -> None:
        self._add_iron_cards()
        self._add_shadow_cards()
        self._add_celestial_cards()
        self._add_infernal_cards()
        self._add_nature_cards()
        self._add_arcane_cards()

    def _add_iron_cards(self) -> None:
        self.all_cards.append(
            Card(
                "Iron Warrior",
                CardType.UNIT,
                Sect.IRON,
                Rarity.COMMON,
                3,
                lambda: Unit("Iron Warrior", Sect.IRON, Rarity.COMMON, 80, 80, 15, 8, 1.0),
                description="Sturdy frontline fighter",
            )
        )

        self.all_cards.append(
            Card(
                "Shield Bearer",
                CardType.UNIT,
                Sect.IRON,
                Rarity.COMMON,
                3,
                lambda: Unit(
                    "Shield Bearer",
                    Sect.IRON,
                    Rarity.COMMON,
                    100,
                    100,
                    10,
                    12,
                    0.8,
                    abilities=[
                        Ability(
                            "Shield Wall",
                            TriggerType.COMBAT_START,
                            lambda u, c: c.apply_team_buff(u.sect, "defense", 5, 5.0),
                            description="Grant allies +5 DEF for 5s",
                        )
                    ],
                ),
                description="Protective defender",
            )
        )

        self.all_cards.append(
            Card(
                "Iron Vanguard",
                CardType.UNIT,
                Sect.IRON,
                Rarity.UNCOMMON,
                3,
                lambda: Unit(
                    "Iron Vanguard",
                    Sect.IRON,
                    Rarity.UNCOMMON,
                    120,
                    120,
                    20,
                    10,
                    1.0,
                    abilities=[
                        Ability(
                            "Taunt",
                            TriggerType.COMBAT_START,
                            lambda u, c: setattr(u, "atk", u.atk * 1.2),
                            description="Gain +20% ATK",
                        )
                    ],
                ),
                description="Elite warrior",
            )
        )

        self.all_cards.append(
            Card(
                "Adamant Guardian",
                CardType.UNIT,
                Sect.IRON,
                Rarity.RARE,
                4,
                lambda: Unit(
                    "Adamant Guardian",
                    Sect.IRON,
                    Rarity.RARE,
                    150,
                    150,
                    25,
                    15,
                    0.9,
                    abilities=[
                        Ability(
                            "Fortify",
                            TriggerType.ON_DAMAGED,
                            lambda u, c: u.apply_status(StatusEffect.BUFF_DEF, 2.0),
                            cooldown=3.0,
                            description="Gain DEF buff when hit",
                        )
                    ],
                ),
                description="Grows stronger when attacked",
            )
        )

        self.all_cards.append(
            Card(
                "Unbreakable Titan",
                CardType.UNIT,
                Sect.IRON,
                Rarity.EPIC,
                5,
                lambda: Unit(
                    "Unbreakable Titan",
                    Sect.IRON,
                    Rarity.EPIC,
                    200,
                    200,
                    30,
                    20,
                    0.8,
                    abilities=[
                        Ability(
                            "Last Stand",
                            TriggerType.HP_THRESHOLD,
                            lambda u, c: setattr(u, "atk", u.atk * 2),
                            threshold=0.3,
                            description="Double ATK below 30% HP",
                        )
                    ],
                ),
                description="Becomes mighty when endangered",
            )
        )

        legendary1 = Card(
            "Fortress Eternal",
            CardType.UNIT,
            Sect.IRON,
            Rarity.LEGENDARY,
            6,
            lambda: Unit(
                "Fortress Eternal",
                Sect.IRON,
                Rarity.LEGENDARY,
                250,
                250,
                35,
                30,
                0.7,
                abilities=[
                    Ability(
                        "Immovable",
                        TriggerType.COMBAT_START,
                        lambda u, c: c.apply_team_effect(lambda unit: unit.take_damage(-50)),
                        description="Team takes 50% reduced damage",
                    )
                ],
            ),
            description="LEGENDARY: Your team becomes a fortress",
        )
        self.all_cards.append(legendary1)
        self.legendaries_by_sect[Sect.IRON].append(legendary1)

        legendary2 = Card(
            "Iron Colossus",
            CardType.UNIT,
            Sect.IRON,
            Rarity.LEGENDARY,
            6,
            lambda: Unit(
                "Iron Colossus",
                Sect.IRON,
                Rarity.LEGENDARY,
                300,
                300,
                40,
                25,
                0.6,
                abilities=[
                    Ability(
                        "Earthquake",
                        TriggerType.ON_ATTACK,
                        lambda u, c: c.aoe_damage_enemies(20),
                        cooldown=4.0,
                        description="AOE 20 damage every 4s",
                    )
                ],
            ),
            description="LEGENDARY: Devastates all enemies",
        )
        self.all_cards.append(legendary2)
        self.legendaries_by_sect[Sect.IRON].append(legendary2)

    def _add_shadow_cards(self) -> None:
        self.all_cards.append(
            Card(
                "Shadow Blade",
                CardType.UNIT,
                Sect.SHADOW,
                Rarity.COMMON,
                3,
                lambda: Unit("Shadow Blade", Sect.SHADOW, Rarity.COMMON, 60, 60, 25, 3, 1.5),
                description="Fast, fragile attacker",
            )
        )

        self.all_cards.append(
            Card(
                "Night Stalker",
                CardType.UNIT,
                Sect.SHADOW,
                Rarity.UNCOMMON,
                3,
                lambda: Unit(
                    "Night Stalker",
                    Sect.SHADOW,
                    Rarity.UNCOMMON,
                    70,
                    70,
                    30,
                    4,
                    1.6,
                    abilities=[
                        Ability(
                            "Ambush",
                            TriggerType.COMBAT_START,
                            lambda u, c: c.instant_damage_weakest(40),
                            description="Deal 40 damage to weakest enemy",
                        )
                    ],
                ),
                description="Strike from shadows",
            )
        )

        self.all_cards.append(
            Card(
                "Silent Assassin",
                CardType.UNIT,
                Sect.SHADOW,
                Rarity.RARE,
                4,
                lambda: Unit(
                    "Silent Assassin",
                    Sect.SHADOW,
                    Rarity.RARE,
                    80,
                    80,
                    40,
                    5,
                    1.7,
                    abilities=[
                        Ability(
                            "Execute",
                            TriggerType.ON_ATTACK,
                            lambda u, c: c.execute_low_hp_enemy(0.25),
                            cooldown=5.0,
                            description="Kill enemies below 25% HP",
                        )
                    ],
                ),
                description="Finishes wounded foes",
            )
        )

        self.all_cards.append(
            Card(
                "Shadow Master",
                CardType.UNIT,
                Sect.SHADOW,
                Rarity.EPIC,
                5,
                lambda: Unit(
                    "Shadow Master",
                    Sect.SHADOW,
                    Rarity.EPIC,
                    90,
                    90,
                    50,
                    5,
                    1.8,
                    abilities=[
                        Ability(
                            "Chain Kill",
                            TriggerType.ON_KILL,
                            lambda u, c: setattr(u, "atk", u.atk * 1.15),
                            description="Gain +15% ATK per kill",
                        )
                    ],
                ),
                description="Grows stronger with each kill",
            )
        )

        legendary1 = Card(
            "Reaper's Shadow",
            CardType.UNIT,
            Sect.SHADOW,
            Rarity.LEGENDARY,
            6,
            lambda: Unit(
                "Reaper's Shadow",
                Sect.SHADOW,
                Rarity.LEGENDARY,
                100,
                100,
                55,
                6,
                1.9,
                abilities=[
                    Ability(
                        "Harvest",
                        TriggerType.ON_ATTACK,
                        lambda u, c: c.execute_all_low_hp(0.4),
                        cooldown=6.0,
                        description="Execute enemies below 40% HP",
                    )
                ],
            ),
            description="LEGENDARY: Cleanses the weak",
        )
        self.all_cards.append(legendary1)
        self.legendaries_by_sect[Sect.SHADOW].append(legendary1)

        legendary2 = Card(
            "Veil of Night",
            CardType.UNIT,
            Sect.SHADOW,
            Rarity.LEGENDARY,
            6,
            lambda: Unit(
                "Veil of Night",
                Sect.SHADOW,
                Rarity.LEGENDARY,
                110,
                110,
                45,
                6,
                1.7,
                abilities=[
                    Ability(
                        "Dark Culling",
                        TriggerType.COMBAT_START,
                        lambda u, c: c.kill_highest_hp_enemy(),
                        description="Slay the strongest foe",
                    )
                ],
            ),
            description="LEGENDARY: Ends the mightiest",
        )
        self.all_cards.append(legendary2)
        self.legendaries_by_sect[Sect.SHADOW].append(legendary2)

    def _add_celestial_cards(self) -> None:
        self.all_cards.append(
            Card(
                "Radiant Healer",
                CardType.UNIT,
                Sect.CELESTIAL,
                Rarity.COMMON,
                3,
                lambda: Unit(
                    "Radiant Healer",
                    Sect.CELESTIAL,
                    Rarity.COMMON,
                    70,
                    70,
                    12,
                    6,
                    1.0,
                    abilities=[
                        Ability(
                            "Light Mend",
                            TriggerType.EVERY_TICK,
                            lambda u, c: c.heal_team(5),
                            cooldown=2.0,
                            description="Heal allies each tick",
                        )
                    ],
                ),
                description="Sustains allies",
            )
        )

        self.all_cards.append(
            Card(
                "Guardian Acolyte",
                CardType.UNIT,
                Sect.CELESTIAL,
                Rarity.UNCOMMON,
                3,
                lambda: Unit(
                    "Guardian Acolyte",
                    Sect.CELESTIAL,
                    Rarity.UNCOMMON,
                    90,
                    90,
                    16,
                    8,
                    1.1,
                    abilities=[
                        Ability(
                            "Sacred Shield",
                            TriggerType.COMBAT_START,
                            lambda u, c: c.apply_team_invuln(2.0),
                            description="Grant shield for 2s",
                        )
                    ],
                ),
                description="Protective support",
            )
        )

        self.all_cards.append(
            Card(
                "Divine Cleric",
                CardType.UNIT,
                Sect.CELESTIAL,
                Rarity.RARE,
                4,
                lambda: Unit(
                    "Divine Cleric",
                    Sect.CELESTIAL,
                    Rarity.RARE,
                    95,
                    95,
                    18,
                    7,
                    1.1,
                    abilities=[
                        Ability(
                            "Restoration",
                            TriggerType.EVERY_TICK,
                            lambda u, c: c.heal_team(15),
                            cooldown=3.0,
                            description="Heal allies",
                        )
                    ],
                ),
                description="Stronger healing",
            )
        )

        self.all_cards.append(
            Card(
                "Seraphic Guardian",
                CardType.UNIT,
                Sect.CELESTIAL,
                Rarity.EPIC,
                5,
                lambda: Unit(
                    "Seraphic Guardian",
                    Sect.CELESTIAL,
                    Rarity.EPIC,
                    130,
                    130,
                    22,
                    10,
                    1.1,
                    abilities=[
                        Ability(
                            "Rebirth",
                            TriggerType.ON_DEATH,
                            lambda u, c: c.revive_unit(u, 0.5),
                            description="Revive ally at 50% HP",
                        )
                    ],
                ),
                description="Resurrection magic",
            )
        )

        legendary1 = Card(
            "Divine Intervention",
            CardType.UNIT,
            Sect.CELESTIAL,
            Rarity.LEGENDARY,
            6,
            lambda: Unit(
                "Divine Intervention",
                Sect.CELESTIAL,
                Rarity.LEGENDARY,
                120,
                120,
                30,
                12,
                1.2,
                abilities=[
                    Ability(
                        "Grace",
                        TriggerType.COMBAT_START,
                        lambda u, c: c.apply_team_invuln(5.0),
                        description="Ally invulnerability",
                    )
                ],
            ),
            description="LEGENDARY: Untouchable",
        )
        self.all_cards.append(legendary1)
        self.legendaries_by_sect[Sect.CELESTIAL].append(legendary1)

        legendary2 = Card(
            "Sun's Embrace",
            CardType.UNIT,
            Sect.CELESTIAL,
            Rarity.LEGENDARY,
            6,
            lambda: Unit(
                "Sun's Embrace",
                Sect.CELESTIAL,
                Rarity.LEGENDARY,
                140,
                140,
                26,
                11,
                1.2,
                abilities=[
                    Ability(
                        "Purifying Flames",
                        TriggerType.ON_ATTACK,
                        lambda u, c: c.apply_burn_to_target(10, 3.0),
                        cooldown=3.0,
                        description="Burn enemies",
                    )
                ],
            ),
            description="LEGENDARY: Burn with the light",
        )
        self.all_cards.append(legendary2)
        self.legendaries_by_sect[Sect.CELESTIAL].append(legendary2)

    def _add_infernal_cards(self) -> None:
        self.all_cards.append(
            Card(
                "Flame Acolyte",
                CardType.UNIT,
                Sect.INFERNAL,
                Rarity.COMMON,
                3,
                lambda: Unit("Flame Acolyte", Sect.INFERNAL, Rarity.COMMON, 75, 75, 24, 5, 1.2),
                description="Aggressive fighter",
            )
        )

        self.all_cards.append(
            Card(
                "Hellfire Mage",
                CardType.UNIT,
                Sect.INFERNAL,
                Rarity.UNCOMMON,
                3,
                lambda: Unit(
                    "Hellfire Mage",
                    Sect.INFERNAL,
                    Rarity.UNCOMMON,
                    70,
                    70,
                    30,
                    4,
                    1.3,
                    abilities=[
                        Ability(
                            "Fire Nova",
                            TriggerType.EVERY_TICK,
                            lambda u, c: c.aoe_damage_enemies(15),
                            cooldown=3.0,
                            description="AOE burn",
                        )
                    ],
                ),
                description="Burning magic",
            )
        )

        self.all_cards.append(
            Card(
                "Infernal Knight",
                CardType.UNIT,
                Sect.INFERNAL,
                Rarity.RARE,
                4,
                lambda: Unit(
                    "Infernal Knight",
                    Sect.INFERNAL,
                    Rarity.RARE,
                    110,
                    110,
                    32,
                    9,
                    1.1,
                    abilities=[
                        Ability(
                            "Blazing Trail",
                            TriggerType.ON_ATTACK,
                            lambda u, c: c.aoe_damage_enemies(25),
                            cooldown=4.0,
                            description="AOE strike",
                        )
                    ],
                ),
                description="Spreads fire",
            )
        )

        self.all_cards.append(
            Card(
                "Soul Harvester",
                CardType.UNIT,
                Sect.INFERNAL,
                Rarity.EPIC,
                5,
                lambda: Unit(
                    "Soul Harvester",
                    Sect.INFERNAL,
                    Rarity.EPIC,
                    100,
                    100,
                    36,
                    8,
                    1.2,
                    abilities=[
                        Ability(
                            "Soul Feast",
                            TriggerType.ON_KILL,
                            lambda u, c: setattr(u, "atk", u.atk + 8),
                            description="Gain ATK on kill",
                        )
                    ],
                ),
                description="Devours souls",
            )
        )

        legendary1 = Card(
            "Inferno Overlord",
            CardType.UNIT,
            Sect.INFERNAL,
            Rarity.LEGENDARY,
            6,
            lambda: Unit(
                "Inferno Overlord",
                Sect.INFERNAL,
                Rarity.LEGENDARY,
                150,
                150,
                40,
                10,
                1.3,
                abilities=[
                    Ability(
                        "Hellfire Rain",
                        TriggerType.COMBAT_START,
                        lambda u, c: c.damage_all_units(80),
                        description="Damage everyone",
                    )
                ],
            ),
            description="LEGENDARY: Burn the arena",
        )
        self.all_cards.append(legendary1)
        self.legendaries_by_sect[Sect.INFERNAL].append(legendary1)

        legendary2 = Card(
            "Cinder Queen",
            CardType.UNIT,
            Sect.INFERNAL,
            Rarity.LEGENDARY,
            6,
            lambda: Unit(
                "Cinder Queen",
                Sect.INFERNAL,
                Rarity.LEGENDARY,
                140,
                140,
                34,
                9,
                1.25,
                abilities=[
                    Ability(
                        "Flame Shield",
                        TriggerType.ON_DAMAGED,
                        lambda u, c: c.damage_all_units(20),
                        cooldown=4.0,
                        description="Explodes when hit",
                    )
                ],
            ),
            description="LEGENDARY: Retaliates with fire",
        )
        self.all_cards.append(legendary2)
        self.legendaries_by_sect[Sect.INFERNAL].append(legendary2)

    def _add_nature_cards(self) -> None:
        self.all_cards.append(
            Card(
                "Forest Sentinel",
                CardType.UNIT,
                Sect.NATURE,
                Rarity.COMMON,
                3,
                lambda: Unit("Forest Sentinel", Sect.NATURE, Rarity.COMMON, 85, 85, 18, 7, 1.0),
                description="Reliable bruiser",
            )
        )

        self.all_cards.append(
            Card(
                "Grove Tender",
                CardType.UNIT,
                Sect.NATURE,
                Rarity.UNCOMMON,
                3,
                lambda: Unit(
                    "Grove Tender",
                    Sect.NATURE,
                    Rarity.UNCOMMON,
                    80,
                    80,
                    20,
                    6,
                    1.0,
                    abilities=[
                        Ability(
                            "Nature's Gift",
                            TriggerType.COMBAT_START,
                            lambda u, c: c.apply_team_buff(u.sect, "defense", 8, 10.0),
                            description="Big DEF buff",
                        )
                    ],
                ),
                description="Protective nature magic",
            )
        )

        self.all_cards.append(
            Card(
                "Verdant Sage",
                CardType.UNIT,
                Sect.NATURE,
                Rarity.RARE,
                4,
                lambda: Unit(
                    "Verdant Sage",
                    Sect.NATURE,
                    Rarity.RARE,
                    90,
                    90,
                    22,
                    6,
                    1.0,
                    abilities=[
                        Ability(
                            "Bloom",
                            TriggerType.EVERY_TICK,
                            lambda u, c: c.heal_and_buff_team(8, 3),
                            cooldown=3.0,
                            description="Heal and buff",
                        )
                    ],
                ),
                description="Grow allies",
            )
        )

        self.all_cards.append(
            Card(
                "Ancient Guardian",
                CardType.UNIT,
                Sect.NATURE,
                Rarity.EPIC,
                5,
                lambda: Unit(
                    "Ancient Guardian",
                    Sect.NATURE,
                    Rarity.EPIC,
                    160,
                    160,
                    28,
                    12,
                    0.9,
                    abilities=[
                        Ability(
                            "Call of the Wild",
                            TriggerType.COMBAT_START,
                            lambda u, c: c.summon_treants(3),
                            description="Summon treants",
                        )
                    ],
                ),
                description="Summons allies",
            )
        )

        legendary1 = Card(
            "Heart of the Grove",
            CardType.UNIT,
            Sect.NATURE,
            Rarity.LEGENDARY,
            6,
            lambda: Unit(
                "Heart of the Grove",
                Sect.NATURE,
                Rarity.LEGENDARY,
                150,
                150,
                26,
                10,
                1.0,
                abilities=[
                    Ability(
                        "Verdant Pulse",
                        TriggerType.COMBAT_START,
                        lambda u, c: c.scale_team_permanently(1.05),
                        description="Permanent scaling",
                    )
                ],
            ),
            description="LEGENDARY: Permanent growth",
        )
        self.all_cards.append(legendary1)
        self.legendaries_by_sect[Sect.NATURE].append(legendary1)

        legendary2 = Card(
            "Emerald Warden",
            CardType.UNIT,
            Sect.NATURE,
            Rarity.LEGENDARY,
            6,
            lambda: Unit(
                "Emerald Warden",
                Sect.NATURE,
                Rarity.LEGENDARY,
                130,
                130,
                32,
                9,
                1.1,
                abilities=[
                    Ability(
                        "Nature's Wrath",
                        TriggerType.ON_ATTACK,
                        lambda u, c: c.true_damage_random(25),
                        cooldown=4.0,
                        description="True damage",
                    )
                ],
            ),
            description="LEGENDARY: Nature strikes true",
        )
        self.all_cards.append(legendary2)
        self.legendaries_by_sect[Sect.NATURE].append(legendary2)

    def _add_arcane_cards(self) -> None:
        self.all_cards.append(
            Card(
                "Arcane Apprentice",
                CardType.UNIT,
                Sect.ARCANE,
                Rarity.COMMON,
                3,
                lambda: Unit("Arcane Apprentice", Sect.ARCANE, Rarity.COMMON, 65, 65, 26, 4, 1.3),
                description="Magic novice",
            )
        )

        self.all_cards.append(
            Card(
                "Spell Weaver",
                CardType.UNIT,
                Sect.ARCANE,
                Rarity.UNCOMMON,
                3,
                lambda: Unit(
                    "Spell Weaver",
                    Sect.ARCANE,
                    Rarity.UNCOMMON,
                    70,
                    70,
                    28,
                    5,
                    1.3,
                    abilities=[
                        Ability(
                            "Arcane Bolt",
                            TriggerType.COMBAT_START,
                            lambda u, c: c.stun_random_enemy(2.0),
                            description="Stun random enemy",
                        )
                    ],
                ),
                description="Control mage",
            )
        )

        self.all_cards.append(
            Card(
                "Rune Scholar",
                CardType.UNIT,
                Sect.ARCANE,
                Rarity.RARE,
                4,
                lambda: Unit(
                    "Rune Scholar",
                    Sect.ARCANE,
                    Rarity.RARE,
                    75,
                    75,
                    32,
                    6,
                    1.3,
                    abilities=[
                        Ability(
                            "Chain Lightning",
                            TriggerType.ON_ATTACK,
                            lambda u, c: c.chain_damage(30, 3),
                            cooldown=4.0,
                            description="Chain damage",
                        )
                    ],
                ),
                description="Lightning magic",
            )
        )

        self.all_cards.append(
            Card(
                "Archmage",
                CardType.UNIT,
                Sect.ARCANE,
                Rarity.EPIC,
                5,
                lambda: Unit(
                    "Archmage",
                    Sect.ARCANE,
                    Rarity.EPIC,
                    85,
                    85,
                    34,
                    7,
                    1.4,
                    abilities=[
                        Ability(
                            "Arcane Storm",
                            TriggerType.COMBAT_START,
                            lambda u, c: c.mass_debuff_enemies(),
                            description="Debuff enemies",
                        )
                    ],
                ),
                description="Weakens all enemies",
            )
        )

        legendary1 = Card(
            "Frost Queen",
            CardType.UNIT,
            Sect.ARCANE,
            Rarity.LEGENDARY,
            6,
            lambda: Unit(
                "Frost Queen",
                Sect.ARCANE,
                Rarity.LEGENDARY,
                100,
                100,
                38,
                7,
                1.4,
                abilities=[
                    Ability(
                        "Absolute Zero",
                        TriggerType.COMBAT_START,
                        lambda u, c: c.freeze_all_enemies(4.0),
                        description="Freeze all enemies",
                    )
                ],
            ),
            description="LEGENDARY: Freeze the battlefield",
        )
        self.all_cards.append(legendary1)
        self.legendaries_by_sect[Sect.ARCANE].append(legendary1)

        legendary2 = Card(
            "Ethereal Sage",
            CardType.UNIT,
            Sect.ARCANE,
            Rarity.LEGENDARY,
            6,
            lambda: Unit(
                "Ethereal Sage",
                Sect.ARCANE,
                Rarity.LEGENDARY,
                105,
                105,
                36,
                6,
                1.4,
                abilities=[
                    Ability(
                        "Reality Rift",
                        TriggerType.ON_ATTACK,
                        lambda u, c: c.true_damage_all_enemies(35),
                        cooldown=5.0,
                        description="True damage AOE",
                    )
                ],
            ),
            description="LEGENDARY: Reality bending damage",
        )
        self.all_cards.append(legendary2)
        self.legendaries_by_sect[Sect.ARCANE].append(legendary2)

    # ------------------------------------------------------------------
    # Shop generation
    # ------------------------------------------------------------------

    def generate_shop(self, level: int, active_sects: List[Sect], active_legendaries: Dict[Sect, List[Card]], size: int = 5) -> List[Card]:
        odds = {
            1: {Rarity.COMMON: 0.75, Rarity.UNCOMMON: 0.2, Rarity.RARE: 0.05},
            2: {Rarity.COMMON: 0.7, Rarity.UNCOMMON: 0.25, Rarity.RARE: 0.05},
            3: {Rarity.COMMON: 0.6, Rarity.UNCOMMON: 0.3, Rarity.RARE: 0.1},
            4: {Rarity.COMMON: 0.45, Rarity.UNCOMMON: 0.35, Rarity.RARE: 0.15, Rarity.EPIC: 0.05},
            5: {Rarity.COMMON: 0.35, Rarity.UNCOMMON: 0.35, Rarity.RARE: 0.2, Rarity.EPIC: 0.08, Rarity.LEGENDARY: 0.02},
            6: {Rarity.COMMON: 0.25, Rarity.UNCOMMON: 0.35, Rarity.RARE: 0.25, Rarity.EPIC: 0.12, Rarity.LEGENDARY: 0.03},
            7: {Rarity.COMMON: 0.2, Rarity.UNCOMMON: 0.3, Rarity.RARE: 0.3, Rarity.EPIC: 0.15, Rarity.LEGENDARY: 0.05},
            8: {Rarity.COMMON: 0.1, Rarity.UNCOMMON: 0.25, Rarity.RARE: 0.35, Rarity.EPIC: 0.2, Rarity.LEGENDARY: 0.1},
        }

        shop: List[Card] = []
        available_cards = [c for c in self.all_cards if c.sect in active_sects]

        for _ in range(size):
            rarity_prob = odds.get(level, odds[1])
            rarities = list(rarity_prob.keys())
            weights = list(rarity_prob.values())
            selected_rarity = random.choices(rarities, weights=weights)[0]

            if selected_rarity == Rarity.LEGENDARY:
                sect = random.choice(active_sects)
                candidates = active_legendaries.get(sect, [])
                if candidates:
                    shop.append(random.choice(candidates))
                    continue

            rarity_pool = [c for c in available_cards if c.rarity == selected_rarity]
            if rarity_pool:
                shop.append(random.choice(rarity_pool))

        while len(shop) < size:
            shop.append(random.choice(available_cards))

        return shop
