"""Full save/load system for game state."""
import json
import os
from dataclasses import asdict

_SAVE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir)
)
_SAVE_PATH = os.path.join(_SAVE_DIR, "savegame.json")

_SAVE_VERSION = 1


def save_game(overworld) -> None:
    """Serialize full game state to savegame.json."""
    overworld._save_current_persistence()

    stats = overworld.stats
    data = {
        "version": _SAVE_VERSION,
        "stats": asdict(stats),
        "skills": overworld.player_skills.to_dict(),
        "inventory": overworld.inventory.to_dict(),
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

    with open(_SAVE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def load_game() -> dict | None:
    """Deserialize save file, or return None if absent/corrupt."""
    try:
        with open(_SAVE_PATH, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "version" not in data:
            return None
        return data
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return None


def has_save() -> bool:
    """Check whether a save file exists."""
    return os.path.isfile(_SAVE_PATH)


def delete_save() -> None:
    """Remove the save file if it exists."""
    if os.path.isfile(_SAVE_PATH):
        os.remove(_SAVE_PATH)
    # Also remove legacy player_stats.json
    legacy = os.path.join(_SAVE_DIR, "player_stats.json")
    if os.path.isfile(legacy):
        os.remove(legacy)
