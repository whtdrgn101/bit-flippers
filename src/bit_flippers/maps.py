"""Map definitions and registry for multi-map navigation."""
from dataclasses import dataclass, field

from bit_flippers.tilemap import DIRT, WALL, SCRAP, DOOR, GRASS, PATH, WATER, TREE, RUINS


@dataclass
class DoorDef:
    """A door on this map linking to another map."""
    x: int
    y: int
    target_map_id: str
    target_spawn_x: int
    target_spawn_y: int
    target_facing: str = "down"


@dataclass
class NPCDef:
    """Placement data for a friendly NPC."""
    tile_x: int
    tile_y: int
    name: str
    dialogue_key: str
    color: tuple[int, int, int]
    facing: str = "down"
    sprite_key: str | None = None
    sprite_style: str = "humanoid"  # "humanoid" or "robot"


@dataclass
class EnemyNPCDef:
    """Placement data for a scripted enemy encounter on the map."""
    tile_x: int
    tile_y: int
    enemy_type_key: str
    color: tuple[int, int, int]


@dataclass
class IconMarker:
    """A branding icon drawn on a wall tile."""
    x: int
    y: int
    icon_type: str  # "sword" or "shield"
    color: tuple[int, int, int] = (255, 255, 255)


@dataclass
class MapDef:
    """Full definition of a game map."""
    map_id: str
    display_name: str
    grid: list[list[int]]
    player_start_x: int
    player_start_y: int
    npcs: list[NPCDef] = field(default_factory=list)
    enemies: list[EnemyNPCDef] = field(default_factory=list)
    doors: list[DoorDef] = field(default_factory=list)
    encounter_table: list[str] = field(default_factory=list)
    encounter_chance: float = 0.0
    music_track: str = "overworld"
    tile_colors_override: dict | None = None
    icon_markers: list[IconMarker] = field(default_factory=list)
    tmx_file: str | None = None


@dataclass
class MapPersistence:
    """Per-map mutable state that persists across visits."""
    collected_scrap: set[tuple] = field(default_factory=set)
    defeated_enemies: set[int] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Map grids
# ---------------------------------------------------------------------------

def _build_overworld():
    """Build an 80x60 outdoor overworld grid.

    Layout:
      Rows 0-2:   Dense TREE border (north) with stream gap
      Rows 3-15:  Northern wilderness — GRASS, scattered TREE clusters,
                  east-west stream (WATER ~rows 8-9), PATH bridge at col ~35,
                  old gas station RUINS near (60,5) with SCRAP
      Rows 16-22: Forest corridors — thicker TREE bands, PATH threading
      Rows 23-37: Central settlement (cols ~28-50, rows ~25-35):
                  WALL buildings with DOOR entrances, PATH crossroads
      Rows 38-50: Southern wilderness — GRASS, old parking lot RUINS
      Rows 50-58: Southern boundary — TREE line + WATER marsh
      Row 59:     TREE border
    """
    W, H = 80, 60
    G = GRASS  # shorthand
    grid = [[G] * W for _ in range(H)]

    def fill(x1, y1, x2, y2, tile):
        for yy in range(max(0, y1), min(H, y2 + 1)):
            for xx in range(max(0, x1), min(W, x2 + 1)):
                grid[yy][xx] = tile

    def hline(x1, x2, y, tile):
        for xx in range(max(0, x1), min(W, x2 + 1)):
            if 0 <= y < H:
                grid[y][xx] = tile

    def vline(x, y1, y2, tile):
        for yy in range(max(0, y1), min(H, y2 + 1)):
            if 0 <= x < W:
                grid[yy][x] = tile

    def put(x, y, tile):
        if 0 <= x < W and 0 <= y < H:
            grid[y][x] = tile

    # === BORDERS ===
    # North tree border (rows 0-2)
    fill(0, 0, W - 1, 2, TREE)
    # South tree border (row 59)
    hline(0, W - 1, 59, TREE)
    # West tree border column
    vline(0, 0, 59, TREE)
    # East tree border column
    vline(79, 0, 59, TREE)

    # === NORTHERN WILDERNESS (rows 3-15) ===
    # Scattered tree clusters
    tree_clusters = [
        (3, 4), (4, 4), (5, 3), (5, 4),
        (10, 5), (11, 5), (10, 6), (11, 6),
        (20, 3), (21, 3), (20, 4),
        (25, 6), (26, 6), (25, 7),
        (45, 4), (46, 4), (45, 5),
        (50, 3), (51, 3), (52, 3),
        (70, 4), (71, 4), (70, 5), (71, 5),
        (15, 10), (16, 10),
        (55, 6), (56, 6), (55, 7),
        (73, 7), (74, 7),
    ]
    for tx, ty in tree_clusters:
        put(tx, ty, TREE)

    # East-west stream (rows 8-9) with bridge gap at col ~35
    for x in range(1, W - 1):
        if 33 <= x <= 37:  # bridge gap — PATH
            put(x, 8, PATH)
            put(x, 9, PATH)
        else:
            put(x, 8, WATER)
            put(x, 9, WATER)

    # Gas station ruins near (60, 5)
    fill(58, 4, 63, 7, RUINS)
    put(60, 5, SCRAP)
    put(62, 6, SCRAP)

    # Scrap near wilderness
    put(8, 7, SCRAP)
    put(28, 5, SCRAP)
    put(48, 6, SCRAP)

    # === MAIN NORTH-SOUTH PATH ===
    # Path from bridge south to settlement and beyond
    vline(35, 9, 55, PATH)
    # Widen the path a bit near settlement
    vline(36, 20, 38, PATH)

    # === FOREST CORRIDORS (rows 16-22) ===
    # Thick tree bands with path threading through
    forest_trees = []
    # Western forest band
    for x in range(2, 20):
        for y in range(16, 22):
            # Leave gaps for the NW path
            if 10 <= x <= 13 and y in (17, 18, 19):
                continue
            if x % 3 == 0 or y % 2 == 0:
                forest_trees.append((x, y))
    # Eastern forest band
    for x in range(55, 78):
        for y in range(16, 22):
            # Leave gap for east path
            if 64 <= x <= 67:
                continue
            if x % 3 == 0 or y % 2 == 0:
                forest_trees.append((x, y))
    for tx, ty in forest_trees:
        put(tx, ty, TREE)

    # NW path to Scrap Cave
    for y in range(18, 26):
        put(12, y, PATH)
    hline(12, 35, 25, PATH)

    # East path from settlement to Scrap Factory
    hline(50, 68, 30, PATH)

    # === CENTRAL SETTLEMENT (rows 25-35, cols 28-50) ===
    # Town square / crossroads
    fill(30, 28, 42, 32, PATH)  # central plaza
    hline(28, 50, 30, PATH)     # east-west road through town

    # --- Tinker Shop (NW of plaza) ---
    fill(28, 25, 33, 27, WALL)
    put(31, 27, DOOR)  # entrance on south wall

    # --- Volt Forge (NE of plaza) ---
    fill(38, 25, 43, 27, WALL)
    put(40, 27, DOOR)  # entrance on south wall

    # --- Iron Shell Outfitters (east of plaza) ---
    fill(46, 28, 50, 31, WALL)
    put(46, 29, DOOR)  # entrance on west wall

    # --- Settlement fountain (center of plaza) ---
    put(36, 30, WATER)
    put(37, 30, WATER)
    put(36, 31, WATER)
    put(37, 31, WATER)

    # === SCRAP CAVE ENTRANCE (NW, near col 12, row 18) ===
    fill(9, 15, 15, 17, WALL)
    put(12, 17, DOOR)  # cave mouth

    # === SCRAP FACTORY (east, col 68, row 30) ===
    fill(66, 28, 72, 32, RUINS)
    put(68, 32, DOOR)  # factory entrance on south wall

    # === SOUTHERN WILDERNESS (rows 38-50) ===
    # Old parking lot ruins cluster (cols 10-20, rows 42-46)
    fill(10, 42, 20, 46, RUINS)
    # Gaps in the parking lot
    fill(13, 43, 15, 45, G)
    put(12, 43, SCRAP)
    put(18, 44, SCRAP)
    put(16, 46, SCRAP)

    # More scrap in southern wilds
    put(40, 42, SCRAP)
    put(55, 45, SCRAP)
    put(65, 48, SCRAP)

    # Scattered trees in southern area
    south_trees = [
        (5, 40), (6, 40), (5, 41),
        (25, 43), (26, 43),
        (30, 45), (31, 45), (30, 46),
        (50, 40), (51, 40),
        (60, 42), (61, 42), (60, 43),
        (72, 44), (73, 44),
        (35, 48), (36, 48),
    ]
    for tx, ty in south_trees:
        put(tx, ty, TREE)

    # South path continues
    vline(35, 38, 55, PATH)

    # === SOUTHERN BOUNDARY (rows 50-58) ===
    # Marsh/lake
    fill(1, 53, 78, 55, WATER)
    # Tree line above and below marsh
    fill(1, 50, 78, 52, TREE)
    fill(1, 56, 78, 58, TREE)
    # Gap in tree line for path
    for y in range(50, 59):
        put(35, y, PATH)
        put(36, y, PATH)

    return grid


_OVERWORLD_GRID = _build_overworld()

_TINKER_SHOP_GRID = [
    [1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,1,1,1,1,1,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,3,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1],
]

_SCRAP_CAVE_GRID = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,1,0,0,0,0,0,0,0,0,1,0,0,0,0,3,1],
    [1,0,0,0,1,0,0,2,0,0,0,0,0,1,0,0,0,2,0,1],
    [1,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,1],
    [1,1,1,0,0,0,0,0,0,1,0,0,0,0,0,1,1,0,0,1],
    [1,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,0,0,0,1],
    [1,0,2,0,0,1,0,0,0,0,0,0,2,0,0,0,0,0,0,1],
    [1,0,0,0,0,1,1,0,0,0,0,1,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,1,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1],
    [1,0,0,1,1,0,0,0,2,0,0,0,0,0,0,0,0,2,0,1],
    [1,0,0,1,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1],
    [1,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]

_SCRAP_FACTORY_GRID = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,1],
    [1,0,0,1,1,1,0,0,0,0,0,1,1,1,1,0,0,0,0,1,0,0,0,0,1],
    [1,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1,0,2,0,0,1],
    [1,0,0,1,0,2,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1],
    [1,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1,1,1,0,0,0,0,2,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,1],
    [1,0,2,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]

_REACTOR_CORE_GRID = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,0,0,0,0,1,0,0,0,2,0,1],
    [1,0,0,1,1,0,1,0,0,0,0,1,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1,0,0,0,1,1,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1],
    [1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,2,0,1],
    [1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,2,0,0,0,0,0,1,1,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]

_VOLT_FORGE_GRID = [
    [1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1],
    [1,0,0,1,1,1,1,0,0,1],
    [1,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,3,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1],
]

_IRON_SHELL_GRID = [
    [1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1],
    [1,0,0,1,1,1,1,0,0,1],
    [1,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,3,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1],
]
# fmt: on

# ---------------------------------------------------------------------------
# Map registry
# ---------------------------------------------------------------------------

MAP_REGISTRY: dict[str, MapDef] = {
    "overworld": MapDef(
        map_id="overworld",
        display_name="Overworld",
        grid=_OVERWORLD_GRID,
        player_start_x=35,
        player_start_y=30,
        npcs=[
            NPCDef(
                33, 29, "Old Tinker", "old_tinker_overworld",
                color=(80, 180, 80), facing="down", sprite_key="old_tinker",
            ),
            NPCDef(
                38, 29, "Sparks", "sparks_overworld",
                color=(160, 180, 60), facing="left",
                sprite_style="robot",
            ),
            NPCDef(
                34, 32, "Drifter", "drifter_overworld",
                color=(160, 100, 180), facing="right", sprite_key="drifter",
            ),
            NPCDef(
                40, 32, "Scout", "scout_overworld",
                color=(100, 160, 200), facing="down", sprite_key="scout",
            ),
        ],
        enemies=[
            EnemyNPCDef(20, 12, "Rust Golem", (160, 60, 40)),
            EnemyNPCDef(60, 35, "Volt Wraith", (100, 40, 160)),
            EnemyNPCDef(15, 44, "Forge Guardian", (200, 120, 40)),
        ],
        doors=[
            DoorDef(31, 27, "tinker_shop", 5, 7, "up"),
            DoorDef(12, 17, "scrap_cave", 2, 13, "up"),
            DoorDef(68, 32, "scrap_factory", 12, 15, "up"),
            DoorDef(40, 27, "volt_forge", 5, 6, "up"),
            DoorDef(46, 29, "iron_shell", 5, 6, "up"),
        ],
        encounter_table=["Scrap Rat", "Scrap Rat", "Wire Spider", "Rust Golem"],
        encounter_chance=0.05,
        music_track="overworld",
        icon_markers=[
            IconMarker(39, 25, "sword", (255, 160, 60)),
            IconMarker(48, 28, "shield", (80, 160, 255)),
        ],
        tmx_file="overworld.tmx",
    ),
    "tinker_shop": MapDef(
        map_id="tinker_shop",
        display_name="Tinker's Shop",
        grid=_TINKER_SHOP_GRID,
        player_start_x=5,
        player_start_y=7,
        npcs=[
            NPCDef(
                5, 2, "Shopkeeper", "shopkeeper",
                color=(180, 120, 60), facing="down", sprite_key="old_tinker",
            ),
        ],
        enemies=[],
        doors=[
            DoorDef(5, 8, "overworld", 31, 28, "down"),
        ],
        encounter_table=[],
        encounter_chance=0.0,
        music_track="overworld",
        tmx_file="tinker_shop.tmx",
    ),
    "scrap_cave": MapDef(
        map_id="scrap_cave",
        display_name="Scrap Cave",
        grid=_SCRAP_CAVE_GRID,
        player_start_x=2,
        player_start_y=13,
        npcs=[],
        enemies=[
            EnemyNPCDef(10, 5, "Volt Wraith", (100, 40, 160)),
            EnemyNPCDef(18, 2, "Meltdown Warden", (220, 60, 60)),
        ],
        doors=[
            DoorDef(1, 13, "overworld", 12, 18, "down"),
            DoorDef(18, 1, "reactor_core", 1, 11, "up"),
        ],
        encounter_table=["Rust Golem", "Rust Golem", "Volt Wraith", "Slag Beetle"],
        encounter_chance=0.05,
        music_track="overworld",
        tile_colors_override={0: (100, 70, 40)},  # darker dirt for cave
    ),
    "scrap_factory": MapDef(
        map_id="scrap_factory",
        display_name="Scrap Factory",
        grid=_SCRAP_FACTORY_GRID,
        player_start_x=12,
        player_start_y=15,
        npcs=[
            NPCDef(
                5, 9, "Engineer", "engineer_factory",
                color=(180, 180, 100), facing="down",
            ),
        ],
        enemies=[
            EnemyNPCDef(11, 8, "Plasma Hound", (200, 100, 40)),
        ],
        doors=[
            DoorDef(12, 16, "overworld", 68, 33, "down"),
        ],
        encounter_table=["Wire Spider", "Slag Beetle", "Plasma Hound"],
        encounter_chance=0.06,
        music_track="overworld",
        tile_colors_override={0: (80, 80, 90)},  # grey-blue factory floor
    ),
    "reactor_core": MapDef(
        map_id="reactor_core",
        display_name="Reactor Core",
        grid=_REACTOR_CORE_GRID,
        player_start_x=1,
        player_start_y=11,
        npcs=[],
        enemies=[
            EnemyNPCDef(8, 6, "Core Leech", (180, 40, 200)),
        ],
        doors=[
            DoorDef(1, 12, "scrap_cave", 18, 3, "down"),
        ],
        encounter_table=["Core Leech", "Volt Wraith", "Plasma Hound"],
        encounter_chance=0.07,
        music_track="overworld",
        tile_colors_override={0: (50, 40, 60)},  # dark purple reactor floor
    ),
    "volt_forge": MapDef(
        map_id="volt_forge",
        display_name="Volt's Forge",
        grid=_VOLT_FORGE_GRID,
        player_start_x=5,
        player_start_y=6,
        npcs=[
            NPCDef(
                4, 2, "Weaponsmith", "weaponsmith",
                color=(180, 100, 50), facing="down",
                sprite_style="robot",
            ),
        ],
        enemies=[],
        doors=[
            DoorDef(5, 7, "overworld", 40, 28, "down"),
        ],
        encounter_table=[],
        encounter_chance=0.0,
        music_track="overworld",
        tile_colors_override={0: (140, 100, 50)},  # warm orange floor
    ),
    "iron_shell": MapDef(
        map_id="iron_shell",
        display_name="Iron Shell Outfitters",
        grid=_IRON_SHELL_GRID,
        player_start_x=5,
        player_start_y=6,
        npcs=[
            NPCDef(
                4, 2, "Armorsmith", "armorsmith",
                color=(100, 120, 160), facing="down",
                sprite_style="robot",
            ),
        ],
        enemies=[],
        doors=[
            DoorDef(5, 7, "overworld", 45, 29, "left"),
        ],
        encounter_table=[],
        encounter_chance=0.0,
        music_track="overworld",
        tile_colors_override={0: (60, 80, 120)},  # cool blue floor
    ),
}
