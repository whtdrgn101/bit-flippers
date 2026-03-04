"""Tile-based event/trigger system for chests, signs, traps, switches, etc."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TileEvent:
    """A single event placed on a map tile."""
    x: int
    y: int
    event_type: str        # "chest", "sign", "trap", "damage_zone", "custom",
                           # "switch", "teleport", "spawn_combat", "heal_zone",
                           # "gate", "scrap_reward"
    properties: dict       # type-specific data (item, text_key, damage, etc.)
    once: bool = True      # one-time event (persisted as "triggered")
    trigger: str = "auto"  # "step", "interact", or "auto" (inferred from type)


# Event types that fire on step
_STEP_TYPES = frozenset({"trap", "damage_zone", "teleport", "heal_zone", "gate"})
# Event types that fire on interact
_INTERACT_TYPES = frozenset({"chest", "sign", "custom", "switch", "scrap_reward"})
# Event types that can be either step or interact
_FLEXIBLE_TYPES = frozenset({"spawn_combat"})


@dataclass
class EventAction:
    """Describes what the overworld should do in response to an event."""
    action_type: str  # "dialogue", "give_item", "damage", "teleport",
                      # "toggle_walkable", "start_combat", "heal", "message",
                      # "block", "give_scrap"
    message: str | None = None
    item_name: str | None = None
    damage: int = 0
    heal_hp: int = 0
    heal_sp: int = 0
    dialogue_lines: list[str] | None = None
    target_x: int = 0
    target_y: int = 0
    enemy_type: str | None = None
    scrap_amount: int = 0
    sfx: str | None = None
    mark_triggered: bool = False


class EventManager:
    """Manages tile-based events for a map."""

    def __init__(self):
        self.events: list[TileEvent] = []
        self.triggered: set[tuple[int, int]] = set()

    def load_events(self, tiled_renderer) -> None:
        """Parse Event objects from a TiledMapRenderer."""
        self.events = tiled_renderer.get_events()
        # Don't reset triggered — caller restores from persistence

    def _find_event(self, x: int, y: int) -> TileEvent | None:
        """Find an untriggered event at (x, y)."""
        for ev in self.events:
            if ev.x == x and ev.y == y:
                if ev.once and (x, y) in self.triggered:
                    continue
                return ev
        return None

    def _is_step_event(self, ev: TileEvent) -> bool:
        if ev.trigger == "step":
            return True
        if ev.trigger == "interact":
            return False
        # Auto-infer from type
        return ev.event_type in _STEP_TYPES or (
            ev.event_type in _FLEXIBLE_TYPES and ev.trigger != "interact"
        )

    def _is_interact_event(self, ev: TileEvent) -> bool:
        if ev.trigger == "interact":
            return True
        if ev.trigger == "step":
            return False
        # Auto-infer from type
        return ev.event_type in _INTERACT_TYPES or (
            ev.event_type in _FLEXIBLE_TYPES and ev.trigger == "interact"
        )

    def on_step(self, x: int, y: int) -> TileEvent | None:
        """Check for step-on triggers. Returns event or None."""
        ev = self._find_event(x, y)
        if ev is None:
            return None
        if self._is_step_event(ev):
            return ev
        return None

    def on_interact(self, x: int, y: int) -> TileEvent | None:
        """Check for interact triggers. Returns event or None."""
        ev = self._find_event(x, y)
        if ev is None:
            return None
        if self._is_interact_event(ev):
            return ev
        return None

    def mark_triggered(self, x: int, y: int) -> None:
        """Mark an event as triggered (for one-time events)."""
        self.triggered.add((x, y))

    def restore_triggered(self, triggered_set: set[tuple[int, int]]) -> None:
        """Restore triggered set from persistence."""
        self.triggered = set(triggered_set)

    # ------------------------------------------------------------------
    # Event execution — returns an EventAction the overworld applies
    # ------------------------------------------------------------------

    def execute(self, event: TileEvent, quest_states: dict[str, str] | None = None,
                inventory=None) -> EventAction | None:
        """Evaluate conditions and produce an EventAction, or None if blocked.

        *quest_states* maps quest_id -> state string (e.g. "active", "done").
        *inventory* is an Inventory instance (for requires_item checks).
        """
        props = event.properties

        # --- Condition checks ---
        req_quest = props.get("requires_quest")
        req_state = props.get("required_state")
        if req_quest and req_state:
            actual = (quest_states or {}).get(req_quest, "unknown")
            if actual != req_state:
                # Gate events show a message when blocked
                if event.event_type == "gate":
                    msg = props.get("message", "The way is blocked.")
                    return EventAction(action_type="block", message=msg)
                return None

        req_item = props.get("requires_item")
        if req_item and inventory is not None:
            if not inventory.has(req_item):
                if event.event_type == "gate":
                    msg = props.get("message", f"Requires {req_item}.")
                    return EventAction(action_type="block", message=msg)
                return None

        sfx = props.get("sfx")

        # --- Type dispatch ---
        if event.event_type == "chest":
            item_name = props.get("item", "Scrap Metal")
            return EventAction(
                action_type="give_item",
                item_name=item_name,
                message=f"Found {item_name}!",
                sfx=sfx or "pickup",
                mark_triggered=event.once,
            )

        if event.event_type == "sign":
            from bit_flippers.strings import get_npc_dialogue
            text_key = props.get("text_key", "")
            lines = get_npc_dialogue(text_key)
            if lines:
                return EventAction(
                    action_type="dialogue",
                    dialogue_lines=lines,
                    sfx=sfx,
                    mark_triggered=event.once,
                )
            return None

        if event.event_type in ("trap", "damage_zone"):
            damage = int(props.get("damage", 1))
            msg = props.get("message", f"Took {damage} damage!")
            return EventAction(
                action_type="damage",
                damage=damage,
                message=msg,
                sfx=sfx,
                mark_triggered=event.once,
            )

        if event.event_type == "custom":
            msg = props.get("message", "Something happened...")
            return EventAction(
                action_type="message",
                message=msg,
                sfx=sfx,
                mark_triggered=event.once,
            )

        if event.event_type == "switch":
            tx = int(props.get("target_x", 0))
            ty = int(props.get("target_y", 0))
            msg = props.get("message", "A switch was flipped!")
            return EventAction(
                action_type="toggle_walkable",
                target_x=tx,
                target_y=ty,
                message=msg,
                sfx=sfx or "pickup",
                mark_triggered=event.once,
            )

        if event.event_type == "teleport":
            tx = int(props.get("target_x", 0))
            ty = int(props.get("target_y", 0))
            return EventAction(
                action_type="teleport",
                target_x=tx,
                target_y=ty,
                sfx=sfx,
                mark_triggered=event.once,
            )

        if event.event_type == "spawn_combat":
            enemy_type = props.get("enemy_type", "")
            return EventAction(
                action_type="start_combat",
                enemy_type=enemy_type,
                sfx=sfx,
                mark_triggered=event.once,
            )

        if event.event_type == "heal_zone":
            hp = int(props.get("heal_hp", 0))
            sp = int(props.get("heal_sp", 0))
            msg = props.get("message", "You feel restored.")
            return EventAction(
                action_type="heal",
                heal_hp=hp,
                heal_sp=sp,
                message=msg,
                sfx=sfx,
                mark_triggered=event.once,
            )

        if event.event_type == "gate":
            # If we got here, conditions passed — gate is open
            return None

        if event.event_type == "scrap_reward":
            amount = int(props.get("amount", 0))
            item_name = props.get("item")
            msg = props.get("message", "")
            parts = []
            if amount:
                parts.append(f"Received {amount} scrap!")
            if item_name:
                parts.append(f"Found {item_name}!")
            if not msg:
                msg = " ".join(parts) or "Nothing happened."
            return EventAction(
                action_type="give_scrap",
                scrap_amount=amount,
                item_name=item_name,
                message=msg,
                sfx=sfx or "pickup",
                mark_triggered=event.once,
            )

        # Unknown type — treat as custom message
        msg = props.get("message", "Something happened...")
        return EventAction(
            action_type="message",
            message=msg,
            sfx=sfx,
            mark_triggered=event.once,
        )
