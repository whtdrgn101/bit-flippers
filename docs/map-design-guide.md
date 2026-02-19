# Bit Flippers - Map & Content Design Guide

This guide walks through everything you need to create maps, place NPCs, enemies, doors, scrap pickups, and dialog using Tiled and the Python codebase.

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Creating a New Map in Tiled](#creating-a-new-map-in-tiled)
3. [Tile Layers & Draw Order](#tile-layers--draw-order)
4. [Collision / Walkability](#collision--walkability)
5. [Adding a Spawn Point](#adding-a-spawn-point)
6. [Adding Doors (Map Transitions)](#adding-doors-map-transitions)
7. [Adding NPCs](#adding-npcs)
8. [Adding Dialog](#adding-dialog)
9. [Adding Enemies (Scripted Combat)](#adding-enemies-scripted-combat)
10. [Adding Random Encounters](#adding-random-encounters)
11. [Adding Scrap Pickups](#adding-scrap-pickups)
12. [Adding Icon Markers](#adding-icon-markers)
13. [Map-Level Properties](#map-level-properties)
14. [Registering the Map in Python](#registering-the-map-in-python)
15. [Wiring Up Doors (Both Sides)](#wiring-up-doors-both-sides)
16. [Adding New Enemy Types](#adding-new-enemy-types)
17. [Shop NPCs](#shop-npcs)
18. [Sprites & Art](#sprites--art)
19. [Testing Your Map](#testing-your-map)
20. [Full Worked Example](#full-worked-example)

---

## Quick Reference

### Tiled Object Types

| Type | Required Properties | Optional Properties |
|------|-------------------|-------------------|
| `Spawn` | — | `facing` (default: `"down"`) |
| `Door` | `target_map_id`, `target_spawn_x`, `target_spawn_y` | `target_facing` (default: `"down"`) |
| `NPC` | `dialogue_key` | `sprite_key`, `sprite_style`, `facing`, `color_r/g/b` |
| `Enemy` | `enemy_type_key` | `color_r/g/b` |
| `Scrap` | — | — |
| `IconMarker` | `icon_type` | `color_r/g/b` |

### Layer Naming Rules

| Renders... | Layer names |
|-----------|-------------|
| Below sprites | Anything NOT in the list below (e.g. `ground`, `detail`, `walls`) |
| Above sprites | `fringe`, `above`, `overlay` |
| Collision zones | `collision` or `collisions` (object layer with rectangles) |
| Game objects | Any object layer — objects are identified by their `type`, not the layer name |

### Enemy Type Keys

`scrap_rat`, `rust_golem`, `volt_wraith`, `wire_spider`, `slag_beetle`, `plasma_hound`, `core_leech`, `forge_guardian`, `meltdown_warden`

---

## Creating a New Map in Tiled

### 1. Open the Tiled Project

Always open maps through the project file so custom types are available:

```
File > Open File > assets/maps/bit-flippers.tiled-project
```

This loads the 6 custom object types (NPC, Enemy, Door, Scrap, Spawn, IconMarker) into Tiled so they appear in the Type dropdown when creating objects.

### 2. Create the Map

```
File > New > New Map
```

Settings:
- **Orientation:** Orthogonal
- **Tile layer format:** CSV (or any — pytmx handles all formats)
- **Tile render order:** Right Down
- **Map size:** Fixed, set your desired width/height in tiles
- **Tile size:** 32 x 32 px

Save as `assets/maps/your_map_name.tmx`.

### 3. Add the Tileset

```
Map > Add External Tileset > assets/maps/tilesets/basechip.tsx
```

This is the primary tileset (1064 tiles, 32x32). It already has `walkable: false` set on wall/furniture/water tiles.

You can also add `grass_autotile.tsx` or `water_static.tsx` if your map needs those.

---

## Tile Layers & Draw Order

Create your tile layers in this order (bottom to top):

| Layer Name | Purpose | Example Content |
|-----------|---------|----------------|
| `ground` | Base floor/terrain | Grass, dirt, floor tiles |
| `detail` | Decorations on top of ground | Furniture, rugs, flowers, fences |
| `above` | Canopy rendered OVER sprites | Tree tops, roof overhangs, archways |

**The naming matters.** Layers named `fringe`, `above`, or `overlay` render on top of the player sprite. Everything else renders below. This is how you get the player walking "behind" a tree canopy or under an arch.

You can use as many layers as you want. A dungeon might look like:

```
ground      → stone floor
walls       → wall tiles (rendered below sprites, but marked non-walkable)
detail      → torches, cracks, debris
above       → ceiling edges that overlap the player
```

**Tip:** Keep layers visible in Tiled to preview the final look. Toggle visibility to work on individual layers.

---

## Collision / Walkability

There are two ways to mark tiles as non-walkable. You can use both in the same map.

### Method 1: Tile Properties (Automatic)

Many tiles in `basechip.tsx` already have `walkable` set to `false`. When you paint with those tiles on ANY layer, the engine automatically blocks that cell. You don't need to do anything extra.

To check: select a tile in the tileset panel and look at its Custom Properties. If it says `walkable: false`, it will block movement.

### Method 2: Collision Object Layer (Manual Rectangles)

For cases where you need custom collision zones (e.g., an invisible wall, or a walkable-looking tile that should block):

1. Create a new **Object Layer** named `collision` (or `collisions`)
2. Use the **Rectangle tool** to draw collision boxes
3. The engine converts these pixel rectangles to tile coordinates and marks them non-walkable

**Tip:** The collision layer can be hidden in-game — it's only used for data. You might want to give it a red color in Tiled for visibility while editing.

---

## Adding a Spawn Point

The spawn point is where the player appears when entering this map (unless a door specifies different coordinates).

1. Create an **Object Layer** (name it anything — `entities` is conventional)
2. Use the **Point** or **Rectangle** tool to place an object
3. Set the object's **Type** to `Spawn`
4. Set the **position** in pixels (the engine divides by 32 to get tile coords)
5. Optionally set the `facing` property: `"up"`, `"down"`, `"left"`, or `"right"`

**Position math:** Tile (5, 7) = pixel position (160, 224). Multiply tile coords by 32.

Each map should have exactly one Spawn object. If a door transition provides explicit coordinates, those override the Spawn point.

---

## Adding Doors (Map Transitions)

Doors are tiles the player steps onto to change maps. They trigger instantly on contact — no button press needed.

### In Tiled

1. On your object layer, place a rectangle or point object on the door tile
2. Set **Type** to `Door`
3. Set these custom properties:

| Property | Type | Description |
|----------|------|-------------|
| `target_map_id` | string | The `map_id` of the destination map (e.g. `"overworld"`) |
| `target_spawn_x` | int | Tile X to place the player in the target map |
| `target_spawn_y` | int | Tile Y to place the player in the target map |
| `target_facing` | string | Direction the player faces after transition (default: `"down"`) |

### Example: Shop Exit Door

A shop door at tile (5, 8) that returns to the overworld at tile (31, 28) facing down:

- Position: x=160, y=256 (pixel coords)
- Type: `Door`
- `target_map_id`: `"overworld"`
- `target_spawn_x`: `31`
- `target_spawn_y`: `28`
- `target_facing`: `"down"`

### Important: Doors Must Be Paired

Every door needs a matching door on the other side! If your shop exit goes to overworld (31, 28), the overworld map needs a door at (31, 28) that goes back to your shop. See [Wiring Up Doors (Both Sides)](#wiring-up-doors-both-sides).

---

## Adding NPCs

### In Tiled

1. Place an object on your object layer
2. Set the **Name** to the NPC's display name (e.g. `"Old Tinker"`) — this shows in the dialog box
3. Set **Type** to `NPC`
4. Set custom properties:

| Property | Type | Required? | Description |
|----------|------|-----------|-------------|
| `dialogue_key` | string | Yes | Key into `assets/strings.json` (see [Adding Dialog](#adding-dialog)) |
| `sprite_key` | string | No | Sprite to use (see [Sprites & Art](#sprites--art)) |
| `sprite_style` | string | No | `"humanoid"` (default) or `"robot"` — only matters for placeholder sprites |
| `facing` | string | No | `"down"` (default), `"up"`, `"left"`, `"right"` |
| `color_r` | int | No | Red component (0-255) for placeholder sprite |
| `color_g` | int | No | Green component |
| `color_b` | int | No | Blue component |

### Sprite Key Formats

- **Pipoya character:** `"pipoya-characters/Male/Male 03-2"` → loads `assets/sprites/pipoya-characters/Male/Male 03-2.png`
- **Custom sprite:** `"old_tinker"` → loads `assets/sprites/npc_old_tinker.png`
- **No sprite_key:** Falls back to a colored placeholder (humanoid or robot based on `sprite_style`)

### NPC Collision

NPCs automatically block movement. The player can't walk through them — they need to face the NPC and press SPACE to interact.

---

## Adding Dialog

Dialog is stored in `assets/strings.json` and referenced by key.

### 1. Add Lines to strings.json

Open `assets/strings.json` and add your dialog under the `"npcs"` section:

```json
{
  "npcs": {
    "my_new_npc": [
      "Hey there, traveler!",
      "I've been waiting for someone like you.",
      "Take this advice: never trust a Rust Golem."
    ],
    ...
  }
}
```

Each string in the array is one "page" of dialog. The player presses SPACE to advance through pages.

### 2. Reference the Key in Tiled

Set the NPC's `dialogue_key` property to `"my_new_npc"` (matching the key you added to strings.json).

### Dialog Features

- **Typewriter effect:** Text reveals at 30 characters/second
- **SPACE/ENTER:** If text is still revealing, shows it all instantly. If fully shown, advances to next page.
- **Auto-wrapping:** Long lines wrap automatically to fit the dialog panel
- **NPC name:** Displayed in gold at the top of the dialog box (comes from the object's Name in Tiled)

### Quest-Aware Dialog

If an NPC is associated with a quest, the engine automatically swaps their dialog based on quest state. You don't set this in Tiled — it's handled in the quest system. The four dialog keys used are:

- `quest_{quest_id}_offer` — when quest is available
- `quest_{quest_id}_active` — while quest is in progress
- `quest_{quest_id}_complete` — when player has met the objective
- `quest_{quest_id}_done` — after quest is turned in

Add all four to `strings.json` if your NPC gives a quest.

---

## Adding Enemies (Scripted Combat)

Scripted enemies are visible on the map. Walking up to them and pressing SPACE starts combat. Once defeated, they disappear permanently (saved to persistence).

### In Tiled

1. Place an object on your object layer
2. Set **Type** to `Enemy`
3. Set custom properties:

| Property | Type | Required? | Description |
|----------|------|-----------|-------------|
| `enemy_type_key` | string | Yes | Key from the enemy registry (see table below) |
| `color_r` | int | No | Red component for placeholder sprite |
| `color_g` | int | No | Green component |
| `color_b` | int | No | Blue component |

### Available Enemy Types

| Key | Name | HP | ATK | DEF | XP | Scrap |
|-----|------|-----|-----|-----|-----|-------|
| `scrap_rat` | Scrap Rat | 12 | 4 | 1 | 8 | 5 |
| `wire_spider` | Wire Spider | 10 | 6 | 0 | 10 | 6 |
| `slag_beetle` | Slag Beetle | 18 | 5 | 6 | 14 | 10 |
| `rust_golem` | Rust Golem | 25 | 7 | 4 | 18 | 12 |
| `plasma_hound` | Plasma Hound | 22 | 9 | 3 | 20 | 14 |
| `volt_wraith` | Volt Wraith | 20 | 10 | 2 | 22 | 15 |
| `core_leech` | Core Leech | 28 | 12 | 3 | 28 | 20 |
| `forge_guardian` | Forge Guardian | 50 | 12 | 6 | 60 | 40 |
| `meltdown_warden` | Meltdown Warden | 60 | 14 | 5 | 80 | 55 |

Place weaker enemies near the starting areas and stronger ones deeper in dungeons.

---

## Adding Random Encounters

Random encounters trigger while walking, with no visible enemy on the map. They're configured as **map-level properties** — not per-object.

### In Tiled

Click on an empty area of the map (deselect everything), then open **Map > Map Properties** and add:

| Property | Type | Value Example | Description |
|----------|------|---------------|-------------|
| `encounter_table` | string | `"Scrap Rat,Wire Spider"` | Comma-separated **display names** (not keys!) |
| `encounter_chance` | float | `0.05` | Probability per step (0.05 = 5%) |

The engine picks a random enemy from the table each time an encounter triggers. There's a minimum of 10 steps between encounters to prevent frustration.

**Tip:** Only add random encounters to exploration/dungeon maps. Shops and safe areas should have `encounter_chance: 0` (or just don't set it).

---

## Adding Scrap Pickups

Scrap is the game's currency. Pickups appear as glowing items on the map and disappear when collected (persisted).

### In Tiled

1. Place an object where you want the scrap
2. Set **Type** to `Scrap`
3. No custom properties needed — just position

The engine handles the visual and the 25% chance of a bonus item drop.

---

## Adding Icon Markers

Icon markers are decorative symbols drawn on walls (e.g., a sword icon next to a weapon shop door).

### In Tiled

1. Place an object at the tile where the icon should appear
2. Set **Type** to `IconMarker`
3. Set custom properties:

| Property | Type | Description |
|----------|------|-------------|
| `icon_type` | string | `"sword"` or `"shield"` |
| `color_r/g/b` | int | Icon color (default: white) |

---

## Map-Level Properties

These are set on the **map itself** (Map > Map Properties in Tiled), not on any object:

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `display_name` | string | from MapDef | Name shown in the HUD (e.g. "Scrap Cave") |
| `music_track` | string | `"overworld"` | Background music key (`"overworld"` or `"combat"`) |
| `encounter_table` | string | none | Comma-separated enemy names for random battles |
| `encounter_chance` | float | `0.0` | Per-step encounter probability |

---

## Registering the Map in Python

Even though entities can live entirely in the TMX file, you still need a `MapDef` entry so the engine knows your map exists.

### Edit `src/bit_flippers/maps.py`

Add your map to the `MAP_REGISTRY`:

```python
"my_dungeon": MapDef(
    map_id="my_dungeon",
    display_name="My Dungeon",       # fallback if not set in TMX
    player_start_x=5,                # fallback spawn if no Spawn object in TMX
    player_start_y=10,
    tmx_file="my_dungeon.tmx",       # must match filename in assets/maps/
),
```

That's the minimal registration. If all your NPCs, enemies, doors, etc. are defined in the TMX file, you don't need to list them here — the engine loads them from the TMX automatically.

### What the Python Fallbacks Are For

The `MapDef` fields (`npcs`, `enemies`, `doors`, `encounter_table`, etc.) are **fallbacks**. The engine checks the TMX first. If the TMX has objects of that type, those are used. If not, it falls back to the Python definition. This means:

- **New maps:** Put everything in the TMX. Keep the Python entry minimal.
- **Existing maps:** Some still have entities defined in Python (like `overworld`). These will be migrated to TMX over time.

---

## Wiring Up Doors (Both Sides)

Every door transition needs an entry point AND an exit point. Here's the step-by-step for connecting two maps:

### Example: Connecting `overworld` to `my_dungeon`

**Step 1: In `my_dungeon.tmx`**

Add a Spawn object at the dungeon entrance (e.g., tile 5, 10):
- Type: `Spawn`
- Position: x=160, y=320
- `facing`: `"up"`

Add a Door at the same tile (or a nearby exit tile) to go back:
- Type: `Door`
- Position: x=160, y=320 (tile 5, 10)
- `target_map_id`: `"overworld"`
- `target_spawn_x`: `25` (the tile BELOW the overworld door so the player doesn't re-trigger it)
- `target_spawn_y`: `16`
- `target_facing`: `"down"`

**Step 2: In `overworld.tmx`**

Add a Door object at the overworld entrance (e.g., tile 25, 15):
- Type: `Door`
- Position: x=800, y=480 (tile 25, 15)
- `target_map_id`: `"my_dungeon"`
- `target_spawn_x`: `5`
- `target_spawn_y`: `10`
- `target_facing`: `"up"`

**Key detail:** Doors trigger instantly when the player steps on them. To prevent an infinite loop, make sure the target spawn position is NOT on top of another door. Typically:
- The overworld door sends you to the dungeon's Spawn point (which is near the exit door but not ON it)
- The dungeon exit door sends you to a tile adjacent to the overworld entrance

---

## Adding New Enemy Types

To create a completely new enemy (not just placing existing ones):

### Edit `src/bit_flippers/combat.py`

Add to the `ENEMY_TYPES` dict:

```python
"my_new_enemy": EnemyData(
    name="Circuit Crawler",
    hp=15,
    attack=7,
    defense=2,
    color=(100, 255, 100),       # placeholder sprite color
    xp_reward=12,
    money_reward=8,
    dexterity=6,
    ability=None,                # or see below for status effects
    battle_sprite_key=None,      # or path to sprite
),
```

### Adding a Special Ability

Enemies can inflict status effects. Set the `ability` field:

```python
ability={
    "name": "Toxic Spray",           # displayed in combat log
    "status": "Poison",              # "Poison", "Stun", "Burn", or "Despondent"
    "chance": 0.25,                  # 25% chance to apply
}
```

| Status | Duration | Effect |
|--------|----------|--------|
| Poison | 3 turns | 2 damage/turn |
| Stun | 1 turn | Skip turn |
| Burn | 3 turns | 1 damage/turn, ATK -2 |
| Despondent | 3 turns | DEX -4 |

### Adding a Battle Sprite

Place a 64x32 PNG (2 frames, 32x32 each) at `assets/sprites/enemy_my_new_enemy.png`, then set:

```python
battle_sprite_key="my_new_enemy",
```

Or use a Pipoya monster sprite:

```python
battle_sprite_key="pipoya-monsters/SomeMonster",
```

### Use It in Tiled

Now you can place `Enemy` objects with `enemy_type_key: "my_new_enemy"` and reference `"Circuit Crawler"` in encounter tables.

---

## Shop NPCs

Certain NPC names automatically open a shop after their dialog closes:

| NPC Name (in Tiled) | Shop Type |
|---------------------|-----------|
| `Shopkeeper` | General shop (default stock) |
| `Weaponsmith` | Weapon shop (`WEAPONSMITH_STOCK`) |
| `Armorsmith` | Armor shop (`ARMORSMITH_STOCK`) |

Just set the object's **Name** to one of these exact strings and the shop behavior hooks in automatically. The `dialogue_key` still controls what they say before the shop opens.

---

## Sprites & Art

### Using Pipoya Character Sprites

The `assets/sprites/pipoya-characters/` folder contains character sprite sheets. Each is a 96x128 PNG with a 3x4 grid of 32x32 frames.

To use one, set `sprite_key` on an NPC to the path relative to `assets/sprites/`:

```
pipoya-characters/Male/Male 01-1
pipoya-characters/Female/Female 06-3
pipoya-characters/Animal/Cat 01-1
```

Browse the folders to find one you like. The format is:
- Row 0: facing down
- Row 1: facing left
- Row 2: facing right
- Row 3: facing up
- Columns: walk-left, idle, walk-right

### Using Custom Sprites

For NPCs, save a 32x128 PNG (1 column x 4 rows, one frame per direction: down, left, right, up) as:

```
assets/sprites/npc_yourname.png
```

Then set `sprite_key: "yourname"` on the NPC.

### Placeholder Sprites

If you don't set a `sprite_key`, the engine generates a colored placeholder:
- **Humanoid** (`sprite_style: "humanoid"`): colored rectangle with a hat
- **Robot** (`sprite_style: "robot"`): boxy shape with antenna and glowing eye

Use `color_r/g/b` to customize the color. This is great for prototyping — get your map working first, add real sprites later.

---

## Testing Your Map

### Run the Game

```bash
uv run bit-flippers
```

Or:

```bash
uv run python -m bit_flippers.main
```

### Quick Test Checklist

- [ ] Map loads without errors
- [ ] Player spawns at the correct position
- [ ] Walking into walls is blocked (collision works)
- [ ] `above` layer renders over the player sprite
- [ ] All doors transition to the correct maps and back
- [ ] NPCs are in the right positions and facing the right direction
- [ ] NPC dialog displays correctly (all pages)
- [ ] Enemies trigger combat when interacted with
- [ ] Defeated enemies don't reappear after re-entering the map
- [ ] Random encounters trigger (if configured) at a reasonable rate
- [ ] Scrap pickups work and don't reappear after collection
- [ ] Music plays (if you set `music_track`)
- [ ] HUD shows the correct map name

### Common Issues

| Problem | Likely Cause |
|---------|-------------|
| Map doesn't load | TMX filename doesn't match `tmx_file` in `MapDef` |
| Player spawns in a wall | Spawn point is on a non-walkable tile |
| NPCs don't appear | Object `type` isn't exactly `NPC` (case-sensitive) |
| Dialog is empty | `dialogue_key` doesn't match any key in `strings.json` |
| Door doesn't work | Target map isn't registered in `MAP_REGISTRY` |
| Player stuck in door loop | Target spawn is on top of another door tile |
| Tiles render above player unexpectedly | Layer name isn't in the "above" set — rename it |
| Enemy doesn't appear | `enemy_type_key` doesn't match any key in `ENEMY_TYPES` |

---

## Full Worked Example

Let's create a small dungeon called "Rusty Basement" with an NPC, two enemies, some scrap, and a door back to the overworld.

### 1. Create the TMX

In Tiled (with the project open), create a 15x12 map at 32x32 tiles. Save as `assets/maps/rusty_basement.tmx`.

### 2. Paint the Tile Layers

- `ground` layer: stone floor tiles
- `walls` layer: wall tiles around the edges (these auto-block if they have `walkable: false`)
- `detail` layer: crates, barrels, broken machinery
- `above` layer: ceiling overhang tiles along the top wall

### 3. Set Map Properties

In Map > Map Properties:
- `display_name`: `"Rusty Basement"`
- `music_track`: `"overworld"`
- `encounter_table`: `"Scrap Rat,Wire Spider"`
- `encounter_chance`: `0.08`

### 4. Create the Object Layer

Add an object layer called `entities`.

### 5. Place Objects

**Spawn** at tile (7, 10):
- Type: `Spawn`, position: (224, 320), facing: `"up"`

**Exit Door** at tile (7, 11):
- Type: `Door`, position: (224, 352)
- `target_map_id`: `"overworld"`
- `target_spawn_x`: `20`
- `target_spawn_y`: `26`
- `target_facing`: `"down"`

**NPC** "Scavenger" at tile (3, 4):
- Type: `NPC`, name: `"Scavenger"`, position: (96, 128)
- `dialogue_key`: `"scavenger_basement"`
- `sprite_style`: `"humanoid"`
- `facing`: `"right"`
- `color_r`: 120, `color_g`: 200, `color_b`: 80

**Enemy** at tile (10, 3):
- Type: `Enemy`, position: (320, 96)
- `enemy_type_key`: `"rust_golem"`

**Enemy** at tile (12, 7):
- Type: `Enemy`, position: (384, 224)
- `enemy_type_key`: `"slag_beetle"`

**Scrap** pickups at tiles (5, 6) and (11, 5):
- Type: `Scrap`, positions: (160, 192) and (352, 160)

### 6. Add Dialog

In `assets/strings.json`, add under `"npcs"`:

```json
"scavenger_basement": [
    "Watch your step down here.",
    "The Rust Golems are territorial.",
    "I found some good scrap deeper in, but those beetles are nasty."
]
```

### 7. Register the Map

In `src/bit_flippers/maps.py`, add to `MAP_REGISTRY`:

```python
"rusty_basement": MapDef(
    map_id="rusty_basement",
    display_name="Rusty Basement",
    player_start_x=7,
    player_start_y=10,
    tmx_file="rusty_basement.tmx",
),
```

### 8. Add the Overworld Door

In `overworld.tmx`, add a Door object at tile (20, 25):
- Type: `Door`, position: (640, 800)
- `target_map_id`: `"rusty_basement"`
- `target_spawn_x`: `7`
- `target_spawn_y`: `10`
- `target_facing`: `"up"`

### 9. Test

```bash
uv run bit-flippers
```

Walk to tile (20, 25) on the overworld. You should transition into Rusty Basement, see the Scavenger NPC, fight the two enemies, collect scrap, and exit back to the overworld.
