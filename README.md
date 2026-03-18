# OBR MCP Bridge

An MCP server that allows Claude to read and manipulate Owlbear Rodeo scenes via a relay extension running in the GM's browser.

## Architecture

```
Claude Code / Claude Desktop
        |
        |  MCP protocol (stdio)
        v
   MCP Server (Python, runs locally)
        |
        |  WSS on localhost
        v
   OBR Relay Extension (iframe in GM's browser)
        |
        |  OBR SDK calls
        v
   Owlbear Rodeo scene state
```

The extension is a thin relay — it executes OBR SDK calls and returns results. All game logic lives in the MCP server.

## Components

### MCP Server (`server/`)

Python server using the `mcp` SDK with stdio transport. Runs a WSS server on `localhost:9876` that the relay extension connects to.

### OBR Relay Extension (`extension/`)

TypeScript/Vite browser extension loaded into Owlbear Rodeo. Connects to the local WSS server, authenticates with a shared token, and proxies SDK calls.

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- [mkcert](https://github.com/nicmccabe/mkcert) for TLS certificates

### TLS Certificates

Required because OBR runs over HTTPS and browsers block mixed content (plain `ws://` from an HTTPS page).

```bash
mkcert -install
mkcert -cert-file server/certs/localhost.pem -key-file server/certs/localhost-key.pem localhost 127.0.0.1
```

If using Firefox, you may need to accept the certificate by navigating to `https://localhost:9876` and `https://localhost:5173` before connecting.

### Environment

Copy `.env.example` to `.env` and set a shared secret token:

```bash
cp .env.example .env
# Edit .env to set OBR_MCP_TOKEN
```

### Install Dependencies

```bash
# Extension
cd extension && npm install

# MCP Server
cd server && pip install -e .
```

### MCP Configuration

Create `.mcp.json` in the project root:

```json
{
  "mcpServers": {
    "obr-mcp-server": {
      "command": "python",
      "args": ["-m", "server.main"],
      "cwd": "server"
    }
  }
}
```

## Usage

1. Start the extension dev server:
   ```bash
   cd extension && npx vite
   ```

2. In Owlbear Rodeo, add a custom extension using `https://localhost:5173/manifest.json`

3. Open the MCP Relay extension in OBR, enter `wss://localhost:9876` and your token, click Connect

4. The MCP server starts automatically when Claude Code loads the `.mcp.json` config

## MCP Tools

| Tool | Description |
|------|-------------|
| `get_items` | List scene items with optional filtering by layer or name |
