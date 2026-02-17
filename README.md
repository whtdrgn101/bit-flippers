# Bit Flippers

A SNES-inspired turn-based RPG set in a post-apocalyptic scrapyard world, built with Python and Pygame.

## Running the Game

```bash
uv run python -m bit_flippers.main
```

## Controls

| Key | Action |
|-----|--------|
| Arrow keys | Move / navigate menus |
| SPACE / ENTER | Interact / confirm |
| ESC | Pause menu |
| C | Character stats screen |
| K | Skill tree screen |

## Features

- Tile-based overworld with scrolling camera and smooth movement
- Animated pixel art sprites with directional walk/idle animations
- NPC dialogue system with typewriter text effect
- Turn-based combat with Attack, Defend, Skill, Item, and Flee options
- Inventory system with scrap pickup and consumable items
- Multiple map areas with door transitions and per-map persistence
- XP, money (Scrap), and level progression
- 7 allocatable character stats (HP, SP, STR, DEX, RES, CON, INT)
- Skill tree with 8 skills across 3 tiers and two branches
- Death screen with respawn penalties (lose half scrap, respawn at half HP)
- Pause menu with access to all sub-screens and quit option
- JSON save/load for player stats and skill progress
