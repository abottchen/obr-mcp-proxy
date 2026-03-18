import asyncio
import json
import logging
import ssl
import uuid
from pathlib import Path

import websockets
from websockets.asyncio.server import Server, ServerConnection

logger = logging.getLogger(__name__)

DEFAULT_PORT = 9876
REQUEST_TIMEOUT = 10.0


class RelayConnection:
    """Manages the WebSocket connection to the OBR relay extension."""

    def __init__(self, token: str, port: int = DEFAULT_PORT, max_concurrent: int = 3) -> None:
        self._token = token
        self._port = port
        self._ws: ServerConnection | None = None
        self._server: Server | None = None
        self._pending: dict[str, asyncio.Future[dict]] = {}
        self._authenticated = False
        self._semaphore = asyncio.Semaphore(max_concurrent)

    @property
    def connected(self) -> bool:
        return self._ws is not None and self._authenticated

    async def start(self) -> None:
        ssl_ctx = self._make_ssl_context()
        self._server = await websockets.serve(
            self._handle_connection,
            "127.0.0.1",
            self._port,
            ssl=ssl_ctx,
        )
        logger.info("WSS server listening on wss://127.0.0.1:%d", self._port)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        self._reject_all_pending("Server shutting down")

    async def send_request(self, method: str, params: dict | None = None) -> dict:
        async with self._semaphore:
            if not self.connected:
                raise ConnectionError("Relay extension is not connected")

            request_id = str(uuid.uuid4())
            message = {
                "type": "request",
                "requestId": request_id,
                "method": method,
                "params": params or {},
            }

            future: asyncio.Future[dict] = asyncio.get_running_loop().create_future()
            self._pending[request_id] = future

            try:
                await self._ws.send(json.dumps(message))  # type: ignore[union-attr]
                return await asyncio.wait_for(future, timeout=REQUEST_TIMEOUT)
            except asyncio.TimeoutError:
                self._pending.pop(request_id, None)
                raise TimeoutError(
                    f"Relay did not respond to {method} within {REQUEST_TIMEOUT}s"
                )
            except Exception:
                self._pending.pop(request_id, None)
            raise

    async def _handle_connection(self, ws: ServerConnection) -> None:
        if self._ws is not None:
            await ws.close(4002, "Another relay is already connected")
            return

        logger.info("Relay extension connecting...")

        try:
            # Wait for auth message
            raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            msg = json.loads(raw)

            if msg.get("type") != "auth" or msg.get("token") != self._token:
                logger.warning("Authentication failed")
                await ws.close(4001, "Authentication failed")
                return

            self._ws = ws
            self._authenticated = True
            await ws.send(json.dumps({"type": "auth-ok"}))
            logger.info("Relay extension authenticated and connected")

            # Message loop
            async for raw_msg in ws:
                try:
                    msg = json.loads(raw_msg)
                    await self._handle_message(msg)
                except json.JSONDecodeError:
                    logger.warning("Received non-JSON message from relay")

        except asyncio.TimeoutError:
            logger.warning("Relay did not send auth message in time")
            await ws.close(4001, "Auth timeout")
        except websockets.ConnectionClosed:
            logger.info("Relay extension disconnected")
        finally:
            self._ws = None
            self._authenticated = False
            self._reject_all_pending("Relay disconnected")

    async def _handle_message(self, msg: dict) -> None:
        msg_type = msg.get("type")

        if msg_type == "response":
            request_id = msg.get("requestId")
            future = self._pending.pop(request_id, None)
            if future and not future.done():
                if msg.get("success"):
                    future.set_result(msg.get("data", {}))
                else:
                    future.set_exception(
                        RuntimeError(msg.get("error", "Unknown relay error"))
                    )
        else:
            logger.debug("Unhandled message type: %s", msg_type)

    def _reject_all_pending(self, reason: str) -> None:
        for future in self._pending.values():
            if not future.done():
                future.set_exception(ConnectionError(reason))
        self._pending.clear()

    def _make_ssl_context(self) -> ssl.SSLContext:
        certs_dir = Path(__file__).parent.parent / "certs"
        cert_file = certs_dir / "localhost.pem"
        key_file = certs_dir / "localhost-key.pem"

        if not cert_file.exists() or not key_file.exists():
            raise FileNotFoundError(
                f"TLS certs not found in {certs_dir}. Run:\n"
                f"  mkcert -cert-file {cert_file} -key-file {key_file} localhost 127.0.0.1"
            )

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert_file, key_file)
        return ctx
