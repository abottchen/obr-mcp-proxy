from mcp.server.fastmcp import FastMCP

from ..grid import is_even_sized
from ..items import get_item_by_id
from ..websocket_server import RelayConnection


async def _snap_for_item(relay: RelayConnection, position: dict, item: dict) -> dict:
    """Snap a position using the correct mode for the item's size."""
    even = is_even_sized(item)
    return await relay.send_request(
        "scene.grid.snapPosition",
        {
            "position": position,
            "useCenter": not even,
            "useCorners": even,
        },
    )


def register_movement_tools(mcp: FastMCP, relay: RelayConnection) -> None:
    @mcp.tool()
    async def move_item(
        item_id: str,
        x: float,
        y: float,
        snap: bool = True,
    ) -> dict:
        """Move an item to an absolute pixel position.

        To move by direction or toward a target, compute the destination
        coordinates yourself using get_grid (for DPI/scale) and item positions.
        For speed-limited movement, read clash_speedWalk from the item's
        metadata via get_item_metadata.

        Args:
            item_id: The item's UUID. Use get_items or get_item to find the ID first.
            x: Target X pixel coordinate.
            y: Target Y pixel coordinate.
            snap: If true, snap to the nearest grid position. Defaults to true.

        Returns:
            The item's new position.
        """
        item = await get_item_by_id(relay, item_id)
        position = {"x": x, "y": y}

        if snap:
            position = await _snap_for_item(relay, position, item)

        await relay.send_request(
            "scene.items.updateItems",
            {"items": [{"id": item_id, "position": position}]},
        )
        return {
            "id": item_id,
            "name": item.get("name", ""),
            "position": position,
        }
