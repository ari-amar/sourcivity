"""WebSocket client for OpenClaw agent gateway.
Used ONLY for: (a) unclassified chat fallback, (b) Telegram notifications."""
import asyncio
import json
import uuid

try:
    from websockets.asyncio.client import connect
except ImportError:
    connect = None

from config import GATEWAY_WS_URL, GATEWAY_TOKEN, SESSION_KEY_PREFIX


async def send_to_agent(message, session=None):
    """Send a message to the OpenClaw agent via WebSocket and get the response."""
    if connect is None:
        return "Error: websockets not installed. Run: pip install websockets"

    async with connect(GATEWAY_WS_URL) as ws:
        # Step 1: Receive connect challenge
        challenge = json.loads(await ws.recv())

        # Step 2: Send connect request with token auth
        await ws.send(json.dumps({
            "type": "req",
            "id": "1",
            "method": "connect",
            "params": {
                "minProtocol": 3,
                "maxProtocol": 3,
                "client": {
                    "id": "cli",
                    "version": "1.0.0",
                    "platform": "linux",
                    "mode": "backend"
                },
                "role": "operator",
                "scopes": ["operator.read", "operator.write", "operator.admin"],
                "caps": [],
                "commands": [],
                "permissions": {},
                "auth": {
                    "token": GATEWAY_TOKEN
                }
            }
        }))

        # Step 3: Wait for hello-ok
        hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        if not hello.get("ok"):
            error = hello.get("error", {})
            return f"Connection failed: {error.get('message', str(error))}"

        # Step 4: Send chat message
        await ws.send(json.dumps({
            "type": "req",
            "id": "2",
            "method": "chat.send",
            "params": {
                "sessionKey": SESSION_KEY_PREFIX + (session if session else str(uuid.uuid4())[:8]),
                "idempotencyKey": str(uuid.uuid4()),
                "message": message
            }
        }))

        # Step 5: Collect agent response
        full_text = ""
        for i in range(500):
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=300))
            except asyncio.TimeoutError:
                return full_text or "Operation timed out."

            msg_type = msg.get("type", "")
            event = msg.get("event", "")
            payload = msg.get("payload", {})

            if msg_type == "res":
                continue

            if not isinstance(payload, dict):
                continue

            if msg_type == "event" and event == "agent":
                stream = payload.get("stream", "")
                data = payload.get("data", {})

                if stream == "assistant" and isinstance(data, dict):
                    snapshot = data.get("text", "")
                    if snapshot:
                        full_text = snapshot

                if stream == "lifecycle" and isinstance(data, dict):
                    if data.get("phase") == "error":
                        continue

            if msg_type == "event" and event == "chat":
                state = payload.get("state", "")
                if state in ("final", "idle", "done", "complete") and full_text:
                    return full_text
                if state == "error" and not full_text:
                    return f"Chat error: {payload.get('errorMessage', 'Unknown')}"

            if event in ("tick", "health"):
                continue

        return full_text or "No response received"


def send_to_agent_sync(message, session=None):
    """Synchronous wrapper around send_to_agent."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(send_to_agent(message, session))
    finally:
        loop.close()
