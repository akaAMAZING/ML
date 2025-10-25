"""Definitions and helpers for faction (sect) synergies."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .enums import Sect, StatusEffect


@dataclass(frozen=True)
class SynergyLevel:
    count: int
    title: str
    description: str


@dataclass(frozen=True)
class SynergyDefinition:
    sect: Sect
    name: str
    tagline: str
    color: str
    levels: Tuple[SynergyLevel, SynergyLevel, SynergyLevel]


SYNERGY_DEFINITIONS: Dict[Sect, SynergyDefinition] = {
    Sect.IRON: SynergyDefinition(
        Sect.IRON,
        name="Ironclad Vanguard",
        tagline="Form indomitable bulwarks that refuse to fall.",
        color="#38bdf8",
        levels=(
            SynergyLevel(2, "Shieldwall", "Iron units gain +8 DEF at the start of combat."),
            SynergyLevel(
                4,
                "Adamant Bulwark",
                "Iron units gain an additional +15 DEF and +50 Max HP.",
            ),
            SynergyLevel(
                6,
                "Unbreakable Phalanx",
                "All allies gain +10 DEF for the duration of combat.",
            ),
        ),
    ),
    Sect.SHADOW: SynergyDefinition(
        Sect.SHADOW,
        name="Shadow Cabal",
        tagline="Strike from the veiled corners with lethal precision.",
        color="#c084fc",
        levels=(
            SynergyLevel(2, "Ambushers", "Shadow units gain +20% ATK."),
            SynergyLevel(4, "Nightfall", "Shadow units gain +0.3 Speed and retain the ATK bonus."),
            SynergyLevel(
                6,
                "Deathmark",
                "At combat start the lowest HP enemy suffers a 35 damage execution strike.",
            ),
        ),
    ),
    Sect.CELESTIAL: SynergyDefinition(
        Sect.CELESTIAL,
        name="Celestial Chorus",
        tagline="Sanctify the arena with radiant blessings.",
        color="#fde68a",
        levels=(
            SynergyLevel(2, "Guiding Light", "Allies heal 20 HP at combat start."),
            SynergyLevel(4, "Seraphic Guard", "Celestial units gain +10 ATK and +10 DEF."),
            SynergyLevel(
                6,
                "Ascension", "All allies gain a 40 HP barrier at combat start.",
            ),
        ),
    ),
    Sect.INFERNAL: SynergyDefinition(
        Sect.INFERNAL,
        name="Infernal Pact",
        tagline="Let the battlefield burn in chaotic flame.",
        color="#f97316",
        levels=(
            SynergyLevel(2, "Hellbrand", "Two random enemies are afflicted with Burn for 6s."),
            SynergyLevel(4, "Conflagration", "All enemies take 15 damage at combat start."),
            SynergyLevel(
                6,
                "Devour Flame", "Infernal units gain +25 ATK for the fight.",
            ),
        ),
    ),
    Sect.NATURE: SynergyDefinition(
        Sect.NATURE,
        name="Verdant Cycle",
        tagline="Life blooms anew with every skirmish.",
        color="#4ade80",
        levels=(
            SynergyLevel(2, "Wild Growth", "Allies heal 15 HP at combat start."),
            SynergyLevel(4, "Briar Armor", "Nature units gain +15 DEF and +0.2 Speed."),
            SynergyLevel(
                6,
                "Worldheart", "All allies permanently gain +30 Max HP this combat.",
            ),
        ),
    ),
    Sect.ARCANE: SynergyDefinition(
        Sect.ARCANE,
        name="Arcane Conclave",
        tagline="Bend reality with raw spellcraft.",
        color="#60a5fa",
        levels=(
            SynergyLevel(2, "Spellweave", "Arcane units reduce ability cooldowns by 20%."),
            SynergyLevel(4, "Astral Focus", "Arcane units gain +15 ATK."),
            SynergyLevel(
                6,
                "Temporal Surge", "All allies gain +0.2 Speed at combat start.",
            ),
        ),
    ),
}


def _resolve_level(definition: SynergyDefinition, count: int) -> Tuple[int, List[SynergyLevel], Optional[SynergyLevel]]:
    """Return (level, active_levels, next_level) for the provided unit count."""
    active: List[SynergyLevel] = []
    next_level: Optional[SynergyLevel] = None
    level = 0
    for idx, threshold in enumerate(definition.levels, start=1):
        if count >= threshold.count:
            active.append(threshold)
            level = idx
        elif next_level is None:
            next_level = threshold
    return level, active, next_level


def summarize_synergies(
    units: Iterable["Unit"],
    tracked_sects: Iterable[Sect],
) -> List[Dict[str, object]]:
    """Build a rich summary of the player's synergies for UI display."""
    from collections import Counter

    counts = Counter(unit.sect for unit in units)
    results: List[Dict[str, object]] = []
    for sect in tracked_sects:
        definition = SYNERGY_DEFINITIONS[sect]
        count = counts.get(sect, 0)
        level, active_levels, next_level = _resolve_level(definition, count)
        results.append(
            {
                "sect": sect.value,
                "name": definition.name,
                "tagline": definition.tagline,
                "color": definition.color,
                "count": count,
                "level": level,
                "active_bonuses": [lvl.description for lvl in active_levels],
                "next_threshold": next_level.count if next_level else None,
                "next_bonus": next_level.description if next_level else None,
                "levels": [
                    {
                        "count": lvl.count,
                        "title": lvl.title,
                        "description": lvl.description,
                    }
                    for lvl in definition.levels
                ],
            }
        )
    return results


def serialize_synergy_definitions(active_only: Optional[Iterable[Sect]] = None) -> Dict[str, Dict[str, object]]:
    """Return a JSON friendly mapping of synergy definitions."""
    selected = set(active_only) if active_only else set(SYNERGY_DEFINITIONS.keys())
    payload: Dict[str, Dict[str, object]] = {}
    for sect in selected:
        definition = SYNERGY_DEFINITIONS[sect]
        payload[sect.value] = {
            "name": definition.name,
            "tagline": definition.tagline,
            "color": definition.color,
            "levels": [
                {
                    "count": lvl.count,
                    "title": lvl.title,
                    "description": lvl.description,
                }
                for lvl in definition.levels
            ],
        }
    return payload


def get_synergy_levels(units: Iterable["Unit"]) -> Dict[Sect, int]:
    """Return the unlocked synergy level per sect for combat calculations."""
    from collections import Counter

    counts = Counter(unit.sect for unit in units)
    levels: Dict[Sect, int] = {}
    for sect, definition in SYNERGY_DEFINITIONS.items():
        count = counts.get(sect, 0)
        level, _, _ = _resolve_level(definition, count)
        if level:
            levels[sect] = level
    return levels


def apply_synergy_effects(team: List["Unit"], enemy: List["Unit"]) -> Dict[Sect, int]:
    """Apply combat modifiers for all synergies present on ``team``."""
    from random import sample

    levels = get_synergy_levels(team)
    if not levels:
        return {}

    for sect, level in levels.items():
        if sect == Sect.IRON:
            for unit in team:
                if unit.sect == Sect.IRON:
                    unit.defense += 8
            if level >= 2:
                for unit in team:
                    if unit.sect == Sect.IRON:
                        unit.max_hp += 50
                        unit.hp = min(unit.max_hp, unit.hp + 50)
                        unit.defense += 7
            if level >= 3:
                for unit in team:
                    unit.defense += 10

        elif sect == Sect.SHADOW:
            for unit in team:
                if unit.sect == Sect.SHADOW:
                    unit.atk *= 1.2
            if level >= 2:
                for unit in team:
                    if unit.sect == Sect.SHADOW:
                        unit.speed += 0.3
            if level >= 3 and enemy:
                target = min((u for u in enemy if u.is_alive), default=None, key=lambda u: u.hp)
                if target:
                    target.take_damage(35)

        elif sect == Sect.CELESTIAL:
            if level >= 1:
                for unit in team:
                    unit.heal(20)
            if level >= 2:
                for unit in team:
                    if unit.sect == Sect.CELESTIAL:
                        unit.atk += 10
                        unit.defense += 10
            if level >= 3:
                for unit in team:
                    unit.max_hp += 40
                    unit.hp = min(unit.max_hp, unit.hp + 40)

        elif sect == Sect.INFERNAL:
            if level >= 1 and enemy:
                alive_enemies = [u for u in enemy if u.is_alive]
                if alive_enemies:
                    afflicted = sample(alive_enemies, k=min(2, len(alive_enemies)))
                    for target in afflicted:
                        target.apply_status(StatusEffect.BURN, 6.0)
            if level >= 2:
                for unit in enemy:
                    if unit.is_alive:
                        unit.take_damage(15)
            if level >= 3:
                for unit in team:
                    if unit.sect == Sect.INFERNAL:
                        unit.atk += 25

        elif sect == Sect.NATURE:
            if level >= 1:
                for unit in team:
                    unit.heal(15)
            if level >= 2:
                for unit in team:
                    if unit.sect == Sect.NATURE:
                        unit.defense += 15
                        unit.speed += 0.2
            if level >= 3:
                for unit in team:
                    unit.max_hp += 30
                    unit.hp = min(unit.max_hp, unit.hp + 30)

        elif sect == Sect.ARCANE:
            if level >= 1:
                for unit in team:
                    if unit.sect == Sect.ARCANE:
                        for ability in unit.abilities:
                            ability.cooldown *= 0.8
                            ability.current_cooldown = 0.0
            if level >= 2:
                for unit in team:
                    if unit.sect == Sect.ARCANE:
                        unit.atk += 15
            if level >= 3:
                for unit in team:
                    unit.speed += 0.2

    return levels


# Avoid circular imports for type checking
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .models import Unit
