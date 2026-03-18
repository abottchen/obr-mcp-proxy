from mcp.server.fastmcp import FastMCP

from ..items import resolve_item, resolve_items_by_pattern
from ..websocket_server import RelayConnection


def register_mutate_tools(mcp: FastMCP, relay: RelayConnection) -> None:
    @mcp.tool()
    async def update_item(
        identifier: str,
        name: str | None = None,
        visible: bool | None = None,
        locked: bool | None = None,
        layer: str | None = None,
    ) -> dict:
        """Update properties of a scene item.

        Args:
            identifier: Item ID or name to update.
            name: New display name.
            visible: Set visibility (true = visible to players).
            locked: Set locked state (true = cannot be moved).
            layer: Move to layer (CHARACTER, MAP, PROP, DRAWING, etc).

        Returns:
            The update that was applied.
        """
        item = await resolve_item(relay, identifier)
        fields: dict = {}
        if name is not None:
            fields["name"] = name
        if visible is not None:
            fields["visible"] = visible
        if locked is not None:
            fields["locked"] = locked
        if layer is not None:
            fields["layer"] = layer.upper()

        if not fields:
            raise ValueError("No fields to update. Provide at least one of: name, visible, locked, layer")

        await relay.send_request(
            "scene.items.updateItems",
            {"items": [{"id": item["id"], **fields}]},
        )
        return {"id": item["id"], "updated": fields}

    @mcp.tool()
    async def set_visible(pattern: str, visible: bool) -> dict:
        """Show or hide items matching a name pattern.

        Args:
            pattern: Name pattern (case-insensitive substring match).
            visible: True to show, false to hide.

        Returns:
            Count and names of items updated.
        """
        items = await resolve_items_by_pattern(relay, pattern)
        if not items:
            raise ValueError(f"No items matched pattern: {pattern}")

        updates = [{"id": i["id"], "visible": visible} for i in items]
        await relay.send_request("scene.items.updateItems", {"items": updates})

        names = [i.get("name", i["id"]) for i in items]
        return {
            "count": len(items),
            "names": names,
            "visible": visible,
        }

    @mcp.tool()
    async def update_item_metadata(identifier: str, metadata: dict) -> dict:
        """Update metadata on a scene item (merged with existing metadata).

        Args:
            identifier: Item ID or name.
            metadata: Dict of metadata keys to set. Merged with existing metadata, not replaced.

        Returns:
            The item ID and metadata keys that were set.
        """
        item = await resolve_item(relay, identifier)
        await relay.send_request(
            "scene.items.updateItems",
            {"items": [{"id": item["id"], "metadata": metadata}]},
        )
        return {"id": item["id"], "metadata_keys_set": list(metadata.keys())}

    @mcp.tool()
    async def update_scene_metadata(metadata: dict) -> dict:
        """Update scene-level metadata (merged with existing).

        Args:
            metadata: Dict of metadata keys to set on the scene.

        Returns:
            The metadata keys that were set.
        """
        await relay.send_request("scene.setMetadata", {"metadata": metadata})
        return {"metadata_keys_set": list(metadata.keys())}

    @mcp.tool()
    async def delete_item(identifier: str) -> dict:
        """Remove an item from the scene.

        Args:
            identifier: Item ID or name of the item to delete.

        Returns:
            The ID and name of the deleted item.
        """
        item = await resolve_item(relay, identifier)
        await relay.send_request(
            "scene.items.deleteItems",
            {"ids": [item["id"]]},
        )
        return {"id": item["id"], "name": item.get("name", "")}

    @mcp.tool()
    async def add_item(
        type: str,
        name: str,
        x: float,
        y: float,
        layer: str = "CHARACTER",
        width: int = 256,
        height: int = 256,
        image_url: str | None = None,
        text: str | None = None,
        visible: bool = True,
        locked: bool = False,
        metadata: dict | None = None,
    ) -> dict:
        """Add a new item to the scene.

        Args:
            type: Item type (IMAGE, SHAPE, TEXT, LABEL).
            name: Display name for the item.
            x: X pixel position.
            y: Y pixel position.
            layer: Layer to place on (CHARACTER, MAP, PROP, DRAWING). Defaults to CHARACTER.
            width: Image/shape width in pixels. Defaults to 256.
            height: Image/shape height in pixels. Defaults to 256.
            image_url: Image URL (required for IMAGE type).
            text: Text content (for TEXT/LABEL types).
            visible: Whether the item is visible. Defaults to true.
            locked: Whether the item is locked. Defaults to false.
            metadata: Optional metadata dict.

        Returns:
            Summary of the added item.
        """
        item_type = type.upper()
        item: dict = {
            "type": item_type,
            "name": name,
            "position": {"x": x, "y": y},
            "rotation": 0,
            "scale": {"x": 1, "y": 1},
            "visible": visible,
            "locked": locked,
            "layer": layer.upper(),
            "metadata": metadata or {},
            "grid": {"dpi": 256, "offset": {"x": 128, "y": 128}},
            "text": {
                "richText": [{"type": "paragraph", "children": [{"text": ""}]}],
                "plainText": text or name,
                "style": {
                    "padding": 8,
                    "fontFamily": "Roboto",
                    "fontSize": 24,
                    "fontWeight": 400,
                    "textAlign": "CENTER",
                    "textAlignVertical": "BOTTOM",
                    "fillColor": "#ffffff",
                    "fillOpacity": 1,
                    "strokeColor": "#ffffff",
                    "strokeOpacity": 1,
                    "strokeWidth": 0,
                    "lineHeight": 1.5,
                },
                "type": "PLAIN",
                "width": "AUTO",
                "height": "AUTO",
            },
            "textItemType": "LABEL",
        }

        if item_type == "IMAGE":
            if not image_url:
                raise ValueError("image_url is required for IMAGE type items")
            item["image"] = {
                "url": image_url,
                "width": width,
                "height": height,
                "mime": "image/png",
            }

        await relay.send_request("scene.items.addItems", {"items": [item]})
        return {"name": name, "type": item_type, "position": {"x": x, "y": y}}
