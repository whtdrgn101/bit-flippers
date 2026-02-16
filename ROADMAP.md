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
**Status: Not started**
- Pixel art sprite sheets replacing procedural sprites
- Tile set artwork
- Background music, sound effects

## Milestone 8: Map Transitions + Multiple Areas
**Status: Not started**
- Door/portal tiles loading different maps
- Interior maps (buildings, caves)
- State persistence (collected items, defeated NPCs)
