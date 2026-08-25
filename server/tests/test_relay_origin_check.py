import asyncio
import json
import ssl

import pytest
import websockets

from server.websocket_server import RelayConnection

TEST_PORT = 19877
TOKEN = "test-token"
ALLOWED = "https://abottchen.github.io"


def _client_ssl() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def _auth(origin: str | None) -> dict:
    async with websockets.connect(
        f"wss://127.0.0.1:{TEST_PORT}", ssl=_client_ssl(), origin=origin, open_timeout=5
    ) as ws:
        await ws.send(json.dumps({"type": "auth", "token": TOKEN}))
        return json.loads(await asyncio.wait_for(ws.recv(), timeout=5))


@pytest.fixture
async def relay():
    conn = RelayConnection(token=TOKEN, port=TEST_PORT, allowed_origins=[ALLOWED])
    await conn.start()
    try:
        yield conn
    finally:
        await conn.stop()


async def test_allowed_origin_can_connect(relay):
    assert await _auth(ALLOWED) == {"type": "auth-ok"}


async def test_foreign_origin_is_rejected(relay):
    """Browsers cannot forge Origin, so this is what blocks a malicious page."""
    with pytest.raises(websockets.exceptions.InvalidStatus) as exc:
        await _auth("https://evil.example")
    assert exc.value.response.status_code == 403


async def test_missing_origin_is_allowed(relay):
    """Non-browser clients send no Origin; browsers always send one."""
    assert await _auth(None) == {"type": "auth-ok"}
