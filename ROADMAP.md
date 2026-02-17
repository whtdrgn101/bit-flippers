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
**Status: Done**
- SkillDef data model with name, SP cost, effect type, base value, stat scaling, tree position, prerequisites, unlock cost
- 8 skills in a 3-tier tree with two branches converging:
  - Tier 0: Shrapnel Blast (damage), Jury-Rig Shield (buff defense)
  - Tier 1: Voltage Surge (damage), Scrap Leech (drain), Overclock (debuff attack)
  - Tier 2: Magnet Storm (damage), Patchwork Heal (heal), EMP Pulse (debuff ATK+DEF)
- Skill tree UI (`K` key) with node visualization, cursor navigation, and unlock mechanics
- "Skill" option added to combat menu (Attack, Defend, Skill, Item, Flee)
- Skills consume SP; +1 SP regen per combat turn
- Skill points earned on level-up (1/level + bonus every 5th level)
- Intelligence and strength stats scale skill effects via calc_skill_effect
- Enemy debuff system: ATK/DEF reduction for 3 turns with auto-restore
- Drain skill type: damages enemy and heals player for same amount
- Skills data persisted in player_stats.json alongside stats
- Backward-compatible save/load (graceful defaults for missing skills data)

## Polish: Death Screen + Pause Menu
**Status: Done**
- Death screen overlay on defeat: "YOU WERE DEFEATED" with penalty summary
- Death penalties: lose half scrap, respawn at half max HP, SP fully restored
- Auto-save after death penalties applied
- Pause menu (ESC key) with Resume, Inventory, Character, Skill Tree, and Quit Game options
- Quit Game option for clean exit from keyboard

## Milestone 12: Save Game System + Title Screen + Externalized Strings
**Status: Done**
- Full game state save/load (`savegame.json`): stats, skills, inventory, position, map persistence
- Title screen with New Game / Continue / About menu
- About screen with credits loaded from `strings.json`
- All NPC dialogue externalized to `assets/strings.json` (NPCDef uses `dialogue_key`)
- String loader module (`strings.py`) with caching and dot-path accessor
- "Save Game" option in pause menu with confirmation message
- "Continue" grayed out when no save file exists
- Auto-save after combat victory and death penalties
- Legacy `player_stats.json` cleaned up on New Game
- Scrap tile pickup now awards Scrap currency in addition to inventory item

## Milestone 13: Shop System
**Status: Done**
- Buy/sell interface at the Shopkeeper NPC in Tinker's Shop
- Item prices: Scrap Metal (2), Repair Kit (8), Iron Plating (10), Voltage Spike (12)
- Sell price = buy price // 2 (standard RPG convention)
- Two-tab shop UI (Buy/Sell) with cursor navigation and scroll support
- Buy confirmation prompt; instant sell (one unit per press)
- Scrap balance displayed in shop; auto-save on close
- Shopkeeper dialogue triggers shop on close via on_close callback

## Milestone 14: Equipment System
**Status: Done**
- Equipment slots: Weapon, Armor, Accessory
- 12 equipment items across 4 tiers (Bronze, Silver, Titanium, Palladium) with sci-fi names
- Weapons boost ATK (+2/+4/+7/+11), Armor boosts DEF (+2/+4/+7/+11), Accessories give varied bonuses (HP, DEX, SP, INT)
- Equip/unequip from inventory via ENTER key, [E] marker on equipped items
- Equipment stat bonuses reflected in combat formulas (attack, defense, hit chance, skill damage, max HP/SP)
- Equipment section on character screen showing equipped items and stat bonuses
- Two new shop NPCs: Weaponsmith ("Volt's Forge") and Armorsmith ("Iron Shell Outfitters")
- New interior maps with warm orange / cool blue floor tints
- Branding icons (sword/shield) on overworld wall tiles adjacent to shop doors
- Equipment persisted in savegame.json (backward-compatible, defaults to empty slots)
- Selling equipped items auto-unequips them

## Milestone 15: More Enemy Types + Boss Encounters
**Status: Done**
- 4 new regular enemies: Wire Spider, Slag Beetle, Plasma Hound, Core Leech
- 2 boss enemies: Forge Guardian (overworld), Meltdown Warden (scrap cave)
- Bosses placed on tiles guarding doors — block access until defeated
- Per-map encounter table variety with new enemies
- Difficulty progression: Overworld → Factory → Scrap Cave → Reactor Core

## Milestone 16: Status Effects in Combat
**Status: Done**
- 4 status effects: Poison (2 HP/turn, 3t), Stun (skip turn, 1t), Burn (ATK-2 + 1 HP/turn, 3t), Despondent (DEX-4, 3t, player only)
- 6 enemy special abilities that inflict status effects (replace normal attack, deal half damage)
- Colored status indicators with turn counts next to HP bars
- Antidote Kit consumable (price 10) clears all player status effects
- Re-applying same effect refreshes duration (no stacking)
- DoT damage can kill combatants, triggering victory/defeat
- Burn ATK reduction tracked separately from skill debuffs

## Milestone 17: Quest System + Robot NPC Sprites
**Status: Done**
- Quest data model: QuestObjective, QuestDef, PlayerQuests with state machine (available -> active -> complete -> done)
- 5 quests: Spare Parts (fetch), Pest Control (kill), Deep Reconnaissance (multi-stage), Circuit Restoration (fetch, prerequisite chain), Factory Sweep (kill)
- Quest-giving NPCs with dialogue branching per quest state (offer/active/complete/done)
- Quest log UI (`Q` key or pause menu) with objective progress, rewards, and description
- Quest completion rewards: Scrap, XP, items, equipment, and skill unlocks
- Robot procedural sprites for Weaponsmith, Armorsmith, and Sparks NPCs (boxy industrial look)
- Kill tracking after combat victory, fetch checking on NPC interaction, visit tracking on map transition
- HUD indicator when quests are completable
- Quest progress persisted in savegame.json (backward-compatible)

## Milestone 18: More Maps + Areas
**Status: Done**
- Scrap Factory (25x18): grey-blue floor, Wire Spider / Slag Beetle / Plasma Hound encounters, Engineer NPC
- Reactor Core (18x14): dark purple floor, Core Leech / Volt Wraith / Plasma Hound encounters (hardest area)
- Progression path: Overworld → Scrap Factory (via Forge Guardian), Scrap Cave → Reactor Core (via Meltdown Warden)
- Per-area tile color overrides and tuned encounter chances
- Boss-guarded doors connect areas with progressive difficulty
