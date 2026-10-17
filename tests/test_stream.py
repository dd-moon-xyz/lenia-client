import asyncio
import json
import unittest
from unittest.mock import patch

from websockets.asyncio.server import serve

from lenia_client.client import display_stream


class StreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_requests_are_primed_and_replenished(self):
        received = []
        config = {"action": "start", "output_size": 480}

        async def server(websocket):
            received.append(json.loads(await websocket.recv()))
            await websocket.send(json.dumps({"status": "started", "size": 480, "fps": 60}))
            # Both requests must arrive before the server delivers any frame.
            for _ in range(2):
                received.append(await websocket.recv())
            for frame in (b"first", b"second", b"third"):
                await websocket.send(frame)
                received.append(await websocket.recv())
            await websocket.send(json.dumps({"status": "stopped"}))

        async with serve(server, "127.0.0.1", 0) as listener:
            port = listener.sockets[0].getsockname()[1]
            with patch("lenia_client.client.display_frame") as draw:
                await asyncio.wait_for(
                    display_stream(f"ws://127.0.0.1:{port}", config, None, asyncio.Queue()),
                    timeout=5,
                )

        self.assertEqual(received, [config, *(["next"] * 5)])
        self.assertEqual([call.args[1] for call in draw.call_args_list], [b"first", b"second", b"third"])

    async def test_structured_movement_is_sent_as_websocket_json(self):
        movement = {"action": "movement", "direction": "outward", "speed_multiplier": 1.0}
        commands = asyncio.Queue()
        commands.put_nowait(movement)
        received = []

        async def server(websocket):
            await websocket.recv()
            await websocket.send(json.dumps({"status": "started", "size": 480, "fps": 60}))
            await websocket.recv()
            await websocket.recv()
            await websocket.send(b"frame")
            received.append(json.loads(await websocket.recv()))
            self.assertEqual(await websocket.recv(), "next")
            await websocket.send(json.dumps({"status": "stopped"}))

        async with serve(server, "127.0.0.1", 0) as listener:
            port = listener.sockets[0].getsockname()[1]
            with patch("lenia_client.client.display_frame"):
                await asyncio.wait_for(display_stream(f"ws://127.0.0.1:{port}", {}, None, commands), 5)
        self.assertEqual(received, [movement])


if __name__ == "__main__":
    unittest.main()
