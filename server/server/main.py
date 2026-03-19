import logging
import os
import sys
from pathlib import Path

import anyio
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

    port = int(os.environ.get("OBR_MCP_PORT", "9876"))

    relay = RelayConnection(token=token, port=port)
    mcp = FastMCP("obr-mcp-server")
    register_tools(mcp, relay)

    async def run_all() -> None:
        await relay.start()
        logger.info("MCP server starting on stdio...")
        await mcp.run_stdio_async()

    try:
        anyio.run(run_all)
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
