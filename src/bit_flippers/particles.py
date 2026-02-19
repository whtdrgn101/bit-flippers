"""Combat particle system with per-skill presets and screen shake."""
from __future__ import annotations

import math
import random


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "lifetime", "max_lifetime", "color", "size")

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 lifetime: float, color: tuple[int, ...], size: float = 3.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.color = color
        self.size = size

    @property
    def alive(self) -> bool:
        return self.lifetime > 0

    @property
    def alpha(self) -> float:
        return max(0.0, self.lifetime / self.max_lifetime)

    def update(self, dt: float):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt


def draw_particles(screen, particles: list[Particle]):
    """Draw all living particles with alpha fade."""
    import pygame
    for p in particles:
        if not p.alive:
            continue
        a = p.alpha
        r, g, b = p.color[0], p.color[1], p.color[2]
        sz = max(1, int(p.size * a))
        surf = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (r, g, b, int(255 * a)), (sz, sz), sz)
        screen.blit(surf, (int(p.x) - sz, int(p.y) - sz))


def update_particles(particles: list[Particle], dt: float) -> list[Particle]:
    """Update all particles, returning only the living ones."""
    for p in particles:
        p.update(dt)
    return [p for p in particles if p.alive]


# ---------------------------------------------------------------------------
# Spawn patterns
# ---------------------------------------------------------------------------

def _spawn_burst(cx: float, cy: float, color: tuple, count: int,
                 speed: float, lifetime: float, size: float) -> list[Particle]:
    particles = []
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        spd = random.uniform(speed * 0.5, speed)
        vx = math.cos(angle) * spd
        vy = math.sin(angle) * spd
        c = _vary_color(color)
        particles.append(Particle(cx, cy, vx, vy, random.uniform(lifetime * 0.6, lifetime), c, size))
    return particles


def _spawn_rise(cx: float, cy: float, color: tuple, count: int,
                speed: float, lifetime: float, size: float) -> list[Particle]:
    particles = []
    for _ in range(count):
        vx = random.uniform(-speed * 0.3, speed * 0.3)
        vy = -random.uniform(speed * 0.5, speed)
        c = _vary_color(color)
        particles.append(Particle(
            cx + random.uniform(-12, 12), cy,
            vx, vy, random.uniform(lifetime * 0.6, lifetime), c, size,
        ))
    return particles


def _spawn_converge(cx: float, cy: float, tx: float, ty: float,
                    color: tuple, count: int, speed: float,
                    lifetime: float, size: float) -> list[Particle]:
    """Particles start around (cx,cy) and move toward (tx,ty)."""
    particles = []
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(30, 60)
        sx = tx + math.cos(angle) * dist
        sy = ty + math.sin(angle) * dist
        dx, dy = tx - sx, ty - sy
        d = math.hypot(dx, dy) or 1
        spd = random.uniform(speed * 0.5, speed)
        vx = dx / d * spd
        vy = dy / d * spd
        c = _vary_color(color)
        particles.append(Particle(sx, sy, vx, vy, random.uniform(lifetime * 0.6, lifetime), c, size))
    return particles


def _vary_color(base: tuple) -> tuple:
    """Add slight random variation to a color."""
    r = max(0, min(255, base[0] + random.randint(-20, 20)))
    g = max(0, min(255, base[1] + random.randint(-20, 20)))
    b = max(0, min(255, base[2] + random.randint(-20, 20)))
    return (r, g, b)


# ---------------------------------------------------------------------------
# Per-skill presets
# ---------------------------------------------------------------------------

SKILL_PARTICLES: dict[str, dict] = {
    "shrapnel_blast": {
        "color": (220, 180, 100),
        "pattern": "burst",
        "count": 14,
        "speed": 120,
        "lifetime": 0.5,
        "size": 3.0,
        "target": "enemy",
        "shake": 0,
    },
    "voltage_surge": {
        "color": (180, 200, 255),
        "pattern": "burst",
        "count": 16,
        "speed": 140,
        "lifetime": 0.4,
        "size": 2.5,
        "target": "enemy",
        "shake": 0,
    },
    "magnet_storm": {
        "color": (180, 100, 220),
        "pattern": "burst",
        "count": 22,
        "speed": 160,
        "lifetime": 0.6,
        "size": 3.5,
        "target": "enemy",
        "shake": 6,
    },
    "patchwork_heal": {
        "color": (100, 220, 80),
        "pattern": "rise",
        "count": 12,
        "speed": 80,
        "lifetime": 0.7,
        "size": 3.0,
        "target": "player",
        "shake": 0,
    },
    "jury_rig_shield": {
        "color": (80, 140, 255),
        "pattern": "rise",
        "count": 10,
        "speed": 70,
        "lifetime": 0.6,
        "size": 3.0,
        "target": "player",
        "shake": 0,
    },
    "scrap_leech": {
        "color": (180, 80, 220),
        "pattern": "converge",
        "count": 14,
        "speed": 100,
        "lifetime": 0.6,
        "size": 2.5,
        "target": "player",
        "shake": 0,
    },
    "overclock": {
        "color": (255, 160, 60),
        "pattern": "burst",
        "count": 12,
        "speed": 100,
        "lifetime": 0.5,
        "size": 2.5,
        "target": "enemy",
        "shake": 0,
    },
    "emp_pulse": {
        "color": (100, 160, 255),
        "pattern": "burst",
        "count": 18,
        "speed": 130,
        "lifetime": 0.5,
        "size": 3.0,
        "target": "enemy",
        "shake": 0,
    },
    "system_purge": {
        "color": (200, 255, 200),
        "pattern": "rise",
        "count": 14,
        "speed": 90,
        "lifetime": 0.7,
        "size": 3.0,
        "target": "player",
        "shake": 0,
    },
}

# Generic presets for basic attacks / items
GENERIC_HIT = {
    "color": (255, 255, 255),
    "pattern": "burst",
    "count": 8,
    "speed": 80,
    "lifetime": 0.3,
    "size": 2.0,
    "target": "enemy",
    "shake": 0,
}


def spawn_particles(cx: float, cy: float, preset_key: str,
                    target_pos: tuple[float, float] | None = None) -> list[Particle]:
    """Spawn particles for a skill or generic effect at (cx, cy).

    For 'converge' patterns, target_pos is the destination point.
    """
    preset = SKILL_PARTICLES.get(preset_key, GENERIC_HIT)
    color = preset["color"]
    count = preset["count"]
    speed = preset["speed"]
    lifetime = preset["lifetime"]
    size = preset["size"]
    pattern = preset["pattern"]

    if pattern == "burst":
        return _spawn_burst(cx, cy, color, count, speed, lifetime, size)
    elif pattern == "rise":
        return _spawn_rise(cx, cy, color, count, speed, lifetime, size)
    elif pattern == "converge" and target_pos is not None:
        return _spawn_converge(cx, cy, target_pos[0], target_pos[1],
                               color, count, speed, lifetime, size)
    else:
        return _spawn_burst(cx, cy, color, count, speed, lifetime, size)


def get_shake_intensity(preset_key: str) -> float:
    """Return screen shake intensity for a skill, or 0."""
    preset = SKILL_PARTICLES.get(preset_key)
    if preset:
        return preset.get("shake", 0)
    return 0


def shake_offset(intensity: float, timer: float) -> tuple[int, int]:
    """Return a (dx, dy) screen shake offset that decays over time."""
    if intensity <= 0 or timer <= 0:
        return (0, 0)
    mag = intensity * min(1.0, timer / 0.3)
    dx = int(random.uniform(-mag, mag))
    dy = int(random.uniform(-mag, mag))
    return (dx, dy)
