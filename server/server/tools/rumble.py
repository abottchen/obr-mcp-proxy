from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from ..websocket_server import RelayConnection

RUMBLE_PREFIX = "com.battle-system.friends/"


def register_rumble_tools(mcp: FastMCP, relay: RelayConnection) -> None:
    # roll_dice is disabled — Rumble does the rolling and displays the result,
    # but the result isn't returned to us. Kept for reference in case a use case
    # emerges (e.g. if Rumble adds result readback).
    #
    # @mcp.tool()
    # async def roll_dice(notation: str, sender: str = "DM") -> dict:
    #     """Roll dice via Rumble so the result appears in the shared chat log."""
    #     await relay.send_request("player.setMetadata", {
    #         "metadata": {
    #             f"{RUMBLE_PREFIX}metadata_diceroll": {
    #                 "notation": notation,
    #                 "created": datetime.now(timezone.utc).isoformat(),
    #                 "sender": sender,
    #             }
    #         }
    #     })
    #     return {"notation": notation, "sender": sender}

    @mcp.tool()
    async def send_chat(
        message: str,
        sender: str = "DM",
        target_id: str = "0000",
    ) -> dict:
        """Send a message to Rumble's chat log.

        Args:
            message: The chat message text.
            sender: Name to display as the sender. Defaults to 'DM'.
            target_id: OBR user ID to send to, or '0000' for the whole party. Defaults to '0000'.

        Returns:
            Confirmation that the message was sent.
        """
        await relay.send_request("player.setMetadata", {
            "metadata": {
                f"{RUMBLE_PREFIX}metadata_chatlog": {
                    "chatlog": message,
                    "created": datetime.now(timezone.utc).isoformat(),
                    "sender": sender,
                    "targetId": target_id,
                }
            }
        })
        return {"message": message, "sender": sender, "target_id": target_id}
