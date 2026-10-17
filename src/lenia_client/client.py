import argparse
import asyncio
import io
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import urlopen

import pygame
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from lenia_client.sensors import monitor_sensors


def load_preset(url: str) -> dict:
    address = urlsplit(url)
    scheme = {"ws": "http", "wss": "https"}[address.scheme]
    path = address.path.rsplit("/", 1)[0] + "/preset"
    with urlopen(urlunsplit((scheme, address.netloc, path, "", "")), timeout=30) as response:
        return json.load(response)


def display_frame(screen: pygame.Surface, message: bytes) -> None:
    frame = pygame.image.load(io.BytesIO(message), "frame.jpg")
    scale = min(screen.get_width() / frame.get_width(), screen.get_height() / frame.get_height())
    size = tuple(max(1, round(dimension * scale)) for dimension in frame.get_size())
    if frame.get_size() != size:
        frame = pygame.transform.scale(frame, size)

    screen.fill("black")
    screen.blit(frame, frame.get_rect(center=screen.get_rect().center))
    pygame.display.flip()


async def display_stream(url: str, config: dict, screen: pygame.Surface, commands: asyncio.Queue) -> None:
    async with connect(url, max_size=4 * 1024 * 1024, max_queue=1, compression=None) as websocket:
        await websocket.send(json.dumps(config))
        async for message in websocket:
            if isinstance(message, str):
                status = json.loads(message)
                if "error" in status:
                    raise ValueError(status["error"])

                if status.get("status") == "started":
                    print(f"Streaming {status['size']}×{status['size']} at server preset {status['fps']} FPS", flush=True)
                    # Keep two requests in flight so the server can prepare the
                    # next frame while the current one is being delivered.
                    await websocket.send("next")
                    await websocket.send("next")

                if status.get("status") == "stopped":
                    return

                continue

            while not commands.empty():
                command = commands.get_nowait()
                await websocket.send(json.dumps(command) if isinstance(command, dict) else command)

            await websocket.send("next")
            display_frame(screen, message)


async def run(url: str, config: dict, windowed: bool, proximity_device: str = "/dev/i2c-1", proximity_threshold: int = 30, motion_threshold: float = 0.12) -> None:
    pygame.display.init()
    try:
        screen = pygame.display.set_mode((800, 800) if windowed else (0, 0), 0 if windowed else pygame.FULLSCREEN)
        config = {**config, "output_size": min(screen.get_size())}
        pygame.display.set_caption("Lenia client")
        pygame.mouse.set_visible(False)
        print(f"Display: {pygame.display.get_driver()} {screen.get_width()}×{screen.get_height()}", flush=True)
        commands = asyncio.Queue()
        stream = asyncio.create_task(display_stream(url, config, screen, commands))
        proximity = None
        if config.get("boundary") == "circle":
            proximity = asyncio.create_task(monitor_sensors(commands, proximity_device, proximity_threshold, motion_threshold))
        try:
            while not stream.done():
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return

                if proximity is not None and proximity.done():
                    await proximity

                await asyncio.sleep(0.01)

            await stream
        finally:
            tasks = [stream] + ([proximity] if proximity is not None else [])
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    finally:
        pygame.display.quit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Display the Lenia stream fullscreen on HDMI")
    parser.add_argument("--url", default="ws://192.168.0.15:9876/ws")
    parser.add_argument("--config", type=Path, help="JSON start configuration; defaults to the server's /preset")
    parser.add_argument("--windowed", action="store_true", help="Use a 800×800 window instead of fullscreen")
    parser.add_argument("--proximity-device", default="/dev/i2c-1", help="LTR559 Linux I²C device")
    parser.add_argument("--proximity-threshold", type=int, default=30, help="Minimum presence threshold, 2–2047 raw counts; calibrated baseline + 15 also applies")
    parser.add_argument("--motion-threshold", type=float, default=0.12, help="Acceleration change in g to trigger fast outward movement (default 0.12)")
    args = parser.parse_args()
    try:
        config = load_preset(args.url) if args.config is None else json.loads(args.config.read_text())
        asyncio.run(run(args.url, config, args.windowed, args.proximity_device, args.proximity_threshold, args.motion_threshold))
    except (OSError, ValueError, WebSocketException, pygame.error) as error:
        parser.exit(1, f"Error: {error}\n")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
