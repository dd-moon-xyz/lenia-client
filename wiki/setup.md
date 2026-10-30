---
type: Documentation
title: Lenia Client Setup
---

# Setup

The client is based on the sibling `../lenia` and `../hprs` projects. For physical connections, see [sensor and indicator LED wiring](wiring.md).

For the AI Camera host firmware, pretrained models, and container requirements, see [Raspberry Pi AI Camera setup](ai-camera.md).

## Display and server

The Raspberry Pi uses an 800×800 HDMI display and a Wayland desktop. The client uses uv-managed Python 3.14. The desktop must run as `bastian` for the fullscreen client. Enable desktop autologin with `sudo raspi-config` if the display should work after reboot without manual login.

Use the standard `vc4-kms-v3d` driver in `/boot/firmware/config.txt` with no DPI display overlay. HDMI should be the only enabled desktop output so fullscreen playback consistently opens there after reboot. The connected display is currently `HDMI-A-2` at 800×800.

The server must be reachable at `ws://192.168.0.15:9876/ws` and support `GET /preset` and the `output_size` start setting. The server supports concurrent viewers, each with an independent simulation and controls.

## Wi-Fi power saving

For live streaming, disable Wi-Fi power saving to test whether it contributes to intermittent frame delivery delays. Save the setting in the active NetworkManager connection and apply it immediately without reconnecting:

```bash
wifi_profile="$(nmcli -g GENERAL.CONNECTION device show wlan0)"
sudo nmcli connection modify "$wifi_profile" 802-11-wireless.powersave 2
sudo /usr/sbin/iw dev wlan0 set power_save off
```

NetworkManager value `2` disables power saving for future activations of this profile. The `iw` command disables it for the current connection. Repeat the profile change if you switch Wi-Fi networks.

Verify both settings:

```bash
nmcli -g 802-11-wireless.powersave connection show "$wifi_profile"
/usr/sbin/iw dev wlan0 get power_save
```

Expect `2 (disable)` from NetworkManager and `Power save: off` from `iw`. This setting does not establish Wi-Fi as the cause of streaming delays; compare frame timing before and after the change.

## Python environment

From `/home/bastian/projects/lenia-client`:

```bash
make setup
```

This uses the installed `uv` in `~/.local/bin` to download a uv-managed Python 3.14 and sync the client and its dependencies into `.venv`. The project requires uv-managed Python and does not inherit system Python packages or require the OS's `python3-venv` package.

The display dependency is `pygame-ce`, which supplies the `pygame` module and prebuilt Python 3.14 ARM64 wheels.

## Node.js and PM2

The Raspberry Pi uses Node.js 24 LTS for ARM64 under `~/.local/share/node`, with `node`, `npm`, and `npx` linked in `~/.local/bin`. PM2 uses the same user prefix. The Makefile adds `~/.local/bin` to PATH automatically.

On a fresh machine, install Node.js 24 LTS for its architecture from the official Node.js distribution or your preferred version manager, then install PM2:

```bash
export PATH="$HOME/.local/bin:$PATH"
npm install --global --prefix "$HOME/.local" pm2
```

## Run with PM2

```bash
make start
make logs
make restart
make stop
```

The [ecosystem configuration](../ecosystem.config.js) launches `~/.local/bin/uv run --no-sync lenia-client` with the project directory as its working directory. Run `make setup` first to sync the environment. It selects the Wayland driver, defaults `WAYLAND_DISPLAY` to `wayland-0`, and derives `XDG_RUNTIME_DIR` from the current user's UID. Existing values of those two variables take precedence. Output is unbuffered for PM2 logs.

PM2 restarts the client after an exit, with a three-second delay. This allows recovery from server restarts or waiting for the desktop to become available. `make start`, `make stop`, and `make restart` save the PM2 process list. They target only `lenia-client`, leaving other PM2 applications alone. Use `make stop` to keep it stopped; closing the window causes PM2 to restart it.

## Client configuration

All live-client settings are validated by `pydantic-settings` in `src/lenia_client/settings.py`. Edit `.env` in the project working directory; `.env.example` lists every supported setting. On a fresh checkout, copy `.env.example` to `.env`. Environment variables override the file, including in Docker. Run `make restart` after changing settings for PM2. The live client no longer accepts CLI options.

| Variable | Default | Purpose |
| --- | --- | --- |
| `LENIA_URL` | `ws://192.168.0.15:9876/ws` | WebSocket server. |
| `LENIA_CONFIG` | Unset | Optional JSON simulation start file; otherwise fetch the server preset. |
| `LENIA_WINDOWED` | `false` | Set `true` for an 800×800 window. |
| `LENIA_MOTION_DEVICE` | `/dev/i2c-1` | Motion sensor I²C device. |
| `LENIA_MOTION_THRESHOLD` | `0.12` | Positive acceleration threshold in g. |
| `LENIA_PERSON_PROXIMITY` | `0.5` | Person box height fraction; greater than 0 and less than 1. |

For example, set `LENIA_PERSON_PROXIMITY=0.35` to react farther away. These settings configure the client locally; the optional JSON file configures the server simulation.

The client preserves the preset FPS, population, simulation resolution, and timestep. It adds `output_size` matching the shorter display dimension, requesting 800×800 JPEGs on the Raspberry Pi while retaining the 1024×1024 simulation. It adds no client FPS cap.

The client keeps two frame requests in flight and replaces each request as its frame arrives. This allows the server to prepare the following frame during delivery and avoids waiting for a new round trip between simulation steps. The request count stays bounded; every received frame is displayed.

## Start after reboot

Saving the PM2 process list does not install a boot service. To enable PM2 at boot:

```bash
export PATH="$HOME/.local/bin:$PATH"
pm2 startup systemd
```

Execute the privileged command PM2 prints, then run `make start` to save the process list. This requires sudo access. The desktop must also start automatically; PM2 does not launch Wayland. Boot startup is not enabled by the Makefile.

## Foreground and controls

Stop the managed viewer before launching another one:

```bash
make stop
make run
```

Set `LENIA_WINDOWED=true` in `.env` for an 800×800 window. Ctrl+C exits a foreground client. Keyboard events are ignored by both the live client and replay.

In circle mode, the AI Camera acts as a person proximity sensor and the accelerometer/gyroscope remains active. The physical LTR559 proximity sensor is disabled in the client: it is not opened, calibrated, or polled. The [indicator LED](wiring.md#optional-blinking-led) slowly pulses while both camera and motion are clear and fades off when either triggers. Replay and non-circle presets do not open these inputs.

The camera uses pretrained SSD MobileNetV2 FPN Lite on the IMX500. Only person detections with confidence at least 0.60 count. The tallest person box determines proximity, including when multiple people are present. Escape starts after three detections with box height at least 50% of the image; it clears after three detections below 40%. This estimates closeness, not metres. See [AI Camera setup and tuning](ai-camera.md#person-proximity-control).

Tune the trigger with `LENIA_PERSON_PROXIMITY=0.35` in `.env`: lower values react farther away; higher values require a larger person in the image. Valid values are greater than 0 and less than 1; the default is `0.5`. Run `make restart` to apply changes under PM2.

Enable I²C with `sudo raspi-config` and reboot. The desktop user needs read/write access to `/dev/i2c-1` (membership in the `i2c` group; log out and back in after changing groups). The motion sensor at `0x6a` uses 104 Hz readings polled every 50 ms. Acceleration changes of at least 0.12 g or rotation of at least 20 degrees/second trigger escape. `LENIA_MOTION_THRESHOLD` adjusts the acceleration threshold; `LENIA_MOTION_DEVICE` selects the I²C device. After 250 ms without movement, the motion override clears. Keep the stick still during startup.

Either camera proximity or motion selects `outward`; the strongest active input sets speed from ×1 to ×2. Camera speed increases from ×1 at the proximity threshold to ×2 when the person box fills the image height. Motion reaches ×2 at four times its trigger threshold. Speeds are rounded to 0.01 and sent only when changed. With both inputs clear, movement is `inward` at ×1. The camera runs separately so loading or waiting for camera frames does not block motion polling. Camera failure or stale inference stops the client with an error so PM2 can retry; the LTR559 is not used as a fallback.

The WebSocket payload remains `{"action":"movement","direction":"outward","speed_multiplier":1.0}`. The server must support the structured movement API and native `m` command. The client preserves the server preset and simulation settings.

`make run` selects Wayland and defaults to `XDG_RUNTIME_DIR=/run/user/<your UID>` and `WAYLAND_DISPLAY=wayland-0`, matching PM2. Override those variables when the desktop uses a different socket. Startup logs show the SDL driver and display size. When launching with `uv run` directly from SSH, supply these variables too; otherwise SDL may select an invisible offscreen display.

## Recording and replay

`make replay` collects 30 seconds of JPEG frames at the server preset FPS on its first run, then plays them fullscreen in a continuous loop. Later runs use the saved recording without contacting the server. Playback uses a fixed frame rate and ignores capture delays. Frames are preloaded into memory and stored in `recordings/default/`, which Git ignores. Ctrl+C exits foreground playback; keyboard events are ignored.

Stop the live client with `make stop` before replay so both processes do not use the display at once. Use `make replay-start`, `make replay-stop`, `make replay-restart`, and `make replay-logs` to manage replay through PM2. PM2 saves the process list for startup restoration and restarts replay after an exit, including closing its window; use `make replay-stop` to keep it stopped.

Run `make collect` to collect a fresh recording without opening a display, then `make replay` to play it. Every collection deletes previous JPEG frames and the manifest in the selected directory before contacting the server.

For custom collection settings:

```bash
uv run lenia-collect --seconds 30 --output-size 800 --directory recordings/new
```

The collector also accepts `--url` and `--config`. Use `uv run lenia-replay --windowed` for a window, or `--directory recordings/new` to select another recording directory (capturing if no recording exists). Replay also accepts `--url`, `--config`, and `--seconds` (default 30).

## Troubleshooting

Use `make logs` or `PATH="$HOME/.local/bin:$PATH" pm2 describe lenia-client` to inspect failures. For Wayland errors, check that `/run/user/1000/wayland-0` exists and belongs to the desktop user. For connection errors, check the server address and server logs. After changing Python dependencies, rerun `make setup` and `make restart`.


[Wiki index](index.md)
