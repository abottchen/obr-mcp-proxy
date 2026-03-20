import logging
import os
import sys
from pathlib import Path

import anyio
import uvicorn
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .tools import register_tools
from .websocket_server import RelayConnection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def main() -> None:
    # Load .env from project root (one level above server/)
    load_dotenv(Path(__file__).parent.parent.parent / ".env")

    token = os.environ.get("OBR_MCP_TOKEN")
    if not token:
        logger.error("OBR_MCP_TOKEN environment variable is required")
        sys.exit(1)

    relay_port = int(os.environ.get("OBR_MCP_PORT", "9876"))
    mcp_port = int(os.environ.get("OBR_MCP_HTTP_PORT", "3000"))

    relay = RelayConnection(token=token, port=relay_port)
    mcp = FastMCP(
        "obr-mcp-server",
        host="127.0.0.1",
        port=mcp_port,
        instructions=(
            "This server controls an Owlbear Rodeo virtual tabletop scene. "
            "Items returned by get_items/get_item include position, layer, and "
            "type information. IMAGE items have an image.url field containing a "
            "publicly accessible URL — fetch and view these to visually inspect "
            "maps, tokens, and props for spatial understanding.\n\n"
            "Grid and scale: use get_grid to get the DPI (pixels per cell) and "
            "scale (feet per cell, usually 5ft). Token positions are in pixels. "
            "To convert: cells = pixels / dpi, feet = cells * scale.\n\n"
            "Movement: move_item takes absolute pixel coordinates. To move by "
            "direction or toward a target, compute the destination from positions "
            "and grid DPI. For speed-limited movement, read clash_speedWalk from "
            "the token's metadata via get_item_metadata.\n\n"
            "Metadata: Clash (combat tracker) stores stats as item metadata. Use "
            "list_metadata_keys to discover available fields, or request common "
            "fields directly: clash_currentHP, clash_maxHP, clash_armorClass, "
            "clash_speedWalk, clash_standardActions, clash_bonusActions. "
            "Short names work for reads; writes require the full key with "
            "com.battle-system.clash/ prefix."
        ),
    )
    register_tools(mcp, relay)

    async def run_all() -> None:
        await relay.start()
        logger.info("MCP server starting on http://127.0.0.1:%d/mcp", mcp_port)

        app = mcp.streamable_http_app()
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=mcp_port,
            log_level="info",
            timeout_graceful_shutdown=1,
        )
        server = uvicorn.Server(config)
        await server.serve()

    try:
        anyio.run(run_all)
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
