# Lenia Client

Fullscreen Raspberry Pi client for the Lenia WebSocket server, based on `../lenia` and `../hprs`. The GPU server runs the simulation; the Pi receives and displays JPEG frames.

See the [setup wiki](wiki/setup.md) for display configuration, installation, PM2 startup, and troubleshooting.

Python and dependencies are managed by the installed `uv` in `~/.local/bin`, using uv-managed Python 3.14.

```bash
make setup
make start
```

The client connects to `ws://192.168.0.15:9876/ws` and requests JPEGs matching the display size. Simulation resolution, population, timestep, and the preset FPS remain unchanged.

`make start`, `make stop`, `make restart`, and `make logs` manage the client through [ecosystem.config.js](ecosystem.config.js). `make run` runs it directly in the foreground.

`make replay` collects 30 seconds worth of JPEG frames at the server's preset FPS on its first run, then plays them
fullscreen in a continuous loop. Later runs use the saved recording without
contacting the server. Playback uses a fixed frame rate and ignores capture delays.
Frames are preloaded into memory and stored in
`recordings/default/`, which Git ignores. Use Ctrl+C to exit foreground playback. Keyboard events are ignored.

To run replay through PM2, use `make replay-start`. Use `make replay-stop`,
`make replay-restart`, and `make replay-logs` to manage it. Stop the live client
with `make stop` before starting replay so both processes do not use the display
at the same time. PM2 saves the process list for startup restoration and restarts
replay if it exits, including when its window is closed; use `make replay-stop` to
keep it stopped.

Run `make collect` to collect a fresh recording without opening a display,
then `make replay` to play it. Every collection deletes all previous JPEG frames
and the manifest in the selected directory before contacting the server.
For custom settings, use
`uv run lenia-collect --seconds 30 --output-size 800 --directory recordings/new`.
The collector also accepts `--url` and `--config`.
Use `uv run lenia-replay --windowed` for a window, or `--directory recordings/new`
to capture a fresh recording. The script also accepts `--url`, `--config`, and
`--seconds` (default 30).

In circle mode, the live client uses the LTR559 proximity sensor to steer organisms outward while an object is detected and inward when it clears. Keyboard steering is disabled. See the setup wiki for I²C access and sensitivity settings.
