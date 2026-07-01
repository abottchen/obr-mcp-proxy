import asyncio

from mcp.server.fastmcp import FastMCP

from ..websocket_server import RelayConnection

ROLL_TIMEOUT = 30.0


def register_combat_tools(mcp: FastMCP, relay: RelayConnection) -> None:
    # dicex handles one roll at a time, and the server's per-roll timeout
    # starts at send time — serialize rolls here so each roll's 30s window
    # stays aligned with its actual send and we avoid spurious timeouts /
    # phantom rolls when multiple requests queue up behind dicex.
    dice_lock = asyncio.Lock()

    async def _roll(notation: str) -> dict:
        """Trigger one dicex roll, returning its result or an {error} dict."""
        try:
            async with dice_lock:
                return await relay.send_request(
                    "dice.roll", {"notation": notation}, timeout=ROLL_TIMEOUT
                )
        except (TimeoutError, ConnectionError, RuntimeError) as e:
            return {"error": str(e), "notation": notation}

    @mcp.tool()
    async def roll_dice(notation: str) -> dict:
        """Roll dice in the shared 3D dice tray (dicex) and return the result.

        Triggers a real physics roll in the GM's dicex extension via the Dice+
        integration. Rolls are GM-hidden.

        Notation (dicex format):
          - Terms joined by + / - ; whitespace ignored. Multiple pools allowed,
            e.g. "2d6+1d8+3".
          - NdS: N dice with S sides. Valid sides: 4, 6, 8, 10, 12, 20, 100.
          - Modifiers: integers, e.g. "+3", "-2". Dice cannot be subtracted.
          - Keep/drop (suffix on a pool): "khN"/"kN" keep highest N,
            "klN" keep lowest N, "dN" drop lowest N.
          - Exploding (suffix, before keep/drop): "!" on max, "!>N" on >= N,
            "!N" on exactly N.
          Examples: "1d20", "2d6+3", "2d20kh1+5" (advantage), "2d20kl1"
          (disadvantage), "4d6k3" (ability score), "3d6!" (exploding).

        Args:
            notation: A dicex dice-notation string (see above).

        Returns:
            On success: {notation, total, summary, groups: [{description,
            diceType, total, dice: [{value, kept}]}]}.
            On failure: {error, notation} — invalid notation, or dicex not
            responding (extension missing / GM tab inactive).
        """
        return await _roll(notation)

    @mcp.tool()
    async def roll_dice_batch(notations: list[str]) -> dict:
        """Roll several dice notations in one call and return all results.

        Each notation is rolled in the shared 3D dicex tray, one after another
        (dicex animates one roll at a time, so the batch runs serially). Results
        preserve input order, and a bad notation does not abort the batch — its
        slot holds an {error} dict instead. See roll_dice for the full notation
        reference and the per-roll result shape.

        Args:
            notations: A list of dicex dice-notation strings (see roll_dice).

        Returns:
            {"results": [<per-notation result>, ...]} in input order. Each entry
            is either {notation, total, summary, groups} on success or
            {error, notation} on failure.
        """
        results = [await _roll(notation) for notation in notations]
        return {"results": results}
