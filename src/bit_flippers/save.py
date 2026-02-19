"""Full save/load system with 5 save slots."""
import json
import os
import time
from dataclasses import asdict

_SAVE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir)
)

_SAVE_VERSION = 2
_NUM_SLOTS = 5


def _slot_path(slot: int) -> str:
    return os.path.join(_SAVE_DIR, f"savegame_{slot}.json")


def _legacy_path() -> str:
    return os.path.join(_SAVE_DIR, "savegame.json")


def save_game(overworld, slot: int | None = None) -> None:
    """Serialize full game state to a save slot.

    If slot is None, uses overworld.active_save_slot.
    """
    if slot is None:
        slot = getattr(overworld, "active_save_slot", 0)
    overworld._save_current_persistence()

    stats = overworld.stats
    equipment = getattr(overworld, "equipment", None)
    data = {
        "version": _SAVE_VERSION,
        "slot": slot,
        "timestamp": time.time(),
        "stats": asdict(stats),
        "skills": overworld.player_skills.to_dict(),
        "inventory": overworld.inventory.to_dict(),
        "equipment": equipment.to_dict() if equipment else {},
        "quests": overworld.player_quests.to_dict() if hasattr(overworld, "player_quests") else {},
        "current_map_id": overworld.current_map_id,
        "player_x": overworld.player_x,
        "player_y": overworld.player_y,
        "player_facing": overworld.player_facing,
        "steps_since_encounter": overworld.steps_since_encounter,
        "map_persistence": {},
    }

    for map_id, persist in overworld.map_persistence.items():
        data["map_persistence"][map_id] = {
            "collected_scrap": sorted([list(t) for t in persist.collected_scrap]),
            "defeated_enemies": sorted(persist.defeated_enemies),
        }

    with open(_slot_path(slot), "w") as f:
        json.dump(data, f, indent=2)


def load_game(slot: int = 0) -> dict | None:
    """Deserialize save file from a slot, or return None if absent/corrupt.

    For slot 0, also checks for legacy savegame.json and migrates it.
    """
    path = _slot_path(slot)

    # Legacy migration: if slot 0 requested and new file doesn't exist, try old path
    if slot == 0 and not os.path.isfile(path):
        legacy = _legacy_path()
        if os.path.isfile(legacy):
            try:
                with open(legacy, "r") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "version" in data:
                    # Migrate: save to new slot path and remove legacy
                    data["slot"] = 0
                    data["timestamp"] = data.get("timestamp", os.path.getmtime(legacy))
                    with open(path, "w") as f:
                        json.dump(data, f, indent=2)
                    os.remove(legacy)
                    return data
            except (json.JSONDecodeError, TypeError, OSError):
                pass

    try:
        with open(path, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "version" not in data:
            return None
        return data
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return None


def has_save(slot: int | None = None) -> bool:
    """Check whether a save file exists.

    If slot is None, check if ANY slot has a save.
    """
    if slot is not None:
        return os.path.isfile(_slot_path(slot))
    # Check all slots + legacy
    for s in range(_NUM_SLOTS):
        if os.path.isfile(_slot_path(s)):
            return True
    if os.path.isfile(_legacy_path()):
        return True
    return False


def get_slot_summary(slot: int) -> dict | None:
    """Return a summary dict {level, map_id, money, timestamp} or None if empty."""
    data = load_game(slot)
    if data is None:
        return None
    stats = data.get("stats", {})
    return {
        "level": stats.get("level", 1),
        "map_id": data.get("current_map_id", "?"),
        "money": stats.get("money", 0),
        "timestamp": data.get("timestamp", 0),
    }


def delete_save(slot: int | None = None) -> None:
    """Remove save file(s).

    If slot is None, delete ALL slots and legacy file.
    If slot is specified, delete only that slot.
    """
    if slot is not None:
        path = _slot_path(slot)
        if os.path.isfile(path):
            os.remove(path)
        return

    # Delete all slots
    for s in range(_NUM_SLOTS):
        path = _slot_path(s)
        if os.path.isfile(path):
            os.remove(path)
    # Also remove legacy files
    legacy = _legacy_path()
    if os.path.isfile(legacy):
        os.remove(legacy)
    legacy_stats = os.path.join(_SAVE_DIR, "player_stats.json")
    if os.path.isfile(legacy_stats):
        os.remove(legacy_stats)
