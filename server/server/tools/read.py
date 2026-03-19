import asyncio

from mcp.server.fastmcp import FastMCP

from ..grid import euclidean_distance, fetch_grid_info, pixels_to_feet
from ..constants import CLASH_PREFIX
from ..items import resolve_item
from ..websocket_server import RelayConnection


def _strip_metadata(item: dict) -> dict:
    """Return a copy of the item with metadata removed."""
    return {k: v for k, v in item.items() if k != "metadata"}


def _filter_metadata(metadata: dict, fields: list[str]) -> dict:
    """Return only the requested fields from metadata.

    Accepts short field names (e.g. 'clash_currentHP') or full keys
    (e.g. 'com.battle-system.clash/clash_currentHP').
    """
    result = {}
    for field in fields:
        # Try exact key first
        if field in metadata:
            result[field] = metadata[field]
        else:
            # Try with Clash prefix
            prefixed = f"{CLASH_PREFIX}{field}"
            if prefixed in metadata:
                result[field] = metadata[prefixed]
    return result


def register_read_tools(mcp: FastMCP, relay: RelayConnection) -> None:
    @mcp.tool()
    async def get_items(
        layer: str | None = None,
        name: str | None = None,
    ) -> list[dict]:
        """List all items in the current Owlbear Rodeo scene.

        Returns lightweight item data without metadata. Use get_item_metadata
        to retrieve metadata for specific items.

        Args:
            layer: Filter by layer (CHARACTER, MAP, PROP, DRAWING, FOG, ATTACHMENT, NOTE, POPOVER, RULER, GRID)
            name: Filter by name (case-insensitive substring match)

        Returns:
            Array of scene items with id, name, type, layer, position, visible, and locked.
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

        return [_strip_metadata(i) for i in items]

    @mcp.tool()
    async def get_item(identifier: str) -> dict:
        """Get a single item by ID or name.

        Returns lightweight item data without metadata. Use get_item_metadata
        to retrieve metadata.

        Args:
            identifier: Item ID (exact match) or name (case-insensitive). Errors if ambiguous.

        Returns:
            The matching scene item without metadata.
        """
        item = await resolve_item(relay, identifier)
        return _strip_metadata(item)

    @mcp.tool()
    async def get_metadata() -> dict:
        """Get scene-level metadata.

        Returns:
            Scene metadata dict (includes Clash combat state, extension configs, etc).
        """
        result = await relay.send_request("scene.getMetadata")
        return result if isinstance(result, dict) else {}

    @mcp.tool()
    async def get_player_metadata() -> dict:
        """Get metadata for the current player (the GM running the relay).

        Returns:
            Player metadata dict. May contain Rumble chat/dice state and other extension data.
        """
        result = await relay.send_request("player.getMetadata")
        return result if isinstance(result, dict) else {}

    @mcp.tool()
    async def get_room_metadata() -> dict:
        """Get room-level metadata (persists across scenes).

        Returns:
            Room metadata dict. May contain extension data from Rumble, Quick Store, etc.
        """
        result = await relay.send_request("room.getMetadata")
        return result if isinstance(result, dict) else {}

    @mcp.tool()
    async def get_item_metadata(
        identifier: str,
        fields: list[str] | None = None,
    ) -> dict:
        """Get metadata for a specific item.

        Args:
            identifier: Item ID or name.
            fields: Optional list of metadata field names to return. Accepts short
                names without the Clash prefix (e.g. 'clash_currentHP' instead of
                'com.battle-system.clash/clash_currentHP'). If omitted, returns all metadata.

        Returns:
            The item's metadata dict, filtered to requested fields if specified.
        """
        item = await resolve_item(relay, identifier)
        metadata = item.get("metadata", {})

        if fields:
            return _filter_metadata(metadata, fields)

        return metadata

    @mcp.tool()
    async def list_metadata_keys(identifier: str) -> list[str]:
        """List the metadata key names available on an item.

        Call this first to discover what fields exist before using
        get_item_metadata with specific field names. This avoids pulling
        the entire metadata object when you only need a few values.
        Each item has its own metadata; tokens with Clash stats will have
        keys like clash_currentHP, clash_armorClass, clash_standardActions, etc.
        Tokens without Clash setup will have no keys.

        Args:
            identifier: Item ID or name.

        Returns:
            List of metadata key names present on the item.
        """
        item = await resolve_item(relay, identifier)
        metadata = item.get("metadata", {})
        return list(metadata.keys())

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

        Returns lightweight item data without metadata, plus a distance_feet field.

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
            if origin and item.get("id") == origin_item.get("id"):
                continue

            if layer:
                if item.get("layer") != layer.upper():
                    continue

            pos = item.get("position")
            if not pos:
                continue

            dist_px = euclidean_distance(center, pos)
            if dist_px <= radius_pixels:
                item_copy = _strip_metadata(item)
                item_copy["distance_feet"] = round(pixels_to_feet(dist_px, grid), 1)
                results.append(item_copy)

        results.sort(key=lambda i: i["distance_feet"])
        return results
