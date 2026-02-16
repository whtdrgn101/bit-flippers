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
**Status: Not started**
- Door/portal tiles loading different maps
- Interior maps (buildings, caves)
- State persistence (collected items, defeated NPCs)
