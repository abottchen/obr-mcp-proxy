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
        # SHAPE-specific
        shape_type: str = "RECTANGLE",
        shape_fill_color: str = "#000000",
        shape_fill_opacity: float = 0.0,
        shape_stroke_color: str = "#000000",
        shape_stroke_opacity: float = 1.0,
        shape_stroke_width: float = 5.0,
        shape_stroke_dash: list[float] | None = None,
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
        # TEXT/LABEL style
        font_family: str = "Roboto",
        font_size: float = 24,
        font_weight: int = 400,
        text_align: str = "CENTER",
        text_align_vertical: str = "BOTTOM",
        text_fill_color: str = "#ffffff",
        text_fill_opacity: float = 1.0,
        text_stroke_color: str = "#ffffff",
        text_stroke_opacity: float = 1.0,
        text_stroke_width: float = 0,
        line_height: float = 1.5,
        padding: int = 8,
        text_width: int | str = "AUTO",
        text_height: int | str = "AUTO",
        # LABEL-specific style
        background_color: str | None = None,
        background_opacity: float | None = None,
        corner_radius: float | None = None,
        pointer_width: float | None = None,
        pointer_height: float | None = None,
        pointer_direction: str | None = None,
        max_view_scale: float | None = None,
        min_view_scale: float | None = None,
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
            shape_type: SHAPE type ("RECTANGLE", "CIRCLE", "TRIANGLE", "HEXAGON"). Defaults to "RECTANGLE".
            shape_fill_color: SHAPE fill color hex. Defaults to "#000000".
            shape_fill_opacity: SHAPE fill opacity 0-1. Defaults to 0.0 (transparent).
            shape_stroke_color: SHAPE stroke color hex. Defaults to "#000000".
            shape_stroke_opacity: SHAPE stroke opacity 0-1. Defaults to 1.0.
            shape_stroke_width: SHAPE stroke width. Defaults to 5.0.
            shape_stroke_dash: SHAPE stroke dash pattern. Defaults to solid (empty).
            font_family: Font family for TEXT/LABEL. Defaults to "Roboto".
            font_size: Font size for TEXT/LABEL. Defaults to 24.
            font_weight: Font weight for TEXT/LABEL (100-900). Defaults to 400.
            text_align: Horizontal alignment for TEXT/LABEL ("LEFT", "CENTER", "RIGHT"). Defaults to "CENTER".
            text_align_vertical: Vertical alignment for TEXT/LABEL ("TOP", "MIDDLE", "BOTTOM"). Defaults to "BOTTOM".
            text_fill_color: Text color hex for TEXT/LABEL. Defaults to "#ffffff".
            text_fill_opacity: Text color opacity 0-1 for TEXT/LABEL. Defaults to 1.0.
            text_stroke_color: Text outline color hex for TEXT/LABEL. Defaults to "#ffffff".
            text_stroke_opacity: Text outline opacity 0-1 for TEXT/LABEL. Defaults to 1.0.
            text_stroke_width: Text outline width for TEXT/LABEL. Defaults to 0.
            line_height: Line height multiplier for TEXT/LABEL. Defaults to 1.5.
            padding: Padding in pixels for TEXT/LABEL. Defaults to 8.
            text_width: Width for TEXT/LABEL ("AUTO" or pixel number). Defaults to "AUTO".
            text_height: Height for TEXT/LABEL ("AUTO" or pixel number). Defaults to "AUTO".
            background_color: LABEL background color hex.
            background_opacity: LABEL background opacity 0-1.
            corner_radius: LABEL corner radius.
            pointer_width: LABEL pointer width.
            pointer_height: LABEL pointer height.
            pointer_direction: LABEL pointer direction ("UP", "DOWN", "LEFT", "RIGHT").
            max_view_scale: LABEL max view scale.
            min_view_scale: LABEL min view scale.
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
                    "padding": padding,
                    "fontFamily": font_family,
                    "fontSize": font_size,
                    "fontWeight": font_weight,
                    "textAlign": text_align.upper(),
                    "textAlignVertical": text_align_vertical.upper(),
                    "fillColor": text_fill_color,
                    "fillOpacity": text_fill_opacity,
                    "strokeColor": text_stroke_color,
                    "strokeOpacity": text_stroke_opacity,
                    "strokeWidth": text_stroke_width,
                    "lineHeight": line_height,
                },
                "type": "PLAIN",
                "width": text_width,
                "height": text_height,
            },
            "textItemType": "LABEL",
        }

        stroke_style = {
            "strokeColor": stroke_color,
            "strokeOpacity": stroke_opacity,
            "strokeWidth": stroke_width,
            "strokeDash": stroke_dash or [],
        }

        if item_type in ("TEXT", "LABEL"):
            item["text"] = text or name
            item["textStyle"] = {
                "fontFamily": font_family,
                "fontSize": font_size,
                "fontWeight": font_weight,
                "textAlign": text_align.upper(),
                "textAlignVertical": text_align_vertical.upper(),
                "fillColor": text_fill_color,
                "fillOpacity": text_fill_opacity,
                "strokeColor": text_stroke_color,
                "strokeOpacity": text_stroke_opacity,
                "strokeWidth": text_stroke_width,
                "lineHeight": line_height,
                "padding": padding,
                "width": text_width,
                "height": text_height,
            }
            if item_type == "LABEL":
                label_style: dict = {}
                if background_color is not None:
                    label_style["backgroundColor"] = background_color
                if background_opacity is not None:
                    label_style["backgroundOpacity"] = background_opacity
                if corner_radius is not None:
                    label_style["cornerRadius"] = corner_radius
                if pointer_width is not None:
                    label_style["pointerWidth"] = pointer_width
                if pointer_height is not None:
                    label_style["pointerHeight"] = pointer_height
                if pointer_direction is not None:
                    label_style["pointerDirection"] = pointer_direction.upper()
                if max_view_scale is not None:
                    label_style["maxViewScale"] = max_view_scale
                if min_view_scale is not None:
                    label_style["minViewScale"] = min_view_scale
                if label_style:
                    item["labelStyle"] = label_style

        elif item_type == "SHAPE":
            item["shapeType"] = shape_type.upper()
            item["width"] = width
            item["height"] = height
            item["style"] = {
                "fillColor": shape_fill_color,
                "fillOpacity": shape_fill_opacity,
                "strokeColor": shape_stroke_color,
                "strokeOpacity": shape_stroke_opacity,
                "strokeWidth": shape_stroke_width,
                "strokeDash": shape_stroke_dash or [],
            }

        elif item_type == "IMAGE":
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
