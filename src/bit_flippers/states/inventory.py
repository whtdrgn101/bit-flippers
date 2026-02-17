import pygame
from bit_flippers.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_INVENTORY_BG,
    COLOR_ITEM_HIGHLIGHT,
)
from bit_flippers.items import ITEM_REGISTRY


# Colors for item type tags
_TYPE_COLORS = {
    "equipment": (120, 180, 255),
    "consumable": (120, 220, 120),
    "material": (180, 180, 140),
}


class InventoryState:
    def __init__(self, game, inventory, overworld):
        self.game = game
        self.inventory = inventory
        self.overworld = overworld
        self.cursor = 0
        self.scroll_offset = 0
        self.max_visible = 10
        self.message = ""
        self.message_timer = 0.0

        self.font_title = pygame.font.SysFont(None, 36)
        self.font_item = pygame.font.SysFont(None, 26)
        self.font_desc = pygame.font.SysFont(None, 22)
        self.font_tag = pygame.font.SysFont(None, 20)

        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill(COLOR_INVENTORY_BG)

    def _get_item_list(self):
        """Return list of (name, count) grouped: equipment first, then consumables, then materials."""
        groups = {"equipment": [], "consumable": [], "material": [], "other": []}
        for name, count in self.inventory.items.items():
            if count <= 0:
                continue
            item = ITEM_REGISTRY.get(name)
            if item:
                key = item.item_type if item.item_type in groups else "other"
                groups[key].append((name, count))
            else:
                groups["other"].append((name, count))
        # Sort within each group
        result = []
        for key in ("equipment", "consumable", "material", "other"):
            result.extend(sorted(groups[key]))
        return result

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        items = self._get_item_list()

        if event.key == pygame.K_ESCAPE:
            self.game.pop_state()
        elif event.key == pygame.K_UP:
            if items:
                self.cursor = (self.cursor - 1) % len(items)
                self._ensure_visible()
        elif event.key == pygame.K_DOWN:
            if items:
                self.cursor = (self.cursor + 1) % len(items)
                self._ensure_visible()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if items:
                name, _count = items[self.cursor]
                self._try_use_item(name)

    def _ensure_visible(self):
        if self.cursor < self.scroll_offset:
            self.scroll_offset = self.cursor
        elif self.cursor >= self.scroll_offset + self.max_visible:
            self.scroll_offset = self.cursor - self.max_visible + 1

    def _try_use_item(self, item_name):
        item = ITEM_REGISTRY.get(item_name)
        if not item:
            self.message = "Can't use that."
            self.message_timer = 1.5
            return

        # Equipment: toggle equip/unequip
        if item.item_type == "equipment":
            equipment = getattr(self.overworld, "equipment", None)
            if equipment is None:
                self.message = "Can't equip that."
                self.message_timer = 1.5
                return
            if equipment.is_equipped(item_name):
                equipment.unequip(item.slot)
                self.game.audio.play_sfx("pickup")
                self.message = f"Unequipped {item_name}."
            else:
                prev = equipment.equip(item_name)
                self.game.audio.play_sfx("pickup")
                self.message = f"Equipped {item_name}!"
            self.message_timer = 1.5
            return

        if item.item_type != "consumable":
            self.message = "Can't use that."
            self.message_timer = 1.5
            return

        if item.effect_type == "heal":
            if self.overworld.stats.current_hp >= self.overworld.stats.max_hp:
                self.message = "HP is already full!"
                self.message_timer = 1.5
                return
            self.overworld.stats.current_hp = min(
                self.overworld.stats.max_hp, self.overworld.stats.current_hp + item.effect_value
            )
            self.inventory.remove(item_name)
            self.game.audio.play_sfx("pickup")
            self.message = f"Used {item_name}! HP restored."
            self.message_timer = 1.5
        else:
            self.message = "Can only use this in combat."
            self.message_timer = 1.5

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

    def _selected_item_data(self, items):
        """Return the Item for the currently selected entry, or None."""
        if 0 <= self.cursor < len(items):
            return ITEM_REGISTRY.get(items[self.cursor][0])
        return None

    def draw(self, screen):
        screen.blit(self.overlay, (0, 0))

        # Title
        title = self.font_title.render("INVENTORY", True, (255, 255, 255))
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 30))

        items = self._get_item_list()
        equipment = getattr(self.overworld, "equipment", None)

        if not items:
            empty = self.font_item.render("No items.", True, (160, 160, 160))
            screen.blit(empty, (SCREEN_WIDTH // 2 - empty.get_width() // 2, 100))
        else:
            list_x = 80
            list_y = 80
            row_height = 28

            visible = items[self.scroll_offset : self.scroll_offset + self.max_visible]
            for i, (name, count) in enumerate(visible):
                abs_index = self.scroll_offset + i
                is_selected = abs_index == self.cursor
                item_data = ITEM_REGISTRY.get(name)

                color = COLOR_ITEM_HIGHLIGHT if is_selected else (200, 200, 200)
                prefix = "> " if is_selected else "  "

                # Build display label
                equipped_tag = ""
                if equipment and equipment.is_equipped(name):
                    equipped_tag = " [E]"
                label = f"{prefix}{name}{equipped_tag} x{count}"
                text = self.font_item.render(label, True, color)
                screen.blit(text, (list_x, list_y + i * row_height))

                # Type tag on right side
                if item_data:
                    tag_label = item_data.item_type.upper()
                    if item_data.item_type == "equipment" and item_data.slot:
                        tag_label = item_data.slot.upper()
                    tag_color = _TYPE_COLORS.get(item_data.item_type, (160, 160, 160))
                    tag_surf = self.font_tag.render(tag_label, True, tag_color)
                    screen.blit(tag_surf, (SCREEN_WIDTH - tag_surf.get_width() - 80, list_y + i * row_height + 3))

            # Scroll indicators
            if self.scroll_offset > 0:
                up_arrow = self.font_desc.render("^ more ^", True, (160, 160, 160))
                screen.blit(up_arrow, (list_x, list_y - 20))
            if self.scroll_offset + self.max_visible < len(items):
                down_arrow = self.font_desc.render("v more v", True, (160, 160, 160))
                screen.blit(
                    down_arrow,
                    (list_x, list_y + self.max_visible * row_height + 4),
                )

            # Description for selected item
            if 0 <= self.cursor < len(items):
                selected_name = items[self.cursor][0]
                item_data = ITEM_REGISTRY.get(selected_name)
                if item_data:
                    desc_text = item_data.description
                    if equipment and equipment.is_equipped(selected_name):
                        desc_text += "  [EQUIPPED]"
                    desc = self.font_desc.render(
                        desc_text, True, (180, 180, 180)
                    )
                    screen.blit(desc, (80, SCREEN_HEIGHT - 80))

        # Feedback message
        if self.message:
            msg = self.font_item.render(self.message, True, (100, 255, 100))
            screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, SCREEN_HEIGHT - 50))

        # Context-sensitive controls hint
        sel = self._selected_item_data(items) if items else None
        if sel and sel.item_type == "equipment":
            is_eq = equipment and equipment.is_equipped(items[self.cursor][0])
            action = "[ENTER] Unequip" if is_eq else "[ENTER] Equip"
        elif sel and sel.item_type == "consumable":
            action = "[ENTER] Use"
        else:
            action = ""
        hint_parts = ["[ESC] Close"]
        if action:
            hint_parts.append(action)
        hint = self.font_desc.render("   ".join(hint_parts), True, (120, 120, 120))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 20))
