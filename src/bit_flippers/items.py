from dataclasses import dataclass, field


@dataclass
class Item:
    name: str
    description: str
    item_type: str  # "consumable", "material", or "equipment"
    effect_type: str | None = None  # "heal", "damage", "buff_defense", or None
    effect_value: int = 0
    price: int = 0  # buy price; sell price = price // 2
    slot: str | None = None  # "weapon", "armor", "accessory" (equipment only)
    stat_bonuses: dict[str, int] = field(default_factory=dict)


ITEM_REGISTRY: dict[str, Item] = {
    "Scrap Metal": Item(
        name="Scrap Metal",
        description="Salvaged metal scraps. Useful for crafting.",
        item_type="material",
        price=2,
    ),
    "Repair Kit": Item(
        name="Repair Kit",
        description="Restores 10 HP.",
        item_type="consumable",
        effect_type="heal",
        effect_value=10,
        price=8,
    ),
    "Voltage Spike": Item(
        name="Voltage Spike",
        description="Deals 8 damage to an enemy, bypassing defense.",
        item_type="consumable",
        effect_type="damage",
        effect_value=8,
        price=12,
    ),
    "Antidote Kit": Item(
        name="Antidote Kit",
        description="Clears all status effects.",
        item_type="consumable",
        effect_type="cure_status",
        price=10,
    ),
    "Iron Plating": Item(
        name="Iron Plating",
        description="Boosts defense by 3 for the current combat.",
        item_type="consumable",
        effect_type="buff_defense",
        effect_value=3,
        price=10,
    ),
    # --- Weapons ---
    "Bronze Vibro-Knife": Item(
        name="Bronze Vibro-Knife",
        description="A humming blade. ATK +2.",
        item_type="equipment", slot="weapon",
        stat_bonuses={"strength": 2}, price=20,
    ),
    "Silver Pulse Blade": Item(
        name="Silver Pulse Blade",
        description="Pulsing energy edge. ATK +4.",
        item_type="equipment", slot="weapon",
        stat_bonuses={"strength": 4}, price=50,
    ),
    "Titanium Arc Saber": Item(
        name="Titanium Arc Saber",
        description="Arcing plasma blade. ATK +7.",
        item_type="equipment", slot="weapon",
        stat_bonuses={"strength": 7}, price=120,
    ),
    "Palladium Plasma Edge": Item(
        name="Palladium Plasma Edge",
        description="Legendary plasma weapon. ATK +11.",
        item_type="equipment", slot="weapon",
        stat_bonuses={"strength": 11}, price=280,
    ),
    # --- Armor ---
    "Bronze Shield Vest": Item(
        name="Bronze Shield Vest",
        description="Basic plated vest. DEF +2.",
        item_type="equipment", slot="armor",
        stat_bonuses={"resilience": 2}, price=20,
    ),
    "Silver Flux Armor": Item(
        name="Silver Flux Armor",
        description="Flux-shielded plates. DEF +4.",
        item_type="equipment", slot="armor",
        stat_bonuses={"resilience": 4}, price=50,
    ),
    "Titanium Aegis Plate": Item(
        name="Titanium Aegis Plate",
        description="Heavy aegis plating. DEF +7.",
        item_type="equipment", slot="armor",
        stat_bonuses={"resilience": 7}, price=120,
    ),
    "Palladium Nano Suit": Item(
        name="Palladium Nano Suit",
        description="Nano-fiber armor. DEF +11.",
        item_type="equipment", slot="armor",
        stat_bonuses={"resilience": 11}, price=280,
    ),
    # --- Accessories ---
    "Bronze Servo Ring": Item(
        name="Bronze Servo Ring",
        description="Servo-enhanced ring. Max HP +3.",
        item_type="equipment", slot="accessory",
        stat_bonuses={"max_hp": 3}, price=15,
    ),
    "Silver Combat Vizor": Item(
        name="Silver Combat Vizor",
        description="Targeting vizor. DEX +2.",
        item_type="equipment", slot="accessory",
        stat_bonuses={"dexterity": 2}, price=45,
    ),
    "Titanium Reflex Core": Item(
        name="Titanium Reflex Core",
        description="Reflex enhancer. DEX +2, Max SP +3.",
        item_type="equipment", slot="accessory",
        stat_bonuses={"dexterity": 2, "max_sp": 3}, price=110,
    ),
    "Palladium Neural Link": Item(
        name="Palladium Neural Link",
        description="Neural interface. INT +3, Max SP +5.",
        item_type="equipment", slot="accessory",
        stat_bonuses={"intelligence": 3, "max_sp": 5}, price=260,
    ),
    # --- Chromium tier (chest/drop only) ---
    "Chromium Ion Blade": Item(
        name="Chromium Ion Blade",
        description="Ion-forged blade. ATK +15.",
        item_type="equipment", slot="weapon",
        stat_bonuses={"strength": 15}, price=500,
    ),
    "Chromium Exo Armor": Item(
        name="Chromium Exo Armor",
        description="Exoskeletal plating. DEF +15.",
        item_type="equipment", slot="armor",
        stat_bonuses={"resilience": 15}, price=500,
    ),
    "Chromium Sync Module": Item(
        name="Chromium Sync Module",
        description="Neural sync device. DEX +3, INT +3, Max SP +5.",
        item_type="equipment", slot="accessory",
        stat_bonuses={"dexterity": 3, "intelligence": 3, "max_sp": 5}, price=450,
    ),
}

# Items available in the default shop (unlimited stock)
SHOP_STOCK: list[str] = ["Repair Kit", "Voltage Spike", "Iron Plating", "Antidote Kit", "Scrap Metal"]

# Weaponsmith stock
WEAPONSMITH_STOCK: list[str] = [
    "Bronze Vibro-Knife", "Silver Pulse Blade", "Titanium Arc Saber", "Palladium Plasma Edge",
    "Repair Kit", "Voltage Spike",
]

# Armorsmith stock
ARMORSMITH_STOCK: list[str] = [
    "Bronze Shield Vest", "Silver Flux Armor", "Titanium Aegis Plate", "Palladium Nano Suit",
    "Bronze Servo Ring", "Silver Combat Vizor", "Titanium Reflex Core", "Palladium Neural Link",
]


class Equipment:
    """Tracks which items are equipped in each slot."""
    SLOTS = ("weapon", "armor", "accessory")

    def __init__(self):
        self.slots: dict[str, str | None] = {s: None for s in self.SLOTS}

    def equip(self, item_name: str) -> str | None:
        """Equip an item. Returns the previously equipped item name (or None)."""
        item = ITEM_REGISTRY.get(item_name)
        if not item or item.item_type != "equipment" or not item.slot:
            return None
        previous = self.slots.get(item.slot)
        self.slots[item.slot] = item_name
        return previous

    def unequip(self, slot: str) -> str | None:
        """Unequip the item in a slot. Returns the removed item name (or None)."""
        previous = self.slots.get(slot)
        if slot in self.slots:
            self.slots[slot] = None
        return previous

    def is_equipped(self, item_name: str) -> bool:
        return item_name in self.slots.values()

    def get_total_bonuses(self) -> dict[str, int]:
        """Sum stat bonuses from all equipped items."""
        totals: dict[str, int] = {}
        for item_name in self.slots.values():
            if item_name is None:
                continue
            item = ITEM_REGISTRY.get(item_name)
            if item:
                for stat, val in item.stat_bonuses.items():
                    totals[stat] = totals.get(stat, 0) + val
        return totals

    def to_dict(self) -> dict[str, str | None]:
        return dict(self.slots)

    @classmethod
    def from_dict(cls, data: dict[str, str | None]) -> "Equipment":
        eq = cls()
        for slot in cls.SLOTS:
            eq.slots[slot] = data.get(slot)
        return eq


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

    def to_dict(self) -> dict[str, int]:
        return dict(self.items)

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> "Inventory":
        inv = cls()
        inv.items = dict(data)
        return inv
