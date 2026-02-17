"""Map definitions and registry for multi-map navigation."""
from dataclasses import dataclass, field

from bit_flippers.tilemap import DIRT, WALL, SCRAP, DOOR


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


@dataclass
class EnemyNPCDef:
    """Placement data for a scripted enemy encounter on the map."""
    tile_x: int
    tile_y: int
    enemy_type_key: str
    color: tuple[int, int, int]


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


@dataclass
class MapPersistence:
    """Per-map mutable state that persists across visits."""
    collected_scrap: set[tuple] = field(default_factory=set)
    defeated_enemies: set[int] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Map grids
# ---------------------------------------------------------------------------

# fmt: off
_OVERWORLD_GRID = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,2,0,0,1],
    [1,0,0,1,1,1,1,0,0,0,0,0,0,1,0,0,2,0,0,0,0,0,0,0,0,0,1,0,0,1,1,1,1,1,0,0,0,0,0,1],
    [1,0,0,1,0,0,0,0,0,0,2,0,0,1,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0,1],
    [1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,0,0,0,0,1,0,0,0,1,0,0,0,0,0,1],
    [1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,2,1,0,0,0,0,0,0,1,0,2,0,1,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,2,0,0,1,1,1,0,0,0,0,0,0,0,1,1,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,2,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1],
    [1,0,2,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,2,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,1,1,1,1,1,1,1],
    [1,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1],
    [1,0,0,0,0,1,1,3,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,2,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1,0,0,0,0,0,0,0,1,1,1,1,1,0,0,1,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,2,0,0,0,0,0,1,0,2,0,0,1,0,0,0,0,0,0,0,1,0,0,2,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1,0,0,0,2,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,1,1,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]

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
    [1,0,0,0,1,0,0,0,0,0,0,0,0,1,0,0,0,0,0,1],
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
# fmt: on

# ---------------------------------------------------------------------------
# Map registry
# ---------------------------------------------------------------------------

MAP_REGISTRY: dict[str, MapDef] = {
    "overworld": MapDef(
        map_id="overworld",
        display_name="Overworld",
        grid=_OVERWORLD_GRID,
        player_start_x=2,
        player_start_y=2,
        npcs=[
            NPCDef(
                5, 5, "Old Tinker", "old_tinker_overworld",
                color=(80, 180, 80), facing="down", sprite_key="old_tinker",
            ),
            NPCDef(
                16, 4, "Sparks", "sparks_overworld",
                color=(200, 160, 50), facing="left", sprite_key="sparks",
            ),
            NPCDef(
                22, 7, "Drifter", "drifter_overworld",
                color=(160, 100, 180), facing="right", sprite_key="drifter",
            ),
            NPCDef(
                34, 2, "Scout", "scout_overworld",
                color=(100, 160, 200), facing="down", sprite_key="scout",
            ),
        ],
        enemies=[
            EnemyNPCDef(10, 8, "Rust Golem", (160, 60, 40)),
            EnemyNPCDef(30, 12, "Volt Wraith", (100, 40, 160)),
        ],
        doors=[
            DoorDef(7, 18, "tinker_shop", 5, 7, "up"),
            DoorDef(32, 28, "scrap_cave", 2, 13, "up"),
        ],
        encounter_table=["Scrap Rat", "Scrap Rat", "Rust Golem"],
        encounter_chance=0.05,
        music_track="overworld",
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
            DoorDef(5, 8, "overworld", 7, 19, "down"),
        ],
        encounter_table=[],
        encounter_chance=0.0,
        music_track="overworld",
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
        ],
        doors=[
            DoorDef(1, 13, "overworld", 33, 28, "down"),
        ],
        encounter_table=["Rust Golem", "Rust Golem", "Volt Wraith"],
        encounter_chance=0.05,
        music_track="overworld",
        tile_colors_override={0: (100, 70, 40)},  # darker dirt for cave
    ),
}
