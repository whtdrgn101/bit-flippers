"""Skill tree overlay state for viewing and unlocking skills."""
import pygame
from bit_flippers.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from bit_flippers.skills import SKILL_DEFS, PlayerSkills, _SKILL_LIST
from bit_flippers.save import save_game


# Tree layout constants
NODE_W = 130
NODE_H = 44
COL_SPACING = 160
ROW_SPACING = 80
TREE_X_OFFSET = (SCREEN_WIDTH - COL_SPACING * 2 - NODE_W) // 2
TREE_Y_OFFSET = 65

# Colors
COLOR_UNLOCKED = (60, 180, 80)
COLOR_AVAILABLE = (60, 120, 220)
COLOR_LOCKED = (100, 100, 100)
COLOR_CURSOR = (255, 210, 60)
COLOR_TEXT = (255, 255, 255)
COLOR_DIM = (140, 140, 140)


def _node_rect(row: int, col: int) -> pygame.Rect:
    x = TREE_X_OFFSET + col * COL_SPACING
    y = TREE_Y_OFFSET + row * ROW_SPACING
    return pygame.Rect(x, y, NODE_W, NODE_H)


class SkillTreeState:
    def __init__(self, game, player_skills: PlayerSkills, stats, overworld):
        self.game = game
        self.player_skills = player_skills
        self.stats = stats
        self.overworld = overworld

        # Build ordered list of skills for navigation (row-major order)
        self.skill_order = sorted(_SKILL_LIST, key=lambda s: (s.tree_row, s.tree_col))
        self.cursor = 0

        self.font_title = pygame.font.SysFont(None, 36)
        self.font_node = pygame.font.SysFont(None, 22)
        self.font_desc = pygame.font.SysFont(None, 24)
        self.font_hint = pygame.font.SysFont(None, 22)

        self.overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.overlay.fill((10, 10, 20, 230))

        self.message = ""
        self.message_timer = 0.0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            save_game(self.overworld)
            self.game.pop_state()
        elif event.key == pygame.K_UP:
            self.cursor = (self.cursor - 1) % len(self.skill_order)
        elif event.key == pygame.K_DOWN:
            self.cursor = (self.cursor + 1) % len(self.skill_order)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._try_unlock()

    def _try_unlock(self):
        skill = self.skill_order[self.cursor]
        if skill.skill_id in self.player_skills.unlocked:
            self.message = "Already unlocked!"
            self.message_timer = 1.5
            return
        if self.player_skills.unlock(skill.skill_id):
            self.message = f"Unlocked {skill.name}!"
            self.message_timer = 1.5
        else:
            # Explain why
            if self.player_skills.skill_points < skill.unlock_cost:
                self.message = "Not enough skill points!"
            else:
                self.message = "Prerequisites not met!"
            self.message_timer = 1.5

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""

    def draw(self, screen):
        screen.blit(self.overlay, (0, 0))

        # Title
        title = self.font_title.render("SKILL TREE", True, COLOR_TEXT)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 14))

        # Skill points counter
        pts_color = (100, 180, 255) if self.player_skills.skill_points > 0 else COLOR_DIM
        pts_text = self.font_desc.render(
            f"Skill Points: {self.player_skills.skill_points}", True, pts_color
        )
        screen.blit(pts_text, (SCREEN_WIDTH // 2 - pts_text.get_width() // 2, 48))

        # Draw connecting lines first (behind nodes)
        self._draw_connections(screen)

        # Draw nodes
        for i, skill in enumerate(self.skill_order):
            self._draw_node(screen, skill, is_cursor=i == self.cursor)

        # Draw description panel for selected skill
        selected = self.skill_order[self.cursor]
        self._draw_description(screen, selected)

        # Message
        if self.message:
            msg_surf = self.font_desc.render(self.message, True, (255, 220, 100))
            screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, SCREEN_HEIGHT - 70))

        # Controls hint
        hint = self.font_hint.render(
            "[UP/DOWN] Navigate   [ENTER] Unlock   [ESC] Close", True, (120, 120, 120)
        )
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 24))

    def _draw_connections(self, screen):
        """Draw lines between prerequisite and dependent skill nodes."""
        for skill in _SKILL_LIST:
            for prereq_id in skill.prerequisites:
                prereq = SKILL_DEFS[prereq_id]
                parent_rect = _node_rect(prereq.tree_row, prereq.tree_col)
                child_rect = _node_rect(skill.tree_row, skill.tree_col)
                start = (parent_rect.centerx, parent_rect.bottom)
                end = (child_rect.centerx, child_rect.top)

                # Line color based on unlock status
                if skill.skill_id in self.player_skills.unlocked:
                    color = COLOR_UNLOCKED
                elif prereq_id in self.player_skills.unlocked:
                    color = COLOR_AVAILABLE
                else:
                    color = COLOR_LOCKED

                pygame.draw.line(screen, color, start, end, 2)

    def _draw_node(self, screen, skill, is_cursor: bool):
        rect = _node_rect(skill.tree_row, skill.tree_col)

        # Determine node color
        if skill.skill_id in self.player_skills.unlocked:
            bg_color = (30, 80, 40)
            border_color = COLOR_UNLOCKED
        elif self.player_skills.can_unlock(skill.skill_id):
            bg_color = (25, 50, 90)
            border_color = COLOR_AVAILABLE
        else:
            bg_color = (40, 40, 50)
            border_color = COLOR_LOCKED

        # Draw node background
        bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        bg.fill((*bg_color, 200))
        screen.blit(bg, rect.topleft)

        # Border (gold for cursor)
        if is_cursor:
            pygame.draw.rect(screen, COLOR_CURSOR, rect, 2)
        else:
            pygame.draw.rect(screen, border_color, rect, 1)

        # Skill name
        name_surf = self.font_node.render(skill.name, True, COLOR_TEXT)
        screen.blit(name_surf, (rect.x + rect.width // 2 - name_surf.get_width() // 2, rect.y + 4))

        # SP cost
        sp_text = f"SP: {skill.sp_cost}"
        if skill.skill_id in self.player_skills.unlocked:
            sp_text = "Unlocked"
        sp_surf = self.font_node.render(sp_text, True, COLOR_DIM)
        screen.blit(sp_surf, (rect.x + rect.width // 2 - sp_surf.get_width() // 2, rect.y + 24))

    def _draw_description(self, screen, skill):
        """Draw detail panel at bottom of screen for the selected skill."""
        panel_y = SCREEN_HEIGHT - 120
        desc = skill.description
        cost_label = f"Unlock cost: {skill.unlock_cost} skill point(s)"
        sp_label = f"SP cost: {skill.sp_cost}"

        # Prerequisites
        if skill.prerequisites:
            prereq_names = [SKILL_DEFS[p].name for p in skill.prerequisites]
            prereq_label = f"Requires: {', '.join(prereq_names)}"
        else:
            prereq_label = "No prerequisites"

        desc_surf = self.font_desc.render(desc, True, COLOR_TEXT)
        cost_surf = self.font_hint.render(f"{cost_label}   |   {sp_label}   |   {prereq_label}", True, COLOR_DIM)
        screen.blit(desc_surf, (SCREEN_WIDTH // 2 - desc_surf.get_width() // 2, panel_y))
        screen.blit(cost_surf, (SCREEN_WIDTH // 2 - cost_surf.get_width() // 2, panel_y + 26))
