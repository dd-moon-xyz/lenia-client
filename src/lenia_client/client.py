import argparse
import asyncio
import io
import json
from contextlib import suppress
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import urlopen

import pygame
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException


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
                await websocket.send(commands.get_nowait())

            await websocket.send("next")
            display_frame(screen, message)


async def run(url: str, config: dict, windowed: bool, brightness: int | None) -> None:
    gpio = None
    if brightness is not None:
        import pigpio

        gpio = pigpio.pi()
        if not gpio.connected:
            gpio.stop()
            raise ValueError("GPIO is unavailable; start pigpiod or omit --brightness")

        gpio.set_PWM_dutycycle(19, brightness)

    pygame.display.init()
    try:
        screen = pygame.display.set_mode((800, 800) if windowed else (0, 0), 0 if windowed else pygame.FULLSCREEN)
        config = {**config, "output_size": min(screen.get_size())}
        pygame.display.set_caption("Lenia client")
        pygame.mouse.set_visible(False)
        print(f"Display: {pygame.display.get_driver()} {screen.get_width()}×{screen.get_height()}", flush=True)
        commands = asyncio.Queue()
        held = {}
        steering_keys = {pygame.K_SPACE: "outward", pygame.K_c: "outward", pygame.K_v: "inward_fast"}
        stream = asyncio.create_task(display_stream(url, config, screen, commands))
        try:
            while not stream.done():
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        return

                    if config.get("boundary") == "circle":
                        if event.type == pygame.KEYDOWN and event.key in steering_keys and event.key not in held:
                            held[event.key] = steering_keys[event.key]
                            commands.put_nowait(held[event.key])

                        if event.type == pygame.KEYUP and event.key in held:
                            del held[event.key]
                            commands.put_nowait(next(reversed(held.values()), "inward"))

                        if event.type == pygame.WINDOWFOCUSLOST:
                            held.clear()
                            commands.put_nowait("inward")

                await asyncio.sleep(0.01)

            await stream
        finally:
            stream.cancel()
            with suppress(asyncio.CancelledError):
                await stream

    finally:
        pygame.display.quit()
        if gpio is not None:
            gpio.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Display the Lenia stream fullscreen on the HyperPixel")
    parser.add_argument("--url", default="ws://192.168.0.15:9876/ws")
    parser.add_argument("--config", type=Path, help="JSON start configuration; defaults to the server's /preset")
    parser.add_argument("--windowed", action="store_true", help="Use a 800×800 window instead of fullscreen")
    parser.add_argument("--brightness", type=int, choices=range(256), metavar="0-255", help="Set GPIO 19 PWM (requires the gpio extra and pigpiod)")
    args = parser.parse_args()
    try:
        config = load_preset(args.url) if args.config is None else json.loads(args.config.read_text())
        asyncio.run(run(args.url, config, args.windowed, args.brightness))
    except (OSError, ValueError, WebSocketException, pygame.error) as error:
        parser.exit(1, f"Error: {error}\n")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
