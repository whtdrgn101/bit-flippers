"""Quest log UI showing active, complete, and available quests."""
import pygame
from bit_flippers.fonts import get_font
from bit_flippers.settings import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    COLOR_QUEST_ACTIVE,
    COLOR_QUEST_COMPLETE,
    COLOR_QUEST_AVAILABLE,
)
from bit_flippers.quests import QUEST_REGISTRY


class QuestLogState:
    def __init__(self, game, player_quests):
        self.game = game
        self.player_quests = player_quests
        self.cursor = 0

        self.font_title = get_font(36)
        self.font_quest = get_font(26)
        self.font_detail = get_font(22)
        self.font_hint = get_font(20)

        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((10, 10, 20, 220))

        self._rebuild_list()

    def _rebuild_list(self):
        """Build the sorted quest list: complete first, then active, then available, then done."""
        all_quests = self.player_quests.get_all_quests()
        order = {"complete": 0, "active": 1, "available": 2, "done": 3}
        self.quest_list = sorted(all_quests, key=lambda q: order.get(q[1], 9))
        if self.quest_list and self.cursor >= len(self.quest_list):
            self.cursor = len(self.quest_list) - 1

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            self.game.pop_state()
        elif event.key == pygame.K_UP and self.quest_list:
            self.cursor = (self.cursor - 1) % len(self.quest_list)
        elif event.key == pygame.K_DOWN and self.quest_list:
            self.cursor = (self.cursor + 1) % len(self.quest_list)

    def update(self, dt):
        pass

    def draw(self, screen):
        screen.blit(self.overlay, (0, 0))

        # Title
        title = self.font_title.render("QUEST LOG", True, (255, 255, 255))
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 20))

        if not self.quest_list:
            empty = self.font_quest.render("No quests yet. Talk to NPCs!", True, (160, 160, 160))
            screen.blit(empty, (SCREEN_WIDTH // 2 - empty.get_width() // 2, 80))
            hint = self.font_hint.render("[ESC] Close", True, (120, 120, 120))
            screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 30))
            return

        # Quest list on left side
        list_x = 30
        list_y = 60
        row_h = 28

        for i, (qid, state) in enumerate(self.quest_list):
            qdef = QUEST_REGISTRY[qid]
            is_selected = i == self.cursor

            if state == "complete":
                color = COLOR_QUEST_COMPLETE
                prefix = "[!] "
            elif state == "active":
                color = COLOR_QUEST_ACTIVE
                prefix = "    "
            elif state == "available":
                color = COLOR_QUEST_AVAILABLE
                prefix = "[?] "
            else:  # done
                color = (100, 100, 100)
                prefix = "    "

            if is_selected:
                # Draw selection highlight
                sel_rect = pygame.Rect(list_x - 4, list_y + i * row_h - 2, 260, row_h)
                pygame.draw.rect(screen, (40, 40, 60), sel_rect)
                pygame.draw.rect(screen, color, sel_rect, 1)

            label = f"{prefix}{qdef.name}"
            if state == "done":
                label += " (Done)"
            text = self.font_quest.render(label, True, color)
            screen.blit(text, (list_x, list_y + i * row_h))

        # Detail panel on right side for selected quest
        if self.quest_list:
            qid, state = self.quest_list[self.cursor]
            qdef = QUEST_REGISTRY[qid]
            detail_x = 310
            detail_y = 60

            # Quest name
            name_surf = self.font_quest.render(qdef.name, True, (255, 255, 255))
            screen.blit(name_surf, (detail_x, detail_y))
            detail_y += 30

            # State label
            state_labels = {
                "available": "Available",
                "active": "In Progress",
                "complete": "Ready to Turn In!",
                "done": "Completed",
            }
            state_color = {
                "available": COLOR_QUEST_AVAILABLE,
                "active": COLOR_QUEST_ACTIVE,
                "complete": COLOR_QUEST_COMPLETE,
                "done": (100, 100, 100),
            }
            state_surf = self.font_detail.render(
                state_labels.get(state, state), True, state_color.get(state, (200, 200, 200))
            )
            screen.blit(state_surf, (detail_x, detail_y))
            detail_y += 24

            # Giver
            giver_surf = self.font_detail.render(f"From: {qdef.giver_npc}", True, (180, 180, 180))
            screen.blit(giver_surf, (detail_x, detail_y))
            detail_y += 22

            # Description (word wrap)
            detail_y += 6
            self._draw_wrapped(screen, qdef.description, detail_x, detail_y, 300, (200, 200, 200))
            detail_y += 50

            # Objectives
            objs = self.player_quests.objectives.get(qid, [])
            if state in ("active", "complete") and objs:
                obj_header = self.font_detail.render("Objectives:", True, (220, 220, 220))
                screen.blit(obj_header, (detail_x, detail_y))
                detail_y += 22
                for obj in objs:
                    done = obj.current >= obj.required
                    check = "[x]" if done else "[ ]"
                    obj_color = (100, 200, 100) if done else (180, 180, 180)
                    type_labels = {"kill": "Defeat", "fetch": "Collect", "visit": "Visit"}
                    verb = type_labels.get(obj.obj_type, obj.obj_type)
                    obj_text = f"  {check} {verb} {obj.target}: {obj.current}/{obj.required}"
                    obj_surf = self.font_detail.render(obj_text, True, obj_color)
                    screen.blit(obj_surf, (detail_x, detail_y))
                    detail_y += 20
            elif state == "available":
                # Show objective templates from quest def
                obj_header = self.font_detail.render("Objectives:", True, (220, 220, 220))
                screen.blit(obj_header, (detail_x, detail_y))
                detail_y += 22
                for o in qdef.objectives:
                    type_labels = {"kill": "Defeat", "fetch": "Collect", "visit": "Visit"}
                    verb = type_labels.get(o["obj_type"], o["obj_type"])
                    obj_text = f"  [ ] {verb} {o['target']}: 0/{o['required']}"
                    obj_surf = self.font_detail.render(obj_text, True, (140, 140, 140))
                    screen.blit(obj_surf, (detail_x, detail_y))
                    detail_y += 20

            # Rewards
            detail_y += 8
            rewards = qdef.rewards
            reward_parts = []
            if rewards.get("scrap"):
                reward_parts.append(f"{rewards['scrap']} Scrap")
            if rewards.get("xp"):
                reward_parts.append(f"{rewards['xp']} XP")
            if rewards.get("items"):
                for name, count in rewards["items"].items():
                    reward_parts.append(f"{count}x {name}")
            if rewards.get("equipment"):
                for name in rewards["equipment"]:
                    reward_parts.append(name)
            if rewards.get("skills"):
                reward_parts.append("New Skill")
            if reward_parts:
                rew_header = self.font_detail.render("Rewards:", True, (220, 200, 100))
                screen.blit(rew_header, (detail_x, detail_y))
                detail_y += 20
                rew_text = self.font_detail.render("  " + ", ".join(reward_parts), True, (200, 180, 80))
                screen.blit(rew_text, (detail_x, detail_y))

        # Controls hint
        hint = self.font_hint.render(
            "[UP/DOWN] Navigate   [ESC] Close", True, (120, 120, 120)
        )
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 30))

    def _draw_wrapped(self, screen, text, x, y, max_width, color):
        """Simple word-wrap text rendering."""
        words = text.split()
        line = ""
        for word in words:
            test = f"{line} {word}".strip()
            surf = self.font_detail.render(test, True, color)
            if surf.get_width() > max_width and line:
                screen.blit(self.font_detail.render(line, True, color), (x, y))
                y += 18
                line = word
            else:
                line = test
        if line:
            screen.blit(self.font_detail.render(line, True, color), (x, y))
