"""Map definitions and registry for multi-map navigation.

# TODO: Next step — move NPCs, doors, enemies, encounters, and spawn points
# into TMX object layers so level design can be done entirely in Tiled.
"""
from dataclasses import dataclass, field


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
    player_start_x: int
    player_start_y: int
    npcs: list[NPCDef] = field(default_factory=list)
    enemies: list[EnemyNPCDef] = field(default_factory=list)
    doors: list[DoorDef] = field(default_factory=list)
    encounter_table: list[str] = field(default_factory=list)
    encounter_chance: float = 0.0
    music_track: str = "overworld"
    scrap_positions: list[tuple[int, int]] = field(default_factory=list)
    icon_markers: list[IconMarker] = field(default_factory=list)
    tmx_file: str | None = None


@dataclass
class MapPersistence:
    """Per-map mutable state that persists across visits."""
    collected_scrap: set[tuple] = field(default_factory=set)
    defeated_enemies: set[int] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Map registry
# ---------------------------------------------------------------------------

MAP_REGISTRY: dict[str, MapDef] = {
    "overworld": MapDef(
        map_id="overworld",
        display_name="Overworld",
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
        scrap_positions=[
            (60, 5), (62, 6), (8, 7), (28, 5), (48, 6),
            (12, 43), (18, 44), (16, 46),
            (40, 42), (55, 45), (65, 48),
        ],
        icon_markers=[
            IconMarker(39, 25, "sword", (255, 160, 60)),
            IconMarker(48, 28, "shield", (80, 160, 255)),
        ],
        tmx_file="overworld.tmx",
    ),
    "tinker_shop": MapDef(
        map_id="tinker_shop",
        display_name="Tinker's Shop",
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
        scrap_positions=[
            (7, 2), (17, 2), (2, 6), (12, 6), (8, 10), (17, 10),
        ],
        tmx_file="scrap_cave.tmx",
    ),
    "scrap_factory": MapDef(
        map_id="scrap_factory",
        display_name="Scrap Factory",
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
        scrap_positions=[
            (21, 4), (5, 5), (14, 8), (22, 12), (2, 14),
        ],
        tmx_file="scrap_factory.tmx",
    ),
    "reactor_core": MapDef(
        map_id="reactor_core",
        display_name="Reactor Core",
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
        scrap_positions=[
            (15, 2), (15, 8), (5, 10),
        ],
        tmx_file="reactor_core.tmx",
    ),
    "volt_forge": MapDef(
        map_id="volt_forge",
        display_name="Volt's Forge",
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
        tmx_file="volt_forge.tmx",
    ),
    "iron_shell": MapDef(
        map_id="iron_shell",
        display_name="Iron Shell Outfitters",
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
        tmx_file="iron_shell.tmx",
    ),
}
