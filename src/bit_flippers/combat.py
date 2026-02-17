from dataclasses import dataclass, field

from bit_flippers.sprites import AnimatedSprite, create_placeholder_enemy, load_player, load_enemy


@dataclass
class StatusEffect:
    name: str
    turns_remaining: int


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
    xp_reward: int = 0
    money_reward: int = 0
    dexterity: int = 5
    ability: dict | None = None


ENEMY_TYPES: dict[str, EnemyData] = {
    "Scrap Rat": EnemyData(name="Scrap Rat", hp=12, attack=4, defense=1, color=(140, 100, 60), xp_reward=8, money_reward=5, dexterity=4),
    "Rust Golem": EnemyData(name="Rust Golem", hp=25, attack=7, defense=4, color=(160, 80, 40), xp_reward=18, money_reward=12, dexterity=2),
    "Volt Wraith": EnemyData(name="Volt Wraith", hp=20, attack=10, defense=2, color=(100, 60, 180), xp_reward=22, money_reward=15, dexterity=7, ability={"name": "Paralyzing Shock", "status_effect": "Stun", "chance": 0.20}),
    "Wire Spider": EnemyData(name="Wire Spider", hp=10, attack=6, defense=0, color=(60, 180, 60), xp_reward=10, money_reward=6, dexterity=8, ability={"name": "Venomous Bite", "status_effect": "Poison", "chance": 0.30}),
    "Slag Beetle": EnemyData(name="Slag Beetle", hp=18, attack=5, defense=6, color=(120, 60, 30), xp_reward=14, money_reward=10, dexterity=1),
    "Plasma Hound": EnemyData(name="Plasma Hound", hp=22, attack=9, defense=3, color=(200, 100, 40), xp_reward=20, money_reward=14, dexterity=5, ability={"name": "Fire Breath", "status_effect": "Burn", "chance": 0.25}),
    "Core Leech": EnemyData(name="Core Leech", hp=28, attack=12, defense=3, color=(180, 40, 200), xp_reward=28, money_reward=20, dexterity=6, ability={"name": "Psychic Drain", "status_effect": "Despondent", "chance": 0.30}),
    "Forge Guardian": EnemyData(name="Forge Guardian", hp=50, attack=12, defense=6, color=(200, 120, 40), xp_reward=60, money_reward=40, dexterity=3, ability={"name": "Heavy Slam", "status_effect": "Stun", "chance": 0.25}),
    "Meltdown Warden": EnemyData(name="Meltdown Warden", hp=60, attack=14, defense=5, color=(220, 60, 60), xp_reward=80, money_reward=55, dexterity=6, ability={"name": "Meltdown Pulse", "status_effect": "Burn", "chance": 0.35}),
}


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
