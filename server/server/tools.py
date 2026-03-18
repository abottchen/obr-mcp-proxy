import logging

from mcp.server.fastmcp import FastMCP

from .websocket_server import RelayConnection

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP, relay: RelayConnection) -> None:
    @mcp.tool()
    async def get_items(
        layer: str | None = None,
        name: str | None = None,
    ) -> list[dict]:
        """List all items in the current Owlbear Rodeo scene.

        Args:
            layer: Filter by layer (CHARACTER, MAP, PROP, DRAWING, FOG, ATTACHMENT, NOTE, POPOVER, RULER, GRID)
            name: Filter by name (case-insensitive substring match)

        Returns:
            Array of scene items with id, name, type, layer, position, visible, locked, and metadata.
        """
        items = await relay.send_request("scene.items.getItems")

        if not isinstance(items, list):
            items = []

        # Apply filters
        if layer:
            layer_upper = layer.upper()
            items = [i for i in items if i.get("layer") == layer_upper]

        if name:
            name_lower = name.lower()
            items = [
                i for i in items if name_lower in (i.get("name", "") or "").lower()
            ]

        return items
