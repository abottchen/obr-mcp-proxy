import asyncio

from server.tools.combat import register_combat_tools


class _CaptureMCP:
    """Fake FastMCP whose .tool() decorator captures registered functions."""

    def __init__(self) -> None:
        self.tools: dict = {}

    def tool(self, *args, **kwargs):
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn

        return deco


class _FakeRelay:
    def __init__(self, result=None, exc=None) -> None:
        self.result = result
        self.exc = exc
        self.calls: list = []

    async def send_request(self, method, params=None, timeout=None):
        self.calls.append((method, params, timeout))
        if self.exc is not None:
            raise self.exc
        return self.result


def _get_roll_dice(relay):
    mcp = _CaptureMCP()
    register_combat_tools(mcp, relay)
    return mcp.tools["roll_dice"]


async def test_roll_dice_returns_dicex_result_and_calls_relay_correctly():
    relay = _FakeRelay(
        result={"notation": "1d6", "total": 4, "summary": "4 = 4", "groups": []}
    )
    roll = _get_roll_dice(relay)

    out = await roll("1d6")

    assert out["total"] == 4
    assert relay.calls == [("dice.roll", {"notation": "1d6"}, 30)]


async def test_roll_dice_maps_relay_error_to_error_dict():
    relay = _FakeRelay(exc=RuntimeError("Invalid dice notation: garbage"))
    roll = _get_roll_dice(relay)

    out = await roll("garbage")

    assert out == {"error": "Invalid dice notation: garbage", "notation": "garbage"}


async def test_roll_dice_maps_timeout_to_error_dict():
    relay = _FakeRelay(exc=TimeoutError("Relay did not respond to dice.roll within 30s"))
    roll = _get_roll_dice(relay)

    out = await roll("2d20kh1")

    assert out["notation"] == "2d20kh1"
    assert "did not respond" in out["error"]


async def test_roll_dice_serializes_concurrent_calls():
    started: list[str] = []
    release = asyncio.Event()

    class _BlockingRelay:
        def __init__(self) -> None:
            self.calls = 0

        async def send_request(self, method, params=None, timeout=None):
            self.calls += 1
            started.append(params["notation"])
            await release.wait()
            return {"notation": params["notation"], "total": 1}

    relay = _BlockingRelay()
    roll = _get_roll_dice(relay)

    t1 = asyncio.create_task(roll("1d6"))
    t2 = asyncio.create_task(roll("1d8"))
    await asyncio.sleep(0.05)  # let t1 acquire the lock and enter send_request

    # Second roll must be blocked on the lock — only the first reached the relay.
    assert started == ["1d6"]

    release.set()
    r1, r2 = await asyncio.gather(t1, t2)
    assert started == ["1d6", "1d8"]
    assert r1["total"] == 1 and r2["total"] == 1
