from dataclasses import dataclass

from bit_flippers.settings import PLAYER_MAX_HP, PLAYER_ATTACK, PLAYER_DEFENSE
from bit_flippers.sprites import AnimatedSprite, create_placeholder_enemy, load_player, load_enemy


@dataclass
class CombatEntity:
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    sprite: AnimatedSprite

    @property
    def is_alive(self):
        return self.hp > 0


@dataclass
class EnemyData:
    name: str
    hp: int
    attack: int
    defense: int
    color: tuple[int, int, int]


ENEMY_TYPES: dict[str, EnemyData] = {
    "Scrap Rat": EnemyData(name="Scrap Rat", hp=12, attack=4, defense=1, color=(140, 100, 60)),
    "Rust Golem": EnemyData(name="Rust Golem", hp=25, attack=7, defense=4, color=(160, 80, 40)),
    "Volt Wraith": EnemyData(name="Volt Wraith", hp=20, attack=10, defense=2, color=(100, 60, 180)),
}


def create_player_combatant():
    """Create a CombatEntity for the player with default stats."""
    return CombatEntity(
        name="Player",
        hp=PLAYER_MAX_HP,
        max_hp=PLAYER_MAX_HP,
        attack=PLAYER_ATTACK,
        defense=PLAYER_DEFENSE,
        sprite=load_player(),
    )


def create_enemy_combatant(enemy_data: EnemyData) -> CombatEntity:
    """Create a CombatEntity from an EnemyData template."""
    key = enemy_data.name.lower().replace(" ", "_")
    return CombatEntity(
        name=enemy_data.name,
        hp=enemy_data.hp,
        max_hp=enemy_data.hp,
        attack=enemy_data.attack,
        defense=enemy_data.defense,
        sprite=load_enemy(key, enemy_data.color),
    )
