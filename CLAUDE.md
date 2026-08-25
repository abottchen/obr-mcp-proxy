# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OBR MCP Bridge — an MCP server that lets Claude read and manipulate Owlbear Rodeo (OBR) virtual tabletop scenes through a relay extension running in the GM's browser. Two components communicate over WebSocket:

1. **MCP Server** (`server/`) — Python, uses `mcp` SDK with streamable HTTP transport. Exposes MCP tools on `localhost:3000/mcp` and runs a WSS relay on `localhost:9876`.
2. **OBR Relay Extension** (`extension/`) — TypeScript/Vite browser extension loaded into OBR. Connects to the WSS server and proxies OBR SDK calls. Only visible to the GM role.

The extension is a thin relay — all game logic lives in the MCP server. Multiple Claude Code sessions can connect to the same MCP server simultaneously.

## Architecture

```
Claude Code ──→ HTTP (MCP) ──→ Python MCP Server ──WSS──→ Browser Extension ──→ OBR SDK
```

The server uses `FastMCP` (from the `mcp` package) for tool registration. Tools are organized in `server/server/tools/` by domain: `read.py`, `mutate.py`, `movement.py`, `combat.py`, `rumble.py`. Each module exports a `register_*_tools(mcp, relay)` function called from `tools/__init__.py`.

The relay extension dispatches incoming WebSocket requests to OBR SDK calls via a handler map in `extension/src/handlers.ts`. The relay layer (`extension/src/relay.ts`) handles auth, reconnection with exponential backoff, and connection state.

## Development Commands

### MCP Server
```bash
cd server && pip install -e .        # Install (editable)
cd server && python -m server.main   # Run
```

### Extension
```bash
cd extension && npm install          # Install
cd extension && npx vite             # Dev server (HTTPS on localhost:5173)
cd extension && npm run build        # Production build (tsc + vite build)
```

### Both (Windows Terminal)
```powershell
./start.ps1                          # Opens both in split panes
```

### TLS Certificates (required, one-time setup)
```bash
mkcert -install
mkcert -cert-file server/certs/localhost.pem -key-file server/certs/localhost-key.pem localhost 127.0.0.1
```

## Environment

`.env` in project root (loaded by server via `python-dotenv`):
- `OBR_MCP_TOKEN` (required) — shared secret for extension auth
- `OBR_MCP_PORT` — WSS relay port (default 9876)
- `OBR_MCP_HTTP_PORT` — HTTP MCP port (default 3000)
- `OBR_MCP_ALLOWED_ORIGINS` — comma-separated relay origin allowlist (default
  `https://abottchen.github.io,https://localhost:5173`). The relay 403s any
  other `Origin`; see `DEFAULT_ALLOWED_ORIGINS` in `websocket_server.py`.

Note: `.mcp.json` points Claude Code at `http://127.0.0.1:3001/mcp` — this overrides the default port. If you change `OBR_MCP_HTTP_PORT`, update `.mcp.json` to match.

## Adding a New MCP Tool

1. Create or edit a file in `server/server/tools/` (group by domain).
2. Define an `async` function decorated with `@mcp.tool()` inside a `register_*_tools(mcp, relay)` function.
3. Wire it in `server/server/tools/__init__.py` if it's a new module.
4. Add a matching handler in `extension/src/handlers.ts` if the tool needs a new OBR SDK call that isn't already dispatched.

## Key Conventions

- **Item resolution**: Read tools accept names or UUIDs. Mutation/movement tools require UUIDs. The `resolve_item()` helper in `server/server/items.py` handles ID-first, then exact name, then substring matching.
- **Metadata short names**: `get_item_metadata` accepts Clash field names without the `com.battle-system.clash/` prefix for reads. Writes via `update_item_metadata` require the full prefixed key.
- **Grid coordinates**: All positions are in pixels. Use `get_grid` for DPI/scale conversion. Grid distance uses OBR's native measurement (Chebyshev, hex, etc.) via `scene.grid.getDistance`.
- **Token sizes**: `move_item` automatically snaps to the correct grid position based on token size (cell centers for odd sizes, intersections for even).
- **Concurrency**: The relay limits concurrent requests to 3 (`_semaphore` in `RelayConnection`) with a 10-second timeout per request.

## Deployment

The extension deploys to GitHub Pages via `.github/workflows/deploy.yml` on push to `main`. The production extension manifest points to `abottchen.github.io/obr-mcp-proxy/`.

## CLAUDE.md.example

`CLAUDE.md.example` in the project root is a combat operations guide — it documents how to run D&D 5e combat using the MCP tools (initiative, attacks, movement, HP tracking). It's meant to be copied/customized as a session-specific CLAUDE.md when running combat encounters.
