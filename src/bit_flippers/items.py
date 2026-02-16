from dataclasses import dataclass


@dataclass
class Item:
    name: str
    description: str
    item_type: str  # "consumable" or "material"
    effect_type: str | None = None  # "heal", "damage", "buff_defense", or None
    effect_value: int = 0


ITEM_REGISTRY: dict[str, Item] = {
    "Scrap Metal": Item(
        name="Scrap Metal",
        description="Salvaged metal scraps. Useful for crafting.",
        item_type="material",
    ),
    "Repair Kit": Item(
        name="Repair Kit",
        description="Restores 10 HP.",
        item_type="consumable",
        effect_type="heal",
        effect_value=10,
    ),
    "Voltage Spike": Item(
        name="Voltage Spike",
        description="Deals 8 damage to an enemy, bypassing defense.",
        item_type="consumable",
        effect_type="damage",
        effect_value=8,
    ),
    "Iron Plating": Item(
        name="Iron Plating",
        description="Boosts defense by 3 for the current combat.",
        item_type="consumable",
        effect_type="buff_defense",
        effect_value=3,
    ),
}


class Inventory:
    def __init__(self):
        self.items: dict[str, int] = {}

    def add(self, item_name: str, count: int = 1):
        self.items[item_name] = self.items.get(item_name, 0) + count

    def remove(self, item_name: str, count: int = 1):
        if item_name in self.items:
            self.items[item_name] -= count
            if self.items[item_name] <= 0:
                del self.items[item_name]

    def has(self, item_name: str) -> bool:
        return self.items.get(item_name, 0) > 0

    def get_count(self, item_name: str) -> int:
        return self.items.get(item_name, 0)

    def get_consumables(self) -> list[str]:
        result = []
        for name, count in self.items.items():
            if count > 0 and name in ITEM_REGISTRY and ITEM_REGISTRY[name].item_type == "consumable":
                result.append(name)
        return result
