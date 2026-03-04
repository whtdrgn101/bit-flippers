"""Quest data model, registry, and player quest state tracking."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QuestObjective:
    obj_type: str  # "fetch", "kill", "visit"
    target: str  # item name, enemy name, or map_id
    required: int
    current: int = 0


@dataclass
class QuestDef:
    quest_id: str
    name: str
    giver_npc: str  # NPC name that gives/completes the quest
    description: str
    objectives: list[dict]  # list of {obj_type, target, required} templates
    rewards: dict  # {scrap, xp, items?, skills?, equipment?}
    prerequisite: str | list[str] | None = None  # quest_id(s) that must be "done"
    dialogue_offer: str = ""  # strings.json key
    dialogue_active: str = ""
    dialogue_complete: str = ""
    dialogue_done: str = ""


# ---------------------------------------------------------------------------
# Quest registry — 15 quests
# ---------------------------------------------------------------------------

QUEST_REGISTRY: dict[str, QuestDef] = {}

_QUEST_LIST = [
    QuestDef(
        quest_id="spare_parts",
        name="Spare Parts",
        giver_npc="Old Tinker",
        description="Old Tinker needs scrap metal for repairs. Collect 5 Scrap Metal and bring them back.",
        objectives=[{"obj_type": "fetch", "target": "Scrap Metal", "required": 5}],
        rewards={"scrap": 75, "xp": 30},
        prerequisite=None,
        dialogue_offer="quest_spare_parts_offer",
        dialogue_active="quest_spare_parts_active",
        dialogue_complete="quest_spare_parts_complete",
        dialogue_done="quest_spare_parts_done",
    ),
    QuestDef(
        quest_id="pest_control",
        name="Pest Control",
        giver_npc="Scout",
        description="The Scout reports Scrap Rats infesting the area. Defeat 4 of them to clear the sector.",
        objectives=[{"obj_type": "kill", "target": "Scrap Rat", "required": 4}],
        rewards={"scrap": 100, "xp": 50, "items": {"Repair Kit": 2}},
        prerequisite=None,
        dialogue_offer="quest_pest_control_offer",
        dialogue_active="quest_pest_control_active",
        dialogue_complete="quest_pest_control_complete",
        dialogue_done="quest_pest_control_done",
    ),
    QuestDef(
        quest_id="deep_recon",
        name="Deep Reconnaissance",
        giver_npc="Drifter",
        description="The Drifter needs intel on the Scrap Cave. Explore it and deal with the Volt Wraiths lurking inside.",
        objectives=[
            {"obj_type": "visit", "target": "scrap_cave", "required": 1},
            {"obj_type": "kill", "target": "Volt Wraith", "required": 2},
        ],
        rewards={"scrap": 150, "xp": 80, "equipment": ["Silver Pulse Blade"]},
        prerequisite=None,
        dialogue_offer="quest_deep_recon_offer",
        dialogue_active="quest_deep_recon_active",
        dialogue_complete="quest_deep_recon_complete",
        dialogue_done="quest_deep_recon_done",
    ),
    QuestDef(
        quest_id="circuit_restore",
        name="Circuit Restoration",
        giver_npc="Sparks",
        description="Sparks needs Voltage Spikes to restore damaged circuits. Bring 3 Voltage Spikes.",
        objectives=[{"obj_type": "fetch", "target": "Voltage Spike", "required": 3}],
        rewards={"scrap": 100, "xp": 60, "skills": ["scrap_leech"]},
        prerequisite="spare_parts",
        dialogue_offer="quest_circuit_restore_offer",
        dialogue_active="quest_circuit_restore_active",
        dialogue_complete="quest_circuit_restore_complete",
        dialogue_done="quest_circuit_restore_done",
    ),
    QuestDef(
        quest_id="factory_sweep",
        name="Factory Sweep",
        giver_npc="Engineer",
        description="The Engineer needs the factory cleared. Defeat 3 Plasma Hounds prowling the assembly lines.",
        objectives=[{"obj_type": "kill", "target": "Plasma Hound", "required": 3}],
        rewards={"scrap": 200, "xp": 100, "equipment": ["Titanium Aegis Plate"]},
        prerequisite=None,
        dialogue_offer="quest_factory_sweep_offer",
        dialogue_active="quest_factory_sweep_active",
        dialogue_complete="quest_factory_sweep_complete",
        dialogue_done="quest_factory_sweep_done",
    ),
    # --- Comm Tower chain (Operator NPC) ---
    QuestDef(
        quest_id="comm_unlock",
        name="Signal Interference",
        giver_npc="Operator",
        description="The Operator has detected strange signals from the Comm Tower. Investigate the source.",
        objectives=[{"obj_type": "visit", "target": "comm_tower", "required": 1}],
        rewards={"scrap": 150, "xp": 80},
        prerequisite="factory_sweep",
        dialogue_offer="quest_comm_unlock_offer",
        dialogue_active="quest_comm_unlock_active",
        dialogue_complete="quest_comm_unlock_complete",
        dialogue_done="quest_comm_unlock_done",
    ),
    QuestDef(
        quest_id="comm_boss",
        name="Override Protocol",
        giver_npc="Operator",
        description="A Comm Overlord controls the tower's systems. Defeat it to restore communications.",
        objectives=[{"obj_type": "kill", "target": "Comm Overlord", "required": 1}],
        rewards={"scrap": 300, "xp": 150, "items": {"Repair Kit": 3}},
        prerequisite="comm_unlock",
        dialogue_offer="quest_comm_boss_offer",
        dialogue_active="quest_comm_boss_active",
        dialogue_complete="quest_comm_boss_complete",
        dialogue_done="quest_comm_boss_done",
    ),
    QuestDef(
        quest_id="comm_sweep",
        name="Static Purge",
        giver_npc="Operator",
        description="Residual drones still patrol the tower. Clear out 5 Static Drones.",
        objectives=[{"obj_type": "kill", "target": "Static Drone", "required": 5}],
        rewards={"scrap": 250, "xp": 130},
        prerequisite="comm_boss",
        dialogue_offer="quest_comm_sweep_offer",
        dialogue_active="quest_comm_sweep_active",
        dialogue_complete="quest_comm_sweep_complete",
        dialogue_done="quest_comm_sweep_done",
    ),
    # --- Slag Pits chain (Smelter NPC) ---
    QuestDef(
        quest_id="slag_unlock",
        name="Thermal Readings",
        giver_npc="Smelter",
        description="The Smelter needs thermal data from the Slag Pits. Head there and take readings.",
        objectives=[{"obj_type": "visit", "target": "slag_pits", "required": 1}],
        rewards={"scrap": 200, "xp": 100},
        prerequisite="factory_sweep",
        dialogue_offer="quest_slag_unlock_offer",
        dialogue_active="quest_slag_unlock_active",
        dialogue_complete="quest_slag_unlock_complete",
        dialogue_done="quest_slag_unlock_done",
    ),
    QuestDef(
        quest_id="slag_boss",
        name="Heart of the Furnace",
        giver_npc="Smelter",
        description="A massive Slag Titan lurks in the deepest pit. Destroy it to stop the molten overflow.",
        objectives=[{"obj_type": "kill", "target": "Slag Titan", "required": 1}],
        rewards={"scrap": 350, "xp": 175, "items": {"Voltage Spike": 2}},
        prerequisite="slag_unlock",
        dialogue_offer="quest_slag_boss_offer",
        dialogue_active="quest_slag_boss_active",
        dialogue_complete="quest_slag_boss_complete",
        dialogue_done="quest_slag_boss_done",
    ),
    QuestDef(
        quest_id="slag_sweep",
        name="Cooling the Pits",
        giver_npc="Smelter",
        description="Slag Crawlers are still overheating the vents. Eliminate 5 of them.",
        objectives=[{"obj_type": "kill", "target": "Slag Crawler", "required": 5}],
        rewards={"scrap": 300, "xp": 160},
        prerequisite="slag_boss",
        dialogue_offer="quest_slag_sweep_offer",
        dialogue_active="quest_slag_sweep_active",
        dialogue_complete="quest_slag_sweep_complete",
        dialogue_done="quest_slag_sweep_done",
    ),
    # --- Data Vault chain (Drifter NPC, reused) ---
    QuestDef(
        quest_id="vault_unlock",
        name="Deep Archive",
        giver_npc="Drifter",
        description="With the Comm Tower and Slag Pits secured, the path to the Data Vault is clear. Explore it.",
        objectives=[{"obj_type": "visit", "target": "data_vault", "required": 1}],
        rewards={"scrap": 250, "xp": 120},
        prerequisite=["comm_boss", "slag_boss"],
        dialogue_offer="quest_vault_unlock_offer",
        dialogue_active="quest_vault_unlock_active",
        dialogue_complete="quest_vault_unlock_complete",
        dialogue_done="quest_vault_unlock_done",
    ),
    QuestDef(
        quest_id="vault_boss",
        name="System Overwrite",
        giver_npc="Drifter",
        description="The Archive Core guards the vault's deepest secrets. Shut it down permanently.",
        objectives=[{"obj_type": "kill", "target": "Archive Core", "required": 1}],
        rewards={"scrap": 500, "xp": 250},
        prerequisite="vault_unlock",
        dialogue_offer="quest_vault_boss_offer",
        dialogue_active="quest_vault_boss_active",
        dialogue_complete="quest_vault_boss_complete",
        dialogue_done="quest_vault_boss_done",
    ),
    QuestDef(
        quest_id="vault_sweep",
        name="Data Recovery",
        giver_npc="Drifter",
        description="Firewall Sentinels still guard corrupted data nodes. Destroy 4 of them to recover the archives.",
        objectives=[{"obj_type": "kill", "target": "Firewall Sentinel", "required": 4}],
        rewards={"scrap": 400, "xp": 200},
        prerequisite="vault_boss",
        dialogue_offer="quest_vault_sweep_offer",
        dialogue_active="quest_vault_sweep_active",
        dialogue_complete="quest_vault_sweep_complete",
        dialogue_done="quest_vault_sweep_done",
    ),
    # --- Final dungeon gate (Old Tinker NPC, reused) ---
    QuestDef(
        quest_id="nexus_gate",
        name="The Core Nexus",
        giver_npc="Old Tinker",
        description="All threats have been neutralized. The Core Nexus awaits. Enter it and destroy the Omega Core.",
        objectives=[
            {"obj_type": "visit", "target": "core_nexus", "required": 1},
            {"obj_type": "kill", "target": "Omega Core", "required": 1},
        ],
        rewards={"scrap": 1000, "xp": 500},
        prerequisite=["comm_boss", "slag_boss", "vault_boss"],
        dialogue_offer="quest_nexus_gate_offer",
        dialogue_active="quest_nexus_gate_active",
        dialogue_complete="quest_nexus_gate_complete",
        dialogue_done="quest_nexus_gate_done",
    ),
]

for _q in _QUEST_LIST:
    QUEST_REGISTRY[_q.quest_id] = _q


# ---------------------------------------------------------------------------
# Player quest state tracker
# ---------------------------------------------------------------------------

class PlayerQuests:
    """Tracks quest states and objective progress for the player."""

    def __init__(self) -> None:
        # quest_id -> state: "available", "active", "complete", "done"
        self.states: dict[str, str] = {}
        # quest_id -> list of QuestObjective
        self.objectives: dict[str, list[QuestObjective]] = {}

    def _check_available(self, quest_id: str) -> bool:
        """Check if a quest's prerequisites are met."""
        qdef = QUEST_REGISTRY.get(quest_id)
        if qdef is None:
            return False
        prereq = qdef.prerequisite
        if prereq is None:
            return True
        if isinstance(prereq, list):
            return all(self.states.get(p) == "done" for p in prereq)
        return self.states.get(prereq) == "done"

    def get_state(self, quest_id: str) -> str | None:
        """Return quest state, auto-promoting to 'available' if prereqs met."""
        if quest_id in self.states:
            return self.states[quest_id]
        if self._check_available(quest_id):
            return "available"
        return None

    def get_npc_quest(self, npc_name: str) -> tuple[str, str] | None:
        """Find the most relevant quest for an NPC.

        Returns (quest_id, state) or None.
        Priority: complete > active > available.
        """
        best = None
        for qid, qdef in QUEST_REGISTRY.items():
            if qdef.giver_npc != npc_name:
                continue
            state = self.get_state(qid)
            if state is None:
                continue
            if state == "complete":
                return (qid, state)
            if state == "active":
                if best is None or best[1] != "complete":
                    best = (qid, state)
            elif state == "available":
                if best is None or best[1] == "done":
                    best = (qid, state)
            elif state == "done":
                if best is None:
                    best = (qid, state)
        return best

    def accept(self, quest_id: str) -> bool:
        """Accept a quest (available -> active). Returns True on success."""
        if self.get_state(quest_id) != "available":
            return False
        qdef = QUEST_REGISTRY[quest_id]
        self.states[quest_id] = "active"
        self.objectives[quest_id] = [
            QuestObjective(
                obj_type=o["obj_type"],
                target=o["target"],
                required=o["required"],
            )
            for o in qdef.objectives
        ]
        return True

    def update_kill(self, enemy_name: str) -> None:
        """Increment kill counts for active quests matching enemy_name."""
        for qid, state in list(self.states.items()):
            if state != "active":
                continue
            for obj in self.objectives.get(qid, []):
                if obj.obj_type == "kill" and obj.target == enemy_name:
                    obj.current = min(obj.current + 1, obj.required)
            self._check_complete(qid)

    def update_visit(self, map_id: str) -> None:
        """Mark visit objectives complete for active quests."""
        for qid, state in list(self.states.items()):
            if state != "active":
                continue
            for obj in self.objectives.get(qid, []):
                if obj.obj_type == "visit" and obj.target == map_id:
                    obj.current = obj.required
            self._check_complete(qid)

    def update_fetch(self, inventory) -> None:
        """Update fetch objectives based on current inventory counts."""
        for qid, state in list(self.states.items()):
            if state != "active":
                continue
            for obj in self.objectives.get(qid, []):
                if obj.obj_type == "fetch":
                    obj.current = min(inventory.get_count(obj.target), obj.required)
            self._check_complete(qid)

    def _check_complete(self, quest_id: str) -> None:
        """Promote quest to 'complete' if all objectives are met."""
        if self.states.get(quest_id) != "active":
            return
        objs = self.objectives.get(quest_id, [])
        if all(o.current >= o.required for o in objs):
            self.states[quest_id] = "complete"

    def claim_rewards(self, quest_id: str, overworld) -> bool:
        """Claim rewards for a completed quest. Returns True on success."""
        if self.states.get(quest_id) != "complete":
            return False
        qdef = QUEST_REGISTRY[quest_id]
        rewards = qdef.rewards

        # Scrap
        overworld.stats.money += rewards.get("scrap", 0)

        # XP (use overworld's grant logic for level-ups)
        xp = rewards.get("xp", 0)
        if xp > 0:
            overworld.stats.xp += xp
            # Trigger level-up checks
            from bit_flippers.settings import BASE_XP
            from bit_flippers.skills import skill_points_for_level
            from bit_flippers.player_stats import points_for_level

            while overworld.stats.xp >= overworld.stats.level * BASE_XP:
                overworld.stats.xp -= overworld.stats.level * BASE_XP
                overworld.stats.level += 1
                overworld.stats.unspent_points += points_for_level(overworld.stats.level)
                overworld.player_skills.skill_points += skill_points_for_level(overworld.stats.level)
                overworld.stats.current_hp = overworld.stats.max_hp
                overworld.stats.current_sp = overworld.stats.max_sp

        # Items
        for item_name, count in rewards.get("items", {}).items():
            overworld.inventory.add(item_name, count)

        # Equipment (add to inventory)
        for item_name in rewards.get("equipment", []):
            overworld.inventory.add(item_name, 1)

        # Skills (unlock directly)
        for skill_id in rewards.get("skills", []):
            overworld.player_skills.unlocked.add(skill_id)

        # Consume fetched items from inventory
        for obj in self.objectives.get(quest_id, []):
            if obj.obj_type == "fetch":
                overworld.inventory.remove(obj.target, obj.required)

        self.states[quest_id] = "done"
        return True

    def has_completable(self) -> bool:
        """Check if any quest is in the 'complete' state."""
        return any(s == "complete" for s in self.states.values())

    def get_all_quests(self) -> list[tuple[str, str]]:
        """Return list of (quest_id, state) for all known/available quests."""
        result = []
        for qid in QUEST_REGISTRY:
            state = self.get_state(qid)
            if state is not None:
                result.append((qid, state))
        return result

    def to_dict(self) -> dict:
        obj_data = {}
        for qid, objs in self.objectives.items():
            obj_data[qid] = [
                {"obj_type": o.obj_type, "target": o.target,
                 "required": o.required, "current": o.current}
                for o in objs
            ]
        return {
            "states": dict(self.states),
            "objectives": obj_data,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PlayerQuests:
        pq = cls()
        pq.states = dict(data.get("states", {}))
        for qid, obj_list in data.get("objectives", {}).items():
            pq.objectives[qid] = [
                QuestObjective(
                    obj_type=o["obj_type"],
                    target=o["target"],
                    required=o["required"],
                    current=o.get("current", 0),
                )
                for o in obj_list
            ]
        return pq
