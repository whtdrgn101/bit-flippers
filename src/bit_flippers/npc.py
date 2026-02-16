from dataclasses import dataclass, field

from bit_flippers.sprites import AnimatedSprite, create_placeholder_npc, load_npc


@dataclass
class NPC:
    tile_x: int
    tile_y: int
    name: str
    dialogue_lines: list[str]
    sprite: AnimatedSprite
    facing: str = "down"

    def update(self, dt):
        self.sprite.update(dt)

    @property
    def image(self):
        return self.sprite.image


def make_npc(tile_x, tile_y, name, dialogue_lines, body_color, facing="down", npc_key=None):
    """Convenience factory for creating an NPC with a sprite.

    If *npc_key* is provided, attempts to load pixel-art PNG first.
    """
    if npc_key is not None:
        sprite = load_npc(npc_key, body_color, facing)
    else:
        sprite = create_placeholder_npc(body_color, facing)
    return NPC(
        tile_x=tile_x,
        tile_y=tile_y,
        name=name,
        dialogue_lines=dialogue_lines,
        sprite=sprite,
        facing=facing,
    )
