from mcp.server.fastmcp import FastMCP

from ..websocket_server import RelayConnection
from .read import register_read_tools
from .mutate import register_mutate_tools
from .movement import register_movement_tools


def register_tools(mcp: FastMCP, relay: RelayConnection) -> None:
    register_read_tools(mcp, relay)
    register_mutate_tools(mcp, relay)
    register_movement_tools(mcp, relay)
