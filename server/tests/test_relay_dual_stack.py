import asyncio
import json
import ssl

import pytest
import websockets

from server.websocket_server import RelayConnection

TEST_PORT = 19876
TOKEN = "test-token"


def _client_ssl() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def _auth_roundtrip(url: str) -> str:
    async with websockets.connect(url, ssl=_client_ssl(), open_timeout=5) as ws:
        await ws.send(json.dumps({"type": "auth", "token": TOKEN}))
        return await asyncio.wait_for(ws.recv(), timeout=5)


@pytest.fixture
async def relay():
    conn = RelayConnection(token=TOKEN, port=TEST_PORT)
    await conn.start()
    try:
        yield conn
    finally:
        await conn.stop()


@pytest.mark.parametrize("host", ["127.0.0.1", "[::1]"])
async def test_relay_accepts_both_loopback_families(relay, host):
    """Browsers resolve `localhost` to ::1 first; the relay must answer there too."""
    reply = await _auth_roundtrip(f"wss://{host}:{TEST_PORT}")
    assert json.loads(reply) == {"type": "auth-ok"}
