"""Status effect management for combat — extracted from CombatState."""

from bit_flippers.combat import StatusEffect
from bit_flippers.player_stats import calc_debuff_duration


class StatusEffectManager:
    """Tracks and ticks status effects for both player and enemy in combat."""

    def __init__(self):
        self.player_statuses: list[StatusEffect] = []
        self.enemy_statuses: list[StatusEffect] = []
        self.burn_atk_reduction: int = 0

    def has_status(self, target: str, name: str) -> bool:
        """Check if *target* ('player' or 'enemy') has a named status."""
        statuses = self.player_statuses if target == "player" else self.enemy_statuses
        return any(s.name == name for s in statuses)

    def apply_status(self, target: str, effect_name: str, constitution: int = 0,
                     player_entity=None, enemy_entity=None) -> None:
        """Apply (or refresh) a status effect on *target*.

        *constitution* is the player's CON stat used to shorten debuff duration.
        *player_entity* / *enemy_entity* are CombatEntity refs for ATK adjustments (Burn).
        """
        durations = {"Poison": 3, "Stun": 1, "Burn": 3, "Despondent": 3}
        duration = durations.get(effect_name, 3)

        if target == "player":
            duration = calc_debuff_duration(duration, constitution)

        statuses = self.player_statuses if target == "player" else self.enemy_statuses

        # Refresh if already present
        for s in statuses:
            if s.name == effect_name:
                s.turns_remaining = duration
                return

        statuses.append(StatusEffect(name=effect_name, turns_remaining=duration))

        # Burn: reduce ATK by 2
        if effect_name == "Burn":
            if target == "player" and player_entity is not None:
                self.burn_atk_reduction = 2
                player_entity.attack = max(0, player_entity.attack - 2)
            elif target == "enemy" and enemy_entity is not None:
                enemy_entity.attack = max(0, enemy_entity.attack - 2)

    def tick(self, player_entity, enemy_entity, enemy_base_attack: int) -> list[str]:
        """Process status effects at end of turn. Returns messages."""
        messages: list[str] = []

        # --- Player statuses ---
        expired_player: list[str] = []
        for s in self.player_statuses:
            if s.name == "Poison":
                player_entity.hp = max(0, player_entity.hp - 2)
                messages.append("Poison dealt 2 damage!")
            elif s.name == "Burn":
                player_entity.hp = max(0, player_entity.hp - 1)
                messages.append("Burn dealt 1 damage!")

            s.turns_remaining -= 1
            if s.turns_remaining <= 0:
                expired_player.append(s.name)

        for name in expired_player:
            self.player_statuses = [s for s in self.player_statuses if s.name != name]
            if name == "Burn":
                player_entity.attack += self.burn_atk_reduction
                self.burn_atk_reduction = 0
            messages.append(f"{name} wore off!")

        # --- Enemy statuses ---
        expired_enemy: list[str] = []
        for s in self.enemy_statuses:
            if s.name == "Poison":
                enemy_entity.hp = max(0, enemy_entity.hp - 2)
                messages.append(f"{enemy_entity.name} took 2 poison damage!")
            elif s.name == "Burn":
                enemy_entity.hp = max(0, enemy_entity.hp - 1)
                messages.append(f"{enemy_entity.name} took 1 burn damage!")

            s.turns_remaining -= 1
            if s.turns_remaining <= 0:
                expired_enemy.append(s.name)

        for name in expired_enemy:
            self.enemy_statuses = [s for s in self.enemy_statuses if s.name != name]
            if name == "Burn":
                enemy_entity.attack = min(enemy_base_attack, enemy_entity.attack + 2)
            messages.append(f"{enemy_entity.name}'s {name} wore off!")

        return messages

    def clear_all(self, player_entity=None) -> int:
        """Clear all statuses. Returns burn_atk to restore to player."""
        burn_atk = self.burn_atk_reduction
        if burn_atk > 0 and player_entity is not None:
            player_entity.attack += burn_atk
        self.burn_atk_reduction = 0
        self.player_statuses.clear()
        self.enemy_statuses.clear()
        return burn_atk

    def remove_player_stun(self) -> bool:
        """Remove Stun from player statuses. Returns True if stun was present."""
        had_stun = any(s.name == "Stun" for s in self.player_statuses)
        self.player_statuses = [s for s in self.player_statuses if s.name != "Stun"]
        return had_stun

    def remove_enemy_stun(self) -> bool:
        """Remove Stun from enemy statuses. Returns True if stun was present."""
        had_stun = any(s.name == "Stun" for s in self.enemy_statuses)
        self.enemy_statuses = [s for s in self.enemy_statuses if s.name != "Stun"]
        return had_stun

    def cure_player(self, player_entity) -> None:
        """Cure all player status effects (used by items/skills)."""
        if self.burn_atk_reduction > 0:
            player_entity.attack += self.burn_atk_reduction
            self.burn_atk_reduction = 0
        self.player_statuses.clear()
