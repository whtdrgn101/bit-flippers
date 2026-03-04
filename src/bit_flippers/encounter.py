"""Random encounter management — extracted from OverworldState."""

from __future__ import annotations

import random

from bit_flippers.combat import EnemyData, ENEMY_TYPES
from bit_flippers.settings import MIN_STEPS_BETWEEN_ENCOUNTERS


class EncounterManager:
    """Tracks steps and rolls for random encounters."""

    def __init__(self) -> None:
        self.steps_since_encounter: int = 0
        self._encounter_table: list[str] = []
        self._encounter_chance: float = 0.0

    def configure(self, encounter_table: list[str], encounter_chance: float) -> None:
        """Set the encounter table and chance for the current map."""
        self._encounter_table = encounter_table
        self._encounter_chance = encounter_chance

    def on_step(self) -> EnemyData | None:
        """Increment step count and roll for an encounter.

        Returns EnemyData if an encounter is triggered, else None.
        """
        self.steps_since_encounter += 1
        if (
            self._encounter_table
            and self.steps_since_encounter >= MIN_STEPS_BETWEEN_ENCOUNTERS
            and random.random() < self._encounter_chance
        ):
            self.steps_since_encounter = 0
            return ENEMY_TYPES[random.choice(self._encounter_table)]
        return None

    def reset(self) -> None:
        """Reset step counter (called when combat starts externally)."""
        self.steps_since_encounter = 0
