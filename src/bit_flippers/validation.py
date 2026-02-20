"""Content validation — catches broken references at map load time."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def validate_map(map_id: str, map_def, tiled_renderer) -> list[str]:
    """Return list of warning/error messages for a map's content references.

    Runs once per map load as a dev-time safety net.
    """
    from bit_flippers.combat import ENEMY_TYPES
    from bit_flippers.maps import MAP_REGISTRY
    from bit_flippers.strings import get_npc_dialogue

    warnings: list[str] = []

    # --- Encounter table entries ---
    tmx_props = tiled_renderer.get_map_properties()
    if tmx_props.get("encounter_table"):
        encounter_keys = [e.strip() for e in tmx_props["encounter_table"].split(",") if e.strip()]
    else:
        encounter_keys = list(map_def.encounter_table)

    for key in encounter_keys:
        if key not in ENEMY_TYPES:
            msg = f"[{map_id}] Encounter table references unknown enemy: '{key}'"
            warnings.append(msg)
            logger.warning(msg)

    # --- Enemy NPCs ---
    tmx_enemies = tiled_renderer.get_enemies()
    enemy_defs = tmx_enemies if tmx_enemies else map_def.enemies
    for edef in enemy_defs:
        if edef.enemy_type_key not in ENEMY_TYPES:
            msg = f"[{map_id}] Enemy NPC references unknown type: '{edef.enemy_type_key}'"
            warnings.append(msg)
            logger.warning(msg)

    # --- NPC dialogue keys ---
    tmx_npcs = tiled_renderer.get_npcs()
    npc_defs = tmx_npcs if tmx_npcs else map_def.npcs
    for npc_def in npc_defs:
        if npc_def.dialogue_key:
            lines = get_npc_dialogue(npc_def.dialogue_key)
            if not lines:
                msg = f"[{map_id}] NPC '{npc_def.name}' dialogue_key '{npc_def.dialogue_key}' not found in strings.json"
                warnings.append(msg)
                logger.warning(msg)

    # --- Door targets ---
    tmx_doors = tiled_renderer.get_doors()
    door_defs = tmx_doors if tmx_doors else map_def.doors
    for door in door_defs:
        if door.target_map_id not in MAP_REGISTRY:
            msg = f"[{map_id}] Door at ({door.x},{door.y}) targets unknown map: '{door.target_map_id}'"
            warnings.append(msg)
            logger.warning(msg)

    # --- Event text_key references ---
    tmx_events = tiled_renderer.get_events()
    for ev in tmx_events:
        text_key = ev.properties.get("text_key")
        if text_key:
            lines = get_npc_dialogue(text_key)
            if not lines:
                msg = f"[{map_id}] Event at ({ev.x},{ev.y}) text_key '{text_key}' not found in strings.json"
                warnings.append(msg)
                logger.warning(msg)

    return warnings
