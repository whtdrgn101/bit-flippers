# Bit Flippers — Roadmap

A SNES-inspired RPG set in a world where nature reclaimed ancient technology.
Milestones 1–20a completed — see [COMPLETED_ROADMAP.md](COMPLETED_ROADMAP.md) for history.

## Milestone 20b: Engine Polish & Systems
**Status: Not started**

### Audio
- Add SFX files for the 4 referenced sound effects: `hit`, `victory`, `pickup`, `dialogue_advance`
- Add music tracks: `overworld`, `combat`, plus per-area tracks (cave, factory, reactor, shop)
- All 7 maps currently hardcoded to `music_track="overworld"` — differentiate them

### Visual Polish
- Screen transitions: fade/wipe effects for map changes and combat entry/exit (currently instant)
- Skill/combat VFX: unique visual effects per skill (currently all use same white hit flash)
- Custom pixel font to replace 37 instances of `SysFont(None)` (looks different per OS)
- Level-up fanfare animation and sound

### Balance & Gameplay
- Flee chance should factor in dexterity (currently flat 50%)
- Death penalty could scale with level or area (currently always 50% scrap, 50% HP)
- SP regen could factor in intelligence (currently flat +1/turn)
- Bonus item pool from scrap pickups is hardcoded inline — move to config

### Player Customization
- Player sprite selection at game start (currently hardcoded to `Male 01-1` in two places)

### UI
- Minimap or full map view accessible to the player
- Options/settings menu (volume, key bindings, display)
- Auto-save visual indicator (currently saves silently)

### Save System
- Platform-appropriate save location (currently writes to project root)
- Save version migration logic (currently no migration, old saves may break silently)
- Multiple save slots

## Milestone 21: Dungeon Visual Identity + Music
**Status: Not started**
- Per-dungeon music tracks to differentiate areas (overworld, cave, factory, reactor)
- Environmental flavor tiles per dungeon theme (pipes, rubble, grates, glowing vents)
- Dungeon entry/exit feels like a transition (outdoor → indoor)
- Mini-map or area name banner on dungeon entry
- Ensure existing dungeons feel distinct from the new outdoor overworld

## Milestone 22: New Dungeons
**Status: Not started**
- 2–3 new dungeon areas with unique visual themes and encounter tables:
  - Comm Tower: vertical layout, electrical hazards, signal-themed enemies
  - Slag Pits: industrial waste, fire-themed, connects to Scrap Factory path
  - Data Vault: high-tech final dungeon, endgame difficulty, behind Reactor Core
- New boss for each dungeon gating progression
- New regular enemies per area (2–3 each)
- Difficulty curve: Overworld → Factory → Cave → Comm Tower → Slag Pits → Reactor Core → Data Vault

## Milestone 23: Quest Expansion
**Status: Not started**
- New quests tied to each new dungeon area (discovery, boss defeat, item retrieval)
- Multi-part quest chains that span multiple areas
- Optional side quests with unique rewards (rare equipment, skill unlocks)
- NPC quest-givers in the overworld settlement and within dungeons
- Expanded quest log with area/category filtering

## Milestone 24: Plot + Narrative Framework
**Status: Not started**
- Main story arc: what happened to this world, what is the player's goal
- Story beats tied to boss defeats and dungeon completions
- Cutscene/event system for key story moments (dialogue sequences with scripted camera/NPC movement)
- NPC dialogue that evolves as the story progresses
- Final boss encounter and ending sequence
- Lore items/terminals scattered in dungeons for optional world-building
