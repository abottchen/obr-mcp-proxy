import uuid

from mcp.server.fastmcp import FastMCP

from ..websocket_server import RelayConnection


def register_mutate_tools(mcp: FastMCP, relay: RelayConnection) -> None:
    @mcp.tool()
    async def update_item(item_id: str, fields: dict) -> dict:
        """Update properties of a scene item.

        Args:
            item_id: The item's UUID. Use get_items or get_item to find the ID first.
            fields: Dict of fields to set. Common fields include:
                name (str), visible (bool), locked (bool), layer (str),
                position ({x, y}), rotation (number), scale ({x, y}),
                zIndex (number), disableHit (bool), attachedTo (str),
                description (str), disableAutoZIndex (bool).

        Returns:
            The update that was applied.
        """
        if not fields:
            raise ValueError("No fields to update")

        await relay.send_request(
            "scene.items.updateItems",
            {"items": [{"id": item_id, **fields}]},
        )
        return {"id": item_id, "updated": fields}

    @mcp.tool()
    async def update_item_metadata(item_id: str, metadata: dict) -> dict:
        """Update metadata on a scene item (merged with existing metadata).

        Args:
            item_id: The item's UUID. Use get_items or get_item to find the ID first.
            metadata: Dict of metadata keys to set. Merged with existing metadata, not replaced.

        Returns:
            The item ID and metadata keys that were set.
        """
        await relay.send_request(
            "scene.items.updateItems",
            {"items": [{"id": item_id, "metadata": metadata}]},
        )
        return {"id": item_id, "metadata_keys_set": list(metadata.keys())}

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
    async def update_room_metadata(metadata: dict) -> dict:
        """Update room-level metadata (merged with existing, persists across scenes).

        Args:
            metadata: Dict of metadata keys to set on the room.

        Returns:
            The metadata keys that were set.
        """
        await relay.send_request("room.setMetadata", {"metadata": metadata})
        return {"metadata_keys_set": list(metadata.keys())}

    @mcp.tool()
    async def delete_item(item_id: str) -> dict:
        """Remove an item from the scene.

        Args:
            item_id: The item's UUID. Use get_items or get_item to find the ID first.

        Returns:
            The ID and name of the deleted item.
        """
        # Verify the item exists before deleting
        items = await relay.send_request("scene.items.getItems")
        item = next((i for i in items if i.get("id") == item_id), None)
        if not item:
            raise ValueError(f"No item found with ID: {item_id}")

        await relay.send_request(
            "scene.items.deleteItems",
            {"ids": [item_id]},
        )
        return {"id": item_id, "name": item.get("name", "")}

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
        # LINE-specific
        end_x: float | None = None,
        end_y: float | None = None,
        # CURVE-specific
        points: list[dict] | None = None,
        tension: float = 0.5,
        closed: bool = False,
        # PATH-specific
        commands: list[list] | None = None,
        fill_rule: str = "evenodd",
        # Shared style for LINE/CURVE/PATH
        stroke_color: str = "#000000",
        stroke_opacity: float = 1.0,
        stroke_width: float = 5.0,
        stroke_dash: list[float] | None = None,
        fill_color: str = "#000000",
        fill_opacity: float = 0.0,
    ) -> dict:
        """Add a new item to the scene.

        Args:
            type: Item type (IMAGE, SHAPE, TEXT, LABEL, LINE, CURVE, PATH).
            name: Display name for the item.
            x: X pixel position (also the start position for LINE).
            y: Y pixel position (also the start position for LINE).
            layer: Layer to place on (CHARACTER, MAP, PROP, DRAWING). Defaults to CHARACTER.
            width: Image/shape width in pixels. Defaults to 256.
            height: Image/shape height in pixels. Defaults to 256.
            image_url: Image URL (required for IMAGE type).
            text: Text content (for TEXT/LABEL types).
            visible: Whether the item is visible. Defaults to true.
            locked: Whether the item is locked. Defaults to false.
            metadata: Optional metadata dict.
            end_x: LINE end X position (required for LINE).
            end_y: LINE end Y position (required for LINE).
            points: CURVE points as list of {x, y} dicts (required for CURVE).
            tension: CURVE bezier tension. Defaults to 0.5.
            closed: Whether CURVE is closed. Defaults to false.
            commands: PATH commands as list of tuples (required for PATH).
                Each command is a list: [command_type, ...args].
                Command types: 0=MOVE(x,y), 1=LINE(x,y), 2=QUAD(cpX,cpY,x,y),
                3=CONIC(cpX,cpY,x,y,weight), 4=CUBIC(cp1X,cp1Y,cp2X,cp2Y,x,y), 5=CLOSE().
            fill_rule: PATH fill rule, "evenodd" or "nonzero". Defaults to "evenodd".
            stroke_color: Stroke color hex for LINE/CURVE/PATH. Defaults to "#000000".
            stroke_opacity: Stroke opacity 0-1 for LINE/CURVE/PATH. Defaults to 1.0.
            stroke_width: Stroke width for LINE/CURVE/PATH. Defaults to 5.0.
            stroke_dash: Dash pattern for LINE/CURVE/PATH. Defaults to solid (empty).
            fill_color: Fill color hex for CURVE/PATH. Defaults to "#000000".
            fill_opacity: Fill opacity 0-1 for CURVE/PATH. Defaults to 0.0 (transparent).

        Returns:
            Summary of the added item.
        """
        item_type = type.upper()
        item: dict = {
            "id": str(uuid.uuid4()),
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

        stroke_style = {
            "strokeColor": stroke_color,
            "strokeOpacity": stroke_opacity,
            "strokeWidth": stroke_width,
            "strokeDash": stroke_dash or [],
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

        elif item_type == "LINE":
            if end_x is None or end_y is None:
                raise ValueError("end_x and end_y are required for LINE type items")
            item["startPosition"] = {"x": x, "y": y}
            item["endPosition"] = {"x": end_x, "y": end_y}
            item["style"] = stroke_style

        elif item_type == "CURVE":
            if not points:
                raise ValueError("points are required for CURVE type items")
            item["points"] = points
            item["style"] = {
                **stroke_style,
                "fillColor": fill_color,
                "fillOpacity": fill_opacity,
                "tension": tension,
                "closed": closed,
            }

        elif item_type == "PATH":
            if not commands:
                raise ValueError("commands are required for PATH type items")
            item["commands"] = commands
            item["fillRule"] = fill_rule
            item["style"] = {
                **stroke_style,
                "fillColor": fill_color,
                "fillOpacity": fill_opacity,
            }

        await relay.send_request("scene.items.addItems", {"items": [item]})
        return {"id": item["id"], "name": name, "type": item_type, "position": {"x": x, "y": y}}
