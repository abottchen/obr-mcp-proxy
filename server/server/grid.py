import asyncio
import math
from dataclasses import dataclass
from enum import Enum

from .websocket_server import RelayConnection


class Direction(Enum):
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    NORTHEAST = "northeast"
    NORTHWEST = "northwest"
    SOUTHEAST = "southeast"
    SOUTHWEST = "southwest"


@dataclass
class GridInfo:
    dpi: int
    scale_multiplier: float
    scale_unit: str
    grid_type: str  # "SQUARE", "HEX_HORIZONTAL", "HEX_VERTICAL"
    measurement: str


async def fetch_grid_info(relay: RelayConnection) -> GridInfo:
    """Fetch current grid settings from the extension."""
    dpi, scale, grid_type, measurement = await asyncio.gather(
        relay.send_request("scene.grid.getDpi"),
        relay.send_request("scene.grid.getScale"),
        relay.send_request("scene.grid.getType"),
        relay.send_request("scene.grid.getMeasurement"),
    )
    return GridInfo(
        dpi=int(dpi),
        scale_multiplier=float(scale["parsed"]["multiplier"]),
        scale_unit=scale["parsed"]["unit"],
        grid_type=str(grid_type),
        measurement=str(measurement),
    )


_DIRECTION_VECTORS: dict[Direction, tuple[float, float]] = {
    Direction.NORTH: (0, -1),
    Direction.SOUTH: (0, 1),
    Direction.EAST: (1, 0),
    Direction.WEST: (-1, 0),
    Direction.NORTHEAST: (math.sqrt(2) / 2, -math.sqrt(2) / 2),
    Direction.NORTHWEST: (-math.sqrt(2) / 2, -math.sqrt(2) / 2),
    Direction.SOUTHEAST: (math.sqrt(2) / 2, math.sqrt(2) / 2),
    Direction.SOUTHWEST: (-math.sqrt(2) / 2, math.sqrt(2) / 2),
}


def parse_direction(direction: str) -> Direction:
    """Parse a direction string into a Direction enum."""
    try:
        return Direction(direction.lower().strip())
    except ValueError:
        valid = ", ".join(d.value for d in Direction)
        raise ValueError(f"Invalid direction '{direction}'. Valid: {valid}")


def pixels_per_cell(grid: GridInfo) -> float:
    """Approximate pixel spacing for one cell."""
    if grid.grid_type == "SQUARE":
        return float(grid.dpi)
    elif grid.grid_type == "HEX_HORIZONTAL":
        # Pointy-top hex: vertical spacing = DPI * 3/4
        return grid.dpi * 0.75
    elif grid.grid_type == "HEX_VERTICAL":
        # Flat-top hex: horizontal spacing = DPI * 3/4
        return grid.dpi * 0.75
    return float(grid.dpi)


def feet_to_pixels(feet: float, grid: GridInfo) -> float:
    """Convert game-feet to pixels."""
    cells = feet / grid.scale_multiplier
    return cells * pixels_per_cell(grid)


def pixels_to_feet(pixels: float, grid: GridInfo) -> float:
    """Convert pixels to game-feet."""
    cells = pixels / pixels_per_cell(grid)
    return cells * grid.scale_multiplier


def token_size_cells(item: dict) -> int:
    """Get a token's size in grid cells (1 for Medium, 2 for Large, etc.)."""
    item_grid = item.get("grid", {})
    offset_x = item_grid.get("offset", {}).get("x", 128)
    item_dpi = item_grid.get("dpi", 256)
    # offset / item_dpi * 2 gives the size: 0.5/0.5*2=1 for Medium, 1.0/1.0*2=2 for Large
    return round(offset_x / item_dpi * 2)


def token_radius_px(item: dict, grid: GridInfo) -> float:
    """Get a token's radius in pixels based on its grid offset.

    A Medium token (1x1) has offset 128 with item dpi 256, so radius = 0.5 cells.
    A Large token (2x2) has offset 256 with item dpi 256, so radius = 1.0 cells.
    Returns the radius in scene pixels.
    """
    item_grid = item.get("grid", {})
    offset_x = item_grid.get("offset", {}).get("x", 128)
    item_dpi = item_grid.get("dpi", 256)
    radius_cells = offset_x / item_dpi
    return radius_cells * grid.dpi


def is_even_sized(item: dict) -> bool:
    """Return True if the token is even-sized (2x2, 4x4) and snaps to grid intersections."""
    return token_size_cells(item) % 2 == 0


def euclidean_distance(pos1: dict, pos2: dict) -> float:
    """Pixel-space Euclidean distance between two positions."""
    dx = pos1["x"] - pos2["x"]
    dy = pos1["y"] - pos2["y"]
    return math.sqrt(dx * dx + dy * dy)


def compute_move(
    pos: dict, direction: Direction, cells: int, grid: GridInfo
) -> dict:
    """Compute approximate new position after moving N cells in a direction.

    Result should be snapped via the extension's snapPosition.
    """
    dx, dy = _DIRECTION_VECTORS[direction]
    ppc = pixels_per_cell(grid)

    if grid.grid_type == "SQUARE":
        return {
            "x": pos["x"] + dx * cells * grid.dpi,
            "y": pos["y"] + dy * cells * grid.dpi,
        }
    elif grid.grid_type == "HEX_HORIZONTAL":
        # Pointy-top: x-spacing = DPI * sqrt(3)/2, y-spacing = DPI * 3/4
        x_step = grid.dpi * math.sqrt(3) / 2
        y_step = grid.dpi * 0.75
        return {
            "x": pos["x"] + dx * cells * x_step,
            "y": pos["y"] + dy * cells * y_step,
        }
    elif grid.grid_type == "HEX_VERTICAL":
        # Flat-top: x-spacing = DPI * 3/4, y-spacing = DPI * sqrt(3)/2
        x_step = grid.dpi * 0.75
        y_step = grid.dpi * math.sqrt(3) / 2
        return {
            "x": pos["x"] + dx * cells * x_step,
            "y": pos["y"] + dy * cells * y_step,
        }

    # Fallback
    return {
        "x": pos["x"] + dx * cells * ppc,
        "y": pos["y"] + dy * cells * ppc,
    }


def compute_move_toward(
    from_pos: dict, to_pos: dict, cells: int, grid: GridInfo
) -> dict:
    """Compute approximate new position after moving N cells toward target.

    Result should be snapped via the extension's snapPosition.
    """
    dx = to_pos["x"] - from_pos["x"]
    dy = to_pos["y"] - from_pos["y"]
    dist = math.sqrt(dx * dx + dy * dy)

    if dist < 1.0:
        return dict(from_pos)

    # Normalize direction
    nx, ny = dx / dist, dy / dist
    ppc = pixels_per_cell(grid)
    move_dist = cells * ppc

    # Don't overshoot the target
    move_dist = min(move_dist, dist)

    return {
        "x": from_pos["x"] + nx * move_dist,
        "y": from_pos["y"] + ny * move_dist,
    }
