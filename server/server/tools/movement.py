from mcp.server.fastmcp import FastMCP

from ..grid import (
    compute_move,
    compute_move_toward,
    euclidean_distance,
    fetch_grid_info,
    parse_direction,
    pixels_per_cell,
)
from ..items import resolve_item
from ..websocket_server import RelayConnection

CLASH_PREFIX = "com.battle-system.clash/"


def register_movement_tools(mcp: FastMCP, relay: RelayConnection) -> None:
    @mcp.tool()
    async def move_item(
        identifier: str,
        x: float,
        y: float,
        snap: bool = True,
    ) -> dict:
        """Move an item to an absolute pixel position.

        Args:
            identifier: Item ID or name.
            x: Target X pixel coordinate.
            y: Target Y pixel coordinate.
            snap: If true, snap to the nearest grid position. Defaults to true.

        Returns:
            The item's new position.
        """
        item = await resolve_item(relay, identifier)
        position = {"x": x, "y": y}

        if snap:
            position = await relay.send_request(
                "scene.grid.snapPosition", {"position": position}
            )

        await relay.send_request(
            "scene.items.updateItems",
            {"items": [{"id": item["id"], "position": position}]},
        )
        return {
            "id": item["id"],
            "name": item.get("name", ""),
            "position": position,
        }

    @mcp.tool()
    async def move_toward(
        identifier: str,
        target: str,
        cells: int | None = None,
        adjacent: bool = False,
    ) -> dict:
        """Move an item toward another item.

        Args:
            identifier: Item ID or name to move.
            target: Item ID or name of the target.
            cells: Number of grid cells to move. Mutually exclusive with adjacent.
            adjacent: If true, move to a position adjacent (1 cell away) to the target.

        Returns:
            The item's new position and distance moved.
        """
        item = await resolve_item(relay, identifier)
        target_item = await resolve_item(relay, target)
        grid = await fetch_grid_info(relay)

        from_pos = item["position"]
        to_pos = target_item["position"]

        if adjacent:
            # Move to 1 cell away from target
            ppc = pixels_per_cell(grid)
            dist_px = euclidean_distance(from_pos, to_pos)
            # Number of cells to move = total cells - 1 (stop adjacent)
            total_cells = dist_px / ppc
            move_cells = max(0, int(total_cells) - 1)
            new_pos = compute_move_toward(from_pos, to_pos, move_cells, grid)
        elif cells is not None:
            new_pos = compute_move_toward(from_pos, to_pos, cells, grid)
        else:
            raise ValueError("Provide either 'cells' or 'adjacent=true'")

        # Snap to grid
        snapped = await relay.send_request(
            "scene.grid.snapPosition", {"position": new_pos}
        )

        await relay.send_request(
            "scene.items.updateItems",
            {"items": [{"id": item["id"], "position": snapped}]},
        )

        # Get distance moved
        distance = await relay.send_request(
            "scene.grid.getDistance",
            {"from": from_pos, "to": snapped},
        )

        return {
            "id": item["id"],
            "name": item.get("name", ""),
            "position": snapped,
            "distance_feet": distance * grid.scale_multiplier,
        }

    @mcp.tool()
    async def move_direction(
        identifier: str,
        direction: str,
        cells: int | None = None,
        use_speed: bool = False,
    ) -> dict:
        """Move an item in a cardinal or ordinal direction.

        Args:
            identifier: Item ID or name to move.
            direction: Direction to move (north, south, east, west, northeast, northwest, southeast, southwest).
            cells: Number of grid cells to move. Mutually exclusive with use_speed.
            use_speed: If true, use the item's walking speed from Clash metadata to determine distance.

        Returns:
            The item's new position and distance moved.
        """
        item = await resolve_item(relay, identifier)
        grid = await fetch_grid_info(relay)
        dir_enum = parse_direction(direction)

        if use_speed:
            # Read walking speed from Clash metadata
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

        # Snap to grid
        snapped = await relay.send_request(
            "scene.grid.snapPosition", {"position": new_pos}
        )

        await relay.send_request(
            "scene.items.updateItems",
            {"items": [{"id": item["id"], "position": snapped}]},
        )

        # Get distance moved
        distance = await relay.send_request(
            "scene.grid.getDistance",
            {"from": from_pos, "to": snapped},
        )

        return {
            "id": item["id"],
            "name": item.get("name", ""),
            "position": snapped,
            "distance_feet": distance * grid.scale_multiplier,
        }
