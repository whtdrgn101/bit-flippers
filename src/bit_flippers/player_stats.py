"""Player stats, combat formulas, stat allocation, and JSON persistence."""
import json
import os
from dataclasses import dataclass, asdict

_SAVE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir)
)
_SAVE_PATH = os.path.join(_SAVE_DIR, "player_stats.json")


@dataclass
class PlayerStats:
    max_hp: int = 30
    max_sp: int = 10
    strength: int = 5
    dexterity: int = 5
    resilience: int = 3
    constitution: int = 3
    intelligence: int = 3
    level: int = 1
    xp: int = 0
    money: int = 0
    unspent_points: int = 0
    current_hp: int = 30
    current_sp: int = 10


# ---------------------------------------------------------------------------
# Combat formula functions
# ---------------------------------------------------------------------------

def effective_attack(stats: PlayerStats) -> int:
    """Derive attack power from stats. At level 1: 3 + 5 = 8 (matches original)."""
    return 3 + stats.strength


def effective_defense(stats: PlayerStats) -> int:
    """Derive defense from stats. At level 1: 3 (matches original)."""
    return stats.resilience


def calc_hit_chance(attacker_dex: int, defender_dex: int) -> float:
    """Calculate hit probability. Base 85%, +3% per dex advantage, clamped [30%, 99%]."""
    base = 0.85
    diff = attacker_dex - defender_dex
    chance = base + diff * 0.03
    return max(0.30, min(0.99, chance))


def calc_debuff_duration(base_turns: int, constitution: int) -> int:
    """Reduce debuff duration by 1 per 3 CON above 3, minimum 1 turn."""
    reduction = max(0, (constitution - 3) // 3)
    return max(1, base_turns - reduction)


def calc_skill_multiplier(intelligence: int) -> float:
    """Skill damage multiplier based on INT. 1.0 at INT=3."""
    return 1.0 + (intelligence - 3) * 0.05


# ---------------------------------------------------------------------------
# Stat allocation
# ---------------------------------------------------------------------------

def points_for_level(level: int) -> int:
    """Stat points awarded on reaching *level*. 0 for level 1."""
    if level <= 1:
        return 0
    if level % 10 == 0:
        return 4
    return 2


# How much each stat increases per point spent
STAT_POINT_VALUES: dict[str, int] = {
    "max_hp": 3,
    "max_sp": 2,
    "strength": 1,
    "dexterity": 1,
    "resilience": 1,
    "constitution": 1,
    "intelligence": 1,
}

# Ordered list of allocatable stats for the character screen
STAT_ORDER = ["max_hp", "max_sp", "strength", "dexterity", "resilience", "constitution", "intelligence"]

STAT_DESCRIPTIONS: dict[str, str] = {
    "max_hp": "Maximum hit points (+3 per point)",
    "max_sp": "Maximum skill points (+2 per point)",
    "strength": "Physical attack power (+1 per point)",
    "dexterity": "Hit chance and evasion (+1 per point)",
    "resilience": "Physical defense (+1 per point)",
    "constitution": "Reduces debuff duration (+1 per point)",
    "intelligence": "Skill damage multiplier (+1 per point)",
}

STAT_DISPLAY_NAMES: dict[str, str] = {
    "max_hp": "Max HP",
    "max_sp": "Max SP",
    "strength": "STR",
    "dexterity": "DEX",
    "resilience": "RES",
    "constitution": "CON",
    "intelligence": "INT",
}


# ---------------------------------------------------------------------------
# JSON persistence
# ---------------------------------------------------------------------------

def save_stats(stats: PlayerStats, path: str | None = None) -> None:
    """Save player stats to JSON."""
    p = path or _SAVE_PATH
    with open(p, "w") as f:
        json.dump(asdict(stats), f, indent=2)


def load_stats(path: str | None = None) -> PlayerStats:
    """Load player stats from JSON, returning defaults on error."""
    p = path or _SAVE_PATH
    try:
        with open(p, "r") as f:
            data = json.load(f)
        return PlayerStats(**{k: v for k, v in data.items() if k in PlayerStats.__dataclass_fields__})
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return PlayerStats()
