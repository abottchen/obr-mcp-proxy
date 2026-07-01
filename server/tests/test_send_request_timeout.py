import time

import pytest

from server.websocket_server import RelayConnection


class _FakeWS:
    """Captures sent frames and never replies, so the pending future times out."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send(self, data: str) -> None:
        self.sent.append(data)


async def test_send_request_honors_custom_timeout():
    relay = RelayConnection(token="t")
    relay._ws = _FakeWS()          # type: ignore[assignment]
    relay._authenticated = True

    start = time.monotonic()
    with pytest.raises(TimeoutError):
        await relay.send_request("noop", {"x": 1}, timeout=0.05)
    elapsed = time.monotonic() - start

    # Proves the custom 0.05s was used, not the 10s default.
    assert elapsed < 2.0
    # The request frame was actually sent to the socket.
    assert relay._ws.sent and "noop" in relay._ws.sent[0]  # type: ignore[union-attr]
