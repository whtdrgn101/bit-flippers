"""Tile-based event/trigger system for chests, signs, traps, switches, etc."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TileEvent:
    """A single event placed on a map tile."""
    x: int
    y: int
    event_type: str        # "chest", "sign", "trap", "damage_zone", "custom"
    properties: dict       # type-specific data (item, text_key, damage, etc.)
    once: bool = True      # one-time event (persisted as "triggered")


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

    def on_step(self, x: int, y: int) -> TileEvent | None:
        """Check for step-on triggers (traps, damage zones). Returns event or None."""
        ev = self._find_event(x, y)
        if ev is None:
            return None
        if ev.event_type in ("trap", "damage_zone"):
            return ev
        return None

    def on_interact(self, x: int, y: int) -> TileEvent | None:
        """Check for interact triggers (chests, signs). Returns event or None."""
        ev = self._find_event(x, y)
        if ev is None:
            return None
        if ev.event_type in ("chest", "sign", "custom"):
            return ev
        return None

    def mark_triggered(self, x: int, y: int) -> None:
        """Mark an event as triggered (for one-time events)."""
        self.triggered.add((x, y))

    def restore_triggered(self, triggered_set: set[tuple[int, int]]) -> None:
        """Restore triggered set from persistence."""
        self.triggered = set(triggered_set)
