import asyncio

from mcp.server.fastmcp import FastMCP

from ..grid import euclidean_distance, fetch_grid_info, pixels_to_feet
from ..items import resolve_item
from ..websocket_server import RelayConnection


def register_read_tools(mcp: FastMCP, relay: RelayConnection) -> None:
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

        if layer:
            layer_upper = layer.upper()
            items = [i for i in items if i.get("layer") == layer_upper]

        if name:
            name_lower = name.lower()
            items = [
                i for i in items if name_lower in (i.get("name", "") or "").lower()
            ]

        return items

    @mcp.tool()
    async def get_item(identifier: str) -> dict:
        """Get a single item by ID or name.

        Args:
            identifier: Item ID (exact match) or name (case-insensitive). Errors if ambiguous.

        Returns:
            The matching scene item with all fields.
        """
        return await resolve_item(relay, identifier)

    @mcp.tool()
    async def get_metadata() -> dict:
        """Get scene-level metadata.

        Returns:
            Scene metadata dict (includes Clash combat state, extension configs, etc).
        """
        result = await relay.send_request("scene.getMetadata")
        return result if isinstance(result, dict) else {}

    @mcp.tool()
    async def get_item_metadata(identifier: str) -> dict:
        """Get metadata for a specific item.

        Args:
            identifier: Item ID or name.

        Returns:
            The item's metadata dict (includes Clash stats if configured).
        """
        item = await resolve_item(relay, identifier)
        return item.get("metadata", {})

    @mcp.tool()
    async def get_players() -> list[dict]:
        """Get all connected players in the room.

        Returns:
            Array of player objects with id, name, color, role, etc.
        """
        result = await relay.send_request("party.getPlayers")
        return result if isinstance(result, list) else []

    @mcp.tool()
    async def get_grid() -> dict:
        """Get the current scene's grid settings.

        Returns:
            Dict with dpi, scale (raw + parsed), type (SQUARE/HEX_HORIZONTAL/HEX_VERTICAL), and measurement mode.
        """
        dpi, scale, grid_type, measurement = await asyncio.gather(
            relay.send_request("scene.grid.getDpi"),
            relay.send_request("scene.grid.getScale"),
            relay.send_request("scene.grid.getType"),
            relay.send_request("scene.grid.getMeasurement"),
        )
        return {
            "dpi": dpi,
            "scale": scale,
            "type": grid_type,
            "measurement": measurement,
        }

    @mcp.tool()
    async def find_items_near(
        radius_feet: float,
        origin: str | None = None,
        x: float | None = None,
        y: float | None = None,
        layer: str | None = None,
    ) -> list[dict]:
        """Find items within a radius of a point or another item.

        Args:
            radius_feet: Search radius in game feet.
            origin: Item ID or name to use as center point. Mutually exclusive with x/y.
            x: X pixel coordinate of center point. Use with y.
            y: Y pixel coordinate of center point. Use with x.
            layer: Optional layer filter (CHARACTER, MAP, PROP, etc).

        Returns:
            Array of items within radius, each with an added 'distance_feet' field.
        """
        if origin:
            origin_item = await resolve_item(relay, origin)
            center = origin_item["position"]
        elif x is not None and y is not None:
            center = {"x": x, "y": y}
        else:
            raise ValueError("Provide either 'origin' (item name/ID) or both 'x' and 'y'")

        items, grid = await asyncio.gather(
            relay.send_request("scene.items.getItems"),
            fetch_grid_info(relay),
        )

        if not isinstance(items, list):
            return []

        radius_pixels = radius_feet / grid.scale_multiplier * grid.dpi

        results = []
        for item in items:
            # Skip the origin item itself
            if origin and item.get("id") == (origin_item.get("id") if origin else None):
                continue

            if layer:
                if item.get("layer") != layer.upper():
                    continue

            pos = item.get("position")
            if not pos:
                continue

            dist_px = euclidean_distance(center, pos)
            if dist_px <= radius_pixels:
                item_copy = dict(item)
                item_copy["distance_feet"] = round(pixels_to_feet(dist_px, grid), 1)
                results.append(item_copy)

        results.sort(key=lambda i: i["distance_feet"])
        return results
