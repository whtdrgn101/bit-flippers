"""Externalized string loader for game text and NPC dialogue."""
import json
import os

_STRINGS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    os.pardir, os.pardir, "assets", "strings.json",
)
_STRINGS_PATH = os.path.normpath(_STRINGS_PATH)

_cache: dict | None = None


def load_strings() -> dict:
    """Load and cache strings from assets/strings.json."""
    global _cache
    if _cache is None:
        with open(_STRINGS_PATH, "r") as f:
            _cache = json.load(f)
    return _cache


def get_npc_dialogue(key: str) -> list[str]:
    """Return dialogue lines for the given NPC key."""
    strings = load_strings()
    return list(strings.get("npcs", {}).get(key, []))


def get_string(path: str) -> str:
    """Dot-path accessor, e.g. get_string('title_screen.title')."""
    strings = load_strings()
    parts = path.split(".")
    node = strings
    for part in parts:
        if isinstance(node, dict):
            node = node.get(part, "")
        else:
            return ""
    return node if isinstance(node, str) else ""
