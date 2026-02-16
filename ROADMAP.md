# Bit Flippers — Roadmap

A SNES-inspired turn-based RPG set in a post-apocalyptic world.

## Milestone 1: Foundation
**Status: Done**
- Single-screen 20x15 tile map
- Colored-rectangle player with arrow-key movement
- Wall collision, tile types (dirt, wall, scrap)
- Game loop with state system

## Milestone 2: Scrolling Camera + Larger Map
**Status: Done**
- Camera class that follows the player, clamped to map edges
- TileMap class with viewport culling
- 40x30 map with rooms, corridors, open areas, scattered scrap

## Milestone 3: Sprite System
**Status: Done**
- AnimatedSprite and SpriteSheet classes
- Procedurally generated player sprite (4 directions x 3 frames)
- Smooth tile-to-tile lerp movement (~100ms slide)
- Walk/idle animation switching based on movement

## Milestone 4: NPC System + Dialogue
**Status: Done**
- NPC entities placed on the map with sprites and idle animations
- Interaction trigger (face NPC + press key)
- Dialogue box UI with typewriter text effect
- Advance/dismiss dialogue on keypress

## Milestone 5: Turn-Based Combat Foundation
**Status: Done**
- Encounter triggers (scripted or random)
- Battle state: separate screen with player party vs enemies
- Menu-driven actions: Attack, Defend, Item, Flee
- Simple damage formula, HP tracking
- Win/lose conditions, transition back to overworld

## Milestone 6: Inventory + Items
**Status: Done**
- Item data model (name, type, effect)
- Scrap tile pickup adds to inventory
- Inventory/pause menu
- Usable items in combat (healing, buffs)

## Milestone 7: Art Assets + Audio
**Status: Done**
- Pixel art sprite sheets replacing procedural sprites (with fallback)
- Tile set artwork (dirt noise, brick walls, metallic scrap)
- Asset generator tool (`tools/generate_assets.py`)
- AudioManager infrastructure (SFX + music wiring, no audio files yet)

## Milestone 8: Experience, Money + Level Progression
**Status: Done**
- Enemies award XP and money on defeat
- Steady linear XP curve (level N requires N × 20 XP)
- Level up resets HP to full and increases max HP by 2% (min +1)
- Money ("Scrap") tracked on overworld state, displayed in HUD
- HUD displays level, HP bar, XP bar (blue), and money
- Victory screen shows "+X XP" and "+Y Scrap" earned
- Multi-level-up support for large XP rewards
- Dynamic max HP used across combat and inventory

## Milestone 9: Map Transitions + Multiple Areas
**Status: Done**
- Door tile type (DOOR=3) with wooden door tileset sprite
- Map definition system (`maps.py`): DoorDef, NPCDef, EnemyNPCDef, MapDef dataclasses
- MAP_REGISTRY with three maps:
  - Overworld (40x30) — original map with two door exits
  - Tinker's Shop (12x10) — interior with shopkeeper NPC, no random encounters
  - Scrap Cave (20x15) — tight corridors, darker dirt, harder encounter table
- Per-map persistence (collected scrap and defeated enemies survive map transitions)
- Per-map encounter tables and encounter chances
- Tile color override support (cave uses darker dirt palette)
- Map name displayed in HUD when not on overworld

## Milestone 10: Character Stats + Character Screen
**Status: Done**
- PlayerStats dataclass with seven allocatable stats: Max HP, Max SP, Strength, Dexterity, Resilience, Constitution, Intelligence
- Stat point allocation on level-up: 2 points per level, 4 points every 10th level
- Character screen UI (`C` key) with cursor navigation and point allocation
- Stats influence combat:
  - Strength → attack damage (effective_attack = 3 + STR)
  - Dexterity → hit/miss chance (base 85%, ±3% per dex difference, clamped 30–99%)
  - Resilience → defense (effective_defense = RES)
  - Constitution → debuff duration reduction
  - Intelligence → skill damage multiplier
- Enemy dexterity values: Scrap Rat (4), Rust Golem (2), Volt Wraith (7)
- SP bar displayed in overworld HUD and combat
- Unspent points indicator in HUD with `[C]` hint
- JSON save/load for player stats (`player_stats.json`)
- Auto-save after combat rewards; save on character screen close
- Removed deprecated flat constants (PLAYER_ATTACK, PLAYER_DEFENSE, PLAYER_MAX_HP, LEVEL_UP_HP_BONUS)

## Milestone 11: Skills System + Skill Tree
**Status: Not started**
- Skill data model (name, SP cost, effect, stat scaling, tree position)
- Skill tree UI with unlock paths and prerequisites
- Initial skill set themed around scavenging and improvised combat:
  - Use scrap and environmental resources for special attacks
  - Craft-on-the-fly abilities (e.g., shrapnel blast, jury-rig shield)
- "Skills" option added to combat action menu (alongside Attack, Defend, Item, Flee)
- Skills consume SP; SP regeneration or restoration mechanics
- Skill unlock points earned on level-up or via story progression
- Intelligence stat scales skill damage/effectiveness

## Milestone 12: Save Game System
**Status: Not started**
- Full game state save and load (player stats, inventory, map progress, defeated NPCs)
- JSON format for all save data (easy to parse, edit, and tweak)
- Save/load accessible from pause menu
- Multiple save slots or auto-save support
- Graceful handling of missing or corrupted save files
