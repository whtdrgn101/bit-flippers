"""Skill definitions, skill tree, and player skill progression."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SkillDef:
    skill_id: str
    name: str
    description: str
    sp_cost: int
    effect_type: str  # "damage", "heal", "buff_defense", "drain", "debuff_attack", "cure_status"
    base_value: int
    stat_scaling: str  # "intelligence", "strength", "none"
    scaling_factor: float
    tree_row: int
    tree_col: int
    prerequisites: list[str] = field(default_factory=list)
    unlock_cost: int = 1


def calc_skill_effect(skill: SkillDef, stats) -> int:
    """Calculate scaled skill effect value based on player stats."""
    if skill.stat_scaling == "intelligence":
        stat_value = stats.intelligence
    elif skill.stat_scaling == "strength":
        stat_value = stats.strength
    else:
        stat_value = 3  # neutral baseline
    return max(1, int(skill.base_value * (1.0 + (stat_value - 3) * skill.scaling_factor)))


# ---------------------------------------------------------------------------
# Skill registry — 8 skills in a 3-tier tree (two branches converging)
# ---------------------------------------------------------------------------
#
# Tier 0:  [Shrapnel Blast] (col 0)          [Jury-Rig Shield] (col 2)
#                |                                    |
# Tier 1:  [Voltage Surge]   [Scrap Leech]     [Overclock]
#             (col 0)           (col 1)           (col 2)
#                |                 |                 |
# Tier 2:  [Magnet Storm]   [Patchwork Heal]   [EMP Pulse]
#             (col 0)           (col 1)           (col 2)
#                                  |
# Tier 3:                   [System Purge]
#                               (col 1)

SKILL_DEFS: dict[str, SkillDef] = {}

_SKILL_LIST = [
    # Tier 0
    SkillDef(
        skill_id="shrapnel_blast",
        name="Shrapnel Blast",
        description="Hurl scrap shards at the enemy.",
        sp_cost=2,
        effect_type="damage",
        base_value=6,
        stat_scaling="intelligence",
        scaling_factor=0.05,
        tree_row=0,
        tree_col=0,
        prerequisites=[],
        unlock_cost=1,
    ),
    SkillDef(
        skill_id="jury_rig_shield",
        name="Jury-Rig Shield",
        description="Cobble together a makeshift shield.",
        sp_cost=3,
        effect_type="buff_defense",
        base_value=4,
        stat_scaling="intelligence",
        scaling_factor=0.05,
        tree_row=0,
        tree_col=2,
        prerequisites=[],
        unlock_cost=1,
    ),
    # Tier 1
    SkillDef(
        skill_id="voltage_surge",
        name="Voltage Surge",
        description="Channel raw voltage into a powerful strike.",
        sp_cost=4,
        effect_type="damage",
        base_value=10,
        stat_scaling="strength",
        scaling_factor=0.08,
        tree_row=1,
        tree_col=0,
        prerequisites=["shrapnel_blast"],
        unlock_cost=1,
    ),
    SkillDef(
        skill_id="scrap_leech",
        name="Scrap Leech",
        description="Drain energy from the enemy to heal.",
        sp_cost=3,
        effect_type="drain",
        base_value=5,
        stat_scaling="intelligence",
        scaling_factor=0.05,
        tree_row=1,
        tree_col=1,
        prerequisites=["shrapnel_blast"],
        unlock_cost=1,
    ),
    SkillDef(
        skill_id="overclock",
        name="Overclock",
        description="Overload enemy circuits, weakening attacks.",
        sp_cost=3,
        effect_type="debuff_attack",
        base_value=3,
        stat_scaling="intelligence",
        scaling_factor=0.05,
        tree_row=1,
        tree_col=2,
        prerequisites=["jury_rig_shield"],
        unlock_cost=1,
    ),
    # Tier 2
    SkillDef(
        skill_id="magnet_storm",
        name="Magnet Storm",
        description="Unleash a devastating magnetic barrage.",
        sp_cost=5,
        effect_type="damage",
        base_value=16,
        stat_scaling="intelligence",
        scaling_factor=0.05,
        tree_row=2,
        tree_col=0,
        prerequisites=["voltage_surge"],
        unlock_cost=2,
    ),
    SkillDef(
        skill_id="patchwork_heal",
        name="Patchwork Heal",
        description="Mend wounds with salvaged parts.",
        sp_cost=4,
        effect_type="heal",
        base_value=12,
        stat_scaling="intelligence",
        scaling_factor=0.05,
        tree_row=2,
        tree_col=1,
        prerequisites=["scrap_leech"],
        unlock_cost=2,
    ),
    SkillDef(
        skill_id="emp_pulse",
        name="EMP Pulse",
        description="Blast an EMP that cripples enemy ATK and DEF.",
        sp_cost=5,
        effect_type="debuff_attack",
        base_value=2,
        stat_scaling="intelligence",
        scaling_factor=0.05,
        tree_row=2,
        tree_col=2,
        prerequisites=["overclock"],
        unlock_cost=2,
    ),
    # Tier 3
    SkillDef(
        skill_id="system_purge",
        name="System Purge",
        description="Flush corrupted data to clear all status effects.",
        sp_cost=3,
        effect_type="cure_status",
        base_value=0,
        stat_scaling="none",
        scaling_factor=0,
        tree_row=3,
        tree_col=1,
        prerequisites=["patchwork_heal"],
        unlock_cost=2,
    ),
]

for _s in _SKILL_LIST:
    SKILL_DEFS[_s.skill_id] = _s


# ---------------------------------------------------------------------------
# Skill point progression
# ---------------------------------------------------------------------------

def skill_points_for_level(level: int) -> int:
    """Skill points awarded on reaching *level*. 0 at level 1."""
    if level <= 1:
        return 0
    pts = 1
    if level % 5 == 0:
        pts += 1
    return pts


# ---------------------------------------------------------------------------
# Player skill state
# ---------------------------------------------------------------------------

class PlayerSkills:
    """Tracks which skills a player has unlocked and available skill points."""

    def __init__(self) -> None:
        self.unlocked: set[str] = set()
        self.skill_points: int = 0

    def can_unlock(self, skill_id: str) -> bool:
        """Check whether a skill can be unlocked right now."""
        if skill_id in self.unlocked:
            return False
        skill = SKILL_DEFS.get(skill_id)
        if skill is None:
            return False
        if self.skill_points < skill.unlock_cost:
            return False
        for prereq in skill.prerequisites:
            if prereq not in self.unlocked:
                return False
        return True

    def unlock(self, skill_id: str) -> bool:
        """Attempt to unlock a skill. Returns True on success."""
        if not self.can_unlock(skill_id):
            return False
        skill = SKILL_DEFS[skill_id]
        self.skill_points -= skill.unlock_cost
        self.unlocked.add(skill_id)
        return True

    def get_unlocked_skills(self) -> list[SkillDef]:
        """Return list of SkillDef for all unlocked skills."""
        return [SKILL_DEFS[sid] for sid in self.unlocked if sid in SKILL_DEFS]

    def to_dict(self) -> dict:
        return {
            "unlocked": sorted(self.unlocked),
            "skill_points": self.skill_points,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PlayerSkills:
        ps = cls()
        ps.unlocked = set(data.get("unlocked", []))
        ps.skill_points = data.get("skill_points", 0)
        return ps
