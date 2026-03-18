"""Dice roller for D&D 5e.

Adapted from toa/.claude/skills/roll/roll.py
"""

import random
import re


def parse_and_roll(expression: str, mode: str | None = None) -> dict:
    """Roll dice using standard D&D notation.

    Args:
        expression: Dice notation (e.g. '1d20', '2d6+3', '4d6-1').
        mode: Optional 'advantage' or 'disadvantage' for 1d20 rolls.

    Returns:
        Dict with expression, rolls, modifier, total, and optionally chosen/mode.
    """
    match = re.match(r"^(\d+)d(\d+)([+-]\d+)?$", expression.strip())
    if not match:
        return {
            "error": f"Invalid dice expression: {expression}. Use format: NdS or NdS+M or NdS-M"
        }

    num_dice = int(match.group(1))
    sides = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    if num_dice < 1 or num_dice > 100:
        return {"error": "Number of dice must be between 1 and 100"}
    if sides < 2 or sides > 100:
        return {"error": "Number of sides must be between 2 and 100"}

    rolls = [random.randint(1, sides) for _ in range(num_dice)]

    result = {
        "expression": expression,
        "rolls": rolls,
        "modifier": modifier,
        "total": sum(rolls) + modifier,
    }

    if mode in ("advantage", "disadvantage") and num_dice == 1 and sides == 20:
        second_roll = random.randint(1, sides)
        result["rolls"] = [rolls[0], second_roll]
        if mode == "advantage":
            chosen = max(rolls[0], second_roll)
        else:
            chosen = min(rolls[0], second_roll)
        result["chosen"] = chosen
        result["total"] = chosen + modifier
        result["mode"] = mode

    return result
