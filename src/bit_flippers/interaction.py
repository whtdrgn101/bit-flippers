"""NPC interaction resolution — extracted from OverworldState._try_interact."""

from __future__ import annotations

from dataclasses import dataclass, field

from bit_flippers.items import WEAPONSMITH_STOCK, ARMORSMITH_STOCK
from bit_flippers.strings import get_npc_dialogue


@dataclass
class InteractionResult:
    dialogue_lines: list[str] = field(default_factory=list)
    npc_name: str = ""
    quest_id: str | None = None
    quest_action: str | None = None  # "accept" or "claim_rewards"
    shop_stock: list[str] | None = None  # opens shop if set (None = default shop)
    open_default_shop: bool = False
    message: str | None = None  # pickup notification


# Map NPC names to their shop stock lists.
# None means "use default shop stock".
_SHOP_NPCS: dict[str, list[str] | None] = {
    "Shopkeeper": None,
    "Weaponsmith": WEAPONSMITH_STOCK,
    "Armorsmith": ARMORSMITH_STOCK,
}


def resolve_npc_interaction(npc, player_quests, inventory) -> InteractionResult:
    """Determine what happens when the player interacts with an NPC.

    Returns an InteractionResult describing dialogue, quest actions, and
    shop opening — the caller (OverworldState) decides how to push states.
    """
    from bit_flippers.quests import QUEST_REGISTRY

    result = InteractionResult(
        dialogue_lines=list(npc.dialogue_lines),
        npc_name=npc.name,
    )

    quest_info = player_quests.get_npc_quest(npc.name)
    if quest_info is not None:
        qid, qstate = quest_info
        qdef = QUEST_REGISTRY[qid]

        if qstate == "available":
            lines = get_npc_dialogue(qdef.dialogue_offer)
            if lines:
                result.dialogue_lines = lines
            result.quest_id = qid
            result.quest_action = "accept"

        elif qstate == "active":
            player_quests.update_fetch(inventory)
            lines = get_npc_dialogue(qdef.dialogue_active)
            if lines:
                result.dialogue_lines = lines

        elif qstate == "complete":
            lines = get_npc_dialogue(qdef.dialogue_complete)
            if lines:
                result.dialogue_lines = lines
            result.quest_id = qid
            result.quest_action = "claim_rewards"

        elif qstate == "done":
            lines = get_npc_dialogue(qdef.dialogue_done)
            if lines:
                result.dialogue_lines = lines

    # Shop NPCs open their shop after quest dialogue (only when there's no
    # quest action that would take precedence as an on_close callback).
    if result.quest_action is None and npc.name in _SHOP_NPCS:
        stock = _SHOP_NPCS[npc.name]
        if stock is not None:
            result.shop_stock = stock
        else:
            result.open_default_shop = True

    return result
