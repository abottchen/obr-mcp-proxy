from mcp.server.fastmcp import FastMCP

from ..dice import parse_and_roll
from ..websocket_server import RelayConnection


def register_combat_tools(mcp: FastMCP, relay: RelayConnection) -> None:
    @mcp.tool()
    async def roll_dice(
        expression: str,
        mode: str | None = None,
    ) -> dict:
        """Roll dice using standard D&D notation.

        Args:
            expression: Dice notation (e.g. '1d20', '2d6+3', '4d6-1', '1d100').
            mode: Optional 'advantage' or 'disadvantage' for 1d20 rolls.

        Returns:
            Dict with expression, individual rolls, modifier, and total.
            For advantage/disadvantage: includes both rolls, which was chosen, and mode.
        """
        if mode and mode not in ("advantage", "disadvantage"):
            return {"error": f"Unknown mode: {mode}. Use 'advantage' or 'disadvantage'"}

        return parse_and_roll(expression, mode)
