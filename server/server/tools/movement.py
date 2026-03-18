from mcp.server.fastmcp import FastMCP

from ..grid import (
    compute_move,
    compute_move_toward,
    euclidean_distance,
    fetch_grid_info,
    parse_direction,
    pixels_per_cell,
)
from ..items import get_item_by_id
from ..websocket_server import RelayConnection

CLASH_PREFIX = "com.battle-system.clash/"


def register_movement_tools(mcp: FastMCP, relay: RelayConnection) -> None:
    @mcp.tool()
    async def move_item(
        item_id: str,
        x: float,
        y: float,
        snap: bool = True,
    ) -> dict:
        """Move an item to an absolute pixel position.

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
            position = await relay.send_request(
                "scene.grid.snapPosition", {"position": position}
            )

        await relay.send_request(
            "scene.items.updateItems",
            {"items": [{"id": item_id, "position": position}]},
        )
        return {
            "id": item_id,
            "name": item.get("name", ""),
            "position": position,
        }

    @mcp.tool()
    async def move_toward(
        item_id: str,
        target_id: str,
        cells: int | None = None,
        adjacent: bool = False,
    ) -> dict:
        """Move an item toward another item.

        Args:
            item_id: UUID of the item to move.
            target_id: UUID of the target item.
            cells: Number of grid cells to move. Mutually exclusive with adjacent.
            adjacent: If true, move to a position adjacent (1 cell away) to the target.

        Returns:
            The item's new position and distance moved.
        """
        item = await get_item_by_id(relay, item_id)
        target_item = await get_item_by_id(relay, target_id)
        grid = await fetch_grid_info(relay)

        from_pos = item["position"]
        to_pos = target_item["position"]

        if adjacent:
            ppc = pixels_per_cell(grid)
            dist_px = euclidean_distance(from_pos, to_pos)
            total_cells = dist_px / ppc
            move_cells = max(0, int(total_cells) - 1)
            new_pos = compute_move_toward(from_pos, to_pos, move_cells, grid)
        elif cells is not None:
            new_pos = compute_move_toward(from_pos, to_pos, cells, grid)
        else:
            raise ValueError("Provide either 'cells' or 'adjacent=true'")

        snapped = await relay.send_request(
            "scene.grid.snapPosition", {"position": new_pos}
        )

        await relay.send_request(
            "scene.items.updateItems",
            {"items": [{"id": item_id, "position": snapped}]},
        )

        distance = await relay.send_request(
            "scene.grid.getDistance",
            {"from": from_pos, "to": snapped},
        )

        return {
            "id": item_id,
            "name": item.get("name", ""),
            "position": snapped,
            "distance_feet": distance * grid.scale_multiplier,
        }

    @mcp.tool()
    async def move_direction(
        item_id: str,
        direction: str,
        cells: int | None = None,
        use_speed: bool = False,
    ) -> dict:
        """Move an item in a cardinal or ordinal direction.

        Args:
            item_id: UUID of the item to move.
            direction: Direction to move (north, south, east, west, northeast, northwest, southeast, southwest).
            cells: Number of grid cells to move. Mutually exclusive with use_speed.
            use_speed: If true, use the item's walking speed from Clash metadata to determine distance.

        Returns:
            The item's new position and distance moved.
        """
        item = await get_item_by_id(relay, item_id)
        grid = await fetch_grid_info(relay)
        dir_enum = parse_direction(direction)

        if use_speed:
            meta = item.get("metadata", {})
            speed_key = f"{CLASH_PREFIX}clash_speedWalk"
            speed = meta.get(speed_key)
            if speed is None:
                raise ValueError(
                    f"Item '{item.get('name')}' has no walking speed in Clash metadata"
                )
            move_cells = int(float(speed) / grid.scale_multiplier)
        elif cells is not None:
            move_cells = cells
        else:
            raise ValueError("Provide either 'cells' or 'use_speed=true'")

        from_pos = item["position"]
        new_pos = compute_move(from_pos, dir_enum, move_cells, grid)

        snapped = await relay.send_request(
            "scene.grid.snapPosition", {"position": new_pos}
        )

        await relay.send_request(
            "scene.items.updateItems",
            {"items": [{"id": item_id, "position": snapped}]},
        )

        distance = await relay.send_request(
            "scene.grid.getDistance",
            {"from": from_pos, "to": snapped},
        )

        return {
            "id": item_id,
            "name": item.get("name", ""),
            "position": snapped,
            "distance_feet": distance * grid.scale_multiplier,
        }
