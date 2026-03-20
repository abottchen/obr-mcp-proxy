import asyncio
import math
from dataclasses import dataclass

from .websocket_server import RelayConnection


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


def pixels_per_cell(grid: GridInfo) -> float:
    """Approximate pixel spacing for one cell."""
    if grid.grid_type == "SQUARE":
        return float(grid.dpi)
    elif grid.grid_type == "HEX_HORIZONTAL":
        return grid.dpi * 0.75
    elif grid.grid_type == "HEX_VERTICAL":
        return grid.dpi * 0.75
    return float(grid.dpi)


def pixels_to_feet(pixels: float, grid: GridInfo) -> float:
    """Convert pixels to game-feet."""
    cells = pixels / pixels_per_cell(grid)
    return cells * grid.scale_multiplier


def token_size_cells(item: dict) -> int:
    """Get a token's size in grid cells (1 for Medium, 2 for Large, etc.)."""
    item_grid = item.get("grid", {})
    offset_x = item_grid.get("offset", {}).get("x", 128)
    item_dpi = item_grid.get("dpi", 256)
    return round(offset_x / item_dpi * 2)


def is_even_sized(item: dict) -> bool:
    """Return True if the token is even-sized (2x2, 4x4) and snaps to grid intersections."""
    return token_size_cells(item) % 2 == 0


def euclidean_distance(pos1: dict, pos2: dict) -> float:
    """Pixel-space Euclidean distance between two positions."""
    dx = pos1["x"] - pos2["x"]
    dy = pos1["y"] - pos2["y"]
    return math.sqrt(dx * dx + dy * dy)
