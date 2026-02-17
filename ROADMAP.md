# Bit Flippers — Roadmap

A SNES-inspired turn-based RPG set in a post-apocalyptic world.
Milestones 1–18 completed — see [COMPLETED_ROADMAP.md](COMPLETED_ROADMAP.md) for history.

## Milestone 19: Outdoor Tile Palette + Overworld Redesign
**Status: Not started**
- New tile types: GRASS (walkable, outdoor floor), PATH (walkable, roads/trails), WATER (impassable, natural boundary), TREE (impassable, forest/cover)
- Procedural tile sprites for each new type with color fallbacks (extend `tilemap.py` and asset generator)
- Redesign overworld map from dungeon-like rooms/corridors to an outdoor landscape:
  - Central settlement hub with shops and quest NPCs clustered together
  - Dirt paths radiating outward to dungeon entrances
  - Natural boundaries: water edges, tree lines, rocky walls
  - Open grassy areas with scattered scrap and random encounters
  - Dungeon entrances as distinct landmarks (cave mouth, factory gate, etc.)
- Larger overworld map (60x40 or bigger) to give space for exploration
- Overworld music track distinct from dungeon music
- Existing dungeon interiors (Scrap Cave, Factory, Reactor Core) keep their current indoor/underground aesthetic unchanged

## Milestone 20: Dungeon Visual Identity + Music
**Status: Not started**
- Per-dungeon music tracks to differentiate areas (overworld, cave, factory, reactor)
- Environmental flavor tiles per dungeon theme (pipes, rubble, grates, glowing vents)
- Dungeon entry/exit feels like a transition (outdoor → indoor)
- Mini-map or area name banner on dungeon entry
- Ensure existing dungeons feel distinct from the new outdoor overworld

## Milestone 21: New Dungeons
**Status: Not started**
- 2–3 new dungeon areas with unique visual themes and encounter tables:
  - Comm Tower: vertical layout, electrical hazards, signal-themed enemies
  - Slag Pits: industrial waste, fire-themed, connects to Scrap Factory path
  - Data Vault: high-tech final dungeon, endgame difficulty, behind Reactor Core
- New boss for each dungeon gating progression
- New regular enemies per area (2–3 each)
- Difficulty curve: Overworld → Factory → Cave → Comm Tower → Slag Pits → Reactor Core → Data Vault

## Milestone 22: Quest Expansion
**Status: Not started**
- New quests tied to each new dungeon area (discovery, boss defeat, item retrieval)
- Multi-part quest chains that span multiple areas
- Optional side quests with unique rewards (rare equipment, skill unlocks)
- NPC quest-givers in the overworld settlement and within dungeons
- Expanded quest log with area/category filtering

## Milestone 23: Plot + Narrative Framework
**Status: Not started**
- Main story arc: what happened to this world, what is the player's goal
- Story beats tied to boss defeats and dungeon completions
- Cutscene/event system for key story moments (dialogue sequences with scripted camera/NPC movement)
- NPC dialogue that evolves as the story progresses
- Final boss encounter and ending sequence
- Lore items/terminals scattered in dungeons for optional world-building
