import pygame
from bit_flippers.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_SHOP_BG,
    COLOR_SHOP_TAB_ACTIVE,
    COLOR_SHOP_TAB_INACTIVE,
    COLOR_SHOP_AFFORDABLE,
    COLOR_SHOP_UNAFFORDABLE,
    COLOR_SHOP_CONFIRM_BG,
    COLOR_ITEM_HIGHLIGHT,
    COLOR_MONEY_TEXT,
)
from bit_flippers.items import ITEM_REGISTRY, SHOP_STOCK, Equipment
from bit_flippers.save import save_game


class ShopState:
    TAB_BUY = 0
    TAB_SELL = 1

    def __init__(self, game, overworld, stock_list=None):
        self.game = game
        self.overworld = overworld
        self.stock_list = stock_list or SHOP_STOCK
        self.tab = self.TAB_BUY
        self.cursor = 0
        self.scroll_offset = 0
        self.max_visible = 8

        # Confirmation prompt state
        self.confirming = False
        self.confirm_item = None
        self.confirm_cursor = 0  # 0 = Yes, 1 = No

        # Feedback message
        self.message = ""
        self.message_timer = 0.0

        # Fonts
        self.font_title = pygame.font.SysFont(None, 36)
        self.font_tab = pygame.font.SysFont(None, 28)
        self.font_item = pygame.font.SysFont(None, 26)
        self.font_desc = pygame.font.SysFont(None, 22)

        # Overlay
        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill(COLOR_SHOP_BG)

        # Confirm overlay
        self.confirm_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.confirm_overlay.fill(COLOR_SHOP_CONFIRM_BG)

    @property
    def money(self):
        return self.overworld.stats.money

    @money.setter
    def money(self, value):
        self.overworld.stats.money = value

    def _get_buy_list(self):
        """Return list of (name, price) for shop stock."""
        result = []
        for name in self.stock_list:
            item = ITEM_REGISTRY.get(name)
            if item:
                result.append((name, item.price))
        return result

    def _get_sell_list(self):
        """Return list of (name, count, sell_price) for player inventory."""
        result = []
        for name, count in sorted(self.overworld.inventory.items.items()):
            if count > 0 and name in ITEM_REGISTRY:
                sell_price = ITEM_REGISTRY[name].price // 2
                result.append((name, count, sell_price))
        return result

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if self.confirming:
            self._handle_confirm_event(event)
            return

        if event.key == pygame.K_ESCAPE:
            save_game(self.overworld)
            self.game.pop_state()
        elif event.key == pygame.K_LEFT:
            if self.tab != self.TAB_BUY:
                self.tab = self.TAB_BUY
                self.cursor = 0
                self.scroll_offset = 0
        elif event.key == pygame.K_RIGHT:
            if self.tab != self.TAB_SELL:
                self.tab = self.TAB_SELL
                self.cursor = 0
                self.scroll_offset = 0
        elif event.key == pygame.K_UP:
            items = self._current_items()
            if items:
                self.cursor = (self.cursor - 1) % len(items)
                self._ensure_visible()
        elif event.key == pygame.K_DOWN:
            items = self._current_items()
            if items:
                self.cursor = (self.cursor + 1) % len(items)
                self._ensure_visible()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.tab == self.TAB_BUY:
                self._try_buy()
            else:
                self._try_sell()

    def _handle_confirm_event(self, event):
        if event.key == pygame.K_LEFT or event.key == pygame.K_UP:
            self.confirm_cursor = 0
        elif event.key == pygame.K_RIGHT or event.key == pygame.K_DOWN:
            self.confirm_cursor = 1
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.confirm_cursor == 0:  # Yes
                self._execute_buy(self.confirm_item)
            self.confirming = False
            self.confirm_item = None
        elif event.key == pygame.K_ESCAPE:
            self.confirming = False
            self.confirm_item = None

    def _current_items(self):
        if self.tab == self.TAB_BUY:
            return self._get_buy_list()
        return self._get_sell_list()

    def _ensure_visible(self):
        if self.cursor < self.scroll_offset:
            self.scroll_offset = self.cursor
        elif self.cursor >= self.scroll_offset + self.max_visible:
            self.scroll_offset = self.cursor - self.max_visible + 1

    def _try_buy(self):
        items = self._get_buy_list()
        if not items:
            return
        name, price = items[self.cursor]
        if self.money < price:
            self.message = "Not enough Scrap!"
            self.message_timer = 1.5
            return
        # Open confirmation prompt
        self.confirming = True
        self.confirm_item = name
        self.confirm_cursor = 0

    def _execute_buy(self, item_name):
        item = ITEM_REGISTRY.get(item_name)
        if not item:
            return
        if self.money < item.price:
            self.message = "Not enough Scrap!"
            self.message_timer = 1.5
            return
        self.money -= item.price
        self.overworld.inventory.add(item_name)
        self.game.audio.play_sfx("pickup")
        self.message = f"Bought {item_name}!"
        self.message_timer = 1.5

    def _try_sell(self):
        items = self._get_sell_list()
        if not items:
            return
        name, count, sell_price = items[self.cursor]
        if sell_price <= 0:
            self.message = "Worthless!"
            self.message_timer = 1.5
            return
        # Unequip if currently equipped
        equipment = getattr(self.overworld, "equipment", None)
        if equipment and equipment.is_equipped(name):
            item = ITEM_REGISTRY.get(name)
            if item and item.slot:
                equipment.unequip(item.slot)
        self.overworld.inventory.remove(name)
        self.money += sell_price
        self.game.audio.play_sfx("pickup")
        self.message = f"Sold {name} for {sell_price} Scrap!"
        self.message_timer = 1.5
        # Adjust cursor if items depleted
        new_items = self._get_sell_list()
        if self.cursor >= len(new_items) and new_items:
            self.cursor = len(new_items) - 1
            self._ensure_visible()
        elif not new_items:
            self.cursor = 0
            self.scroll_offset = 0

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

    def draw(self, screen):
        screen.blit(self.overlay, (0, 0))

        # Title
        title = self.font_title.render("SHOP", True, (255, 255, 255))
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 20))

        # Scrap balance (top right)
        balance = self.font_tab.render(f"Scrap: {self.money}", True, COLOR_MONEY_TEXT)
        screen.blit(balance, (SCREEN_WIDTH - balance.get_width() - 20, 24))

        # Tabs
        tab_y = 56
        buy_color = COLOR_SHOP_TAB_ACTIVE if self.tab == self.TAB_BUY else COLOR_SHOP_TAB_INACTIVE
        sell_color = COLOR_SHOP_TAB_ACTIVE if self.tab == self.TAB_SELL else COLOR_SHOP_TAB_INACTIVE
        buy_label = self.font_tab.render("[< Buy]", True, buy_color)
        sell_label = self.font_tab.render("[Sell >]", True, sell_color)
        screen.blit(buy_label, (SCREEN_WIDTH // 2 - buy_label.get_width() - 20, tab_y))
        screen.blit(sell_label, (SCREEN_WIDTH // 2 + 20, tab_y))

        # Item list
        list_x = 80
        list_y = 90
        row_height = 30

        if self.tab == self.TAB_BUY:
            self._draw_buy_list(screen, list_x, list_y, row_height)
        else:
            self._draw_sell_list(screen, list_x, list_y, row_height)

        # Feedback message
        if self.message:
            msg = self.font_item.render(self.message, True, (100, 255, 100))
            screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, SCREEN_HEIGHT - 50))

        # Controls hint
        hint = self.font_desc.render("[ESC] Close   [LEFT/RIGHT] Tab   [ENTER] Select", True, (120, 120, 120))
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 20))

        # Confirmation overlay
        if self.confirming:
            self._draw_confirm(screen)

    def _draw_buy_list(self, screen, list_x, list_y, row_height):
        items = self._get_buy_list()
        if not items:
            empty = self.font_item.render("Nothing for sale.", True, (160, 160, 160))
            screen.blit(empty, (SCREEN_WIDTH // 2 - empty.get_width() // 2, list_y + 20))
            return

        visible = items[self.scroll_offset: self.scroll_offset + self.max_visible]
        for i, (name, price) in enumerate(visible):
            abs_index = self.scroll_offset + i
            is_selected = abs_index == self.cursor
            can_afford = self.money >= price

            if is_selected:
                color = COLOR_ITEM_HIGHLIGHT
            elif can_afford:
                color = COLOR_SHOP_AFFORDABLE
            else:
                color = COLOR_SHOP_UNAFFORDABLE

            prefix = "> " if is_selected else "  "
            text = self.font_item.render(f"{prefix}{name}", True, color)
            screen.blit(text, (list_x, list_y + i * row_height))

            price_text = self.font_item.render(f"{price} Scrap", True, color)
            screen.blit(price_text, (SCREEN_WIDTH - price_text.get_width() - 80, list_y + i * row_height))

        self._draw_scroll_indicators(screen, items, list_x, list_y, row_height)
        self._draw_item_description(screen, items[self.cursor][0] if self.cursor < len(items) else None)

    def _draw_sell_list(self, screen, list_x, list_y, row_height):
        items = self._get_sell_list()
        if not items:
            empty = self.font_item.render("Nothing to sell.", True, (160, 160, 160))
            screen.blit(empty, (SCREEN_WIDTH // 2 - empty.get_width() // 2, list_y + 20))
            return

        equipment = getattr(self.overworld, "equipment", None)
        visible = items[self.scroll_offset: self.scroll_offset + self.max_visible]
        for i, (name, count, sell_price) in enumerate(visible):
            abs_index = self.scroll_offset + i
            is_selected = abs_index == self.cursor

            color = COLOR_ITEM_HIGHLIGHT if is_selected else COLOR_SHOP_AFFORDABLE
            prefix = "> " if is_selected else "  "
            equipped_tag = " [E]" if equipment and equipment.is_equipped(name) else ""
            text = self.font_item.render(f"{prefix}{name}{equipped_tag} x{count}", True, color)
            screen.blit(text, (list_x, list_y + i * row_height))

            price_text = self.font_item.render(f"+{sell_price} Scrap", True, color)
            screen.blit(price_text, (SCREEN_WIDTH - price_text.get_width() - 80, list_y + i * row_height))

        self._draw_scroll_indicators(screen, items, list_x, list_y, row_height)
        self._draw_item_description(screen, items[self.cursor][0] if self.cursor < len(items) else None)

    def _draw_scroll_indicators(self, screen, items, list_x, list_y, row_height):
        if self.scroll_offset > 0:
            up_arrow = self.font_desc.render("^ more ^", True, (160, 160, 160))
            screen.blit(up_arrow, (list_x, list_y - 18))
        if self.scroll_offset + self.max_visible < len(items):
            down_arrow = self.font_desc.render("v more v", True, (160, 160, 160))
            screen.blit(down_arrow, (list_x, list_y + self.max_visible * row_height + 4))

    def _draw_item_description(self, screen, item_name):
        if item_name:
            item = ITEM_REGISTRY.get(item_name)
            if item:
                desc_text = item.description
                equipment = getattr(self.overworld, "equipment", None)
                if item.item_type == "equipment" and equipment and equipment.is_equipped(item_name):
                    desc_text += "  [EQUIPPED]"
                desc = self.font_desc.render(desc_text, True, (180, 180, 180))
                screen.blit(desc, (80, SCREEN_HEIGHT - 80))

    def _draw_confirm(self, screen):
        screen.blit(self.confirm_overlay, (0, 0))

        item = ITEM_REGISTRY.get(self.confirm_item)
        if not item:
            return

        # Confirmation box
        box_w, box_h = 320, 120
        box_x = SCREEN_WIDTH // 2 - box_w // 2
        box_y = SCREEN_HEIGHT // 2 - box_h // 2
        pygame.draw.rect(screen, (30, 30, 50), (box_x, box_y, box_w, box_h))
        pygame.draw.rect(screen, (180, 180, 180), (box_x, box_y, box_w, box_h), 2)

        prompt = self.font_item.render(f"Buy {item.name} for {item.price} Scrap?", True, (255, 255, 255))
        screen.blit(prompt, (box_x + box_w // 2 - prompt.get_width() // 2, box_y + 20))

        # Yes / No
        yes_color = COLOR_ITEM_HIGHLIGHT if self.confirm_cursor == 0 else (180, 180, 180)
        no_color = COLOR_ITEM_HIGHLIGHT if self.confirm_cursor == 1 else (180, 180, 180)
        yes_text = self.font_tab.render("Yes", True, yes_color)
        no_text = self.font_tab.render("No", True, no_color)
        btn_y = box_y + 70
        screen.blit(yes_text, (box_x + box_w // 3 - yes_text.get_width() // 2, btn_y))
        screen.blit(no_text, (box_x + 2 * box_w // 3 - no_text.get_width() // 2, btn_y))
