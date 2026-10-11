---
type: Documentation
title: Lenia Client Setup
---

# Setup

## Display and server

CRUX uses a HyperPixel 2.1 Round display, a Wayland desktop, and Python 3.13. The desktop must run as `bastian` for the fullscreen client. Enable desktop autologin with `sudo raspi-config` if the display should work after reboot without manual login.

Following `../hprs`, add this line to `/boot/firmware/config.txt`:

```text
dtoverlay=vc4-kms-dpi-hyperpixel2r
```

Disable I2C with `sudo raspi-config nonint do_i2c 1`, then reboot. CRUX already has a working display; these steps are for a fresh installation. The hprs reference recommends archived Raspberry Pi OS `raspios_arm64-2024-11-19` because HyperPixel compatibility depends on the OS/kernel. Preserve a known working display setup when updating the Pi.

The server must be reachable at `ws://192.168.0.15:9876/ws` and support `GET /preset` and the `output_size` start setting. The server supports concurrent viewers, each with an independent simulation and controls.

## Python environment

From `/home/bastian/projects/lenia-client`:

```bash
make setup
```

This creates `.venv` with access to system packages, reusing CRUX's installed pygame, and installs the client and WebSocket dependency. Fresh installations need Python 3.13 or newer, its venv support, and pygame. On the matching Raspberry Pi OS release, install these with `sudo apt install python3-venv python3-pygame`.

## Node.js and PM2

CRUX uses Node.js 24 LTS for ARM64 under `~/.local/share/node`, with `node`, `npm`, and `npx` linked in `~/.local/bin`. PM2 uses the same user prefix. The Makefile adds `~/.local/bin` to PATH automatically.

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

The [ecosystem configuration](../ecosystem.config.js) launches `.venv/bin/lenia-client` using the virtual environment's Python and the project directory as its working directory. It selects the Wayland driver, defaults `WAYLAND_DISPLAY` to `wayland-0`, and derives `XDG_RUNTIME_DIR` from the current user's UID. Existing values of those two variables take precedence. Output is unbuffered for PM2 logs.

PM2 restarts the client after an exit, with a three-second delay. This allows recovery from server restarts or waiting for the desktop to become available. `make start`, `make stop`, and `make restart` save the PM2 process list. They target only `lenia-client`, leaving other PM2 applications alone. Use `make stop` to keep it stopped; closing the window causes PM2 to restart it.

To change the server or supply a custom configuration, add an `args` entry to the application in `ecosystem.config.js`, then run `make restart`:

```javascript
args: "--url ws://192.168.0.15:9876/ws --config /absolute/path/config.json",
```

The client preserves the preset FPS, population, simulation resolution, and timestep. It adds `output_size` matching the shorter display dimension, requesting 480×480 JPEGs on CRUX while retaining the 1024×1024 simulation. It adds no client FPS cap.

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
XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 SDL_VIDEODRIVER=wayland make run
```

Use `--windowed` for a 480×480 window when invoking `.venv/bin/lenia-client` directly. Escape or Ctrl+C exits a foreground client. In circle mode, hold Space/C for outward steering or V for fast inward steering; release to restore inward movement.

Backlight brightness is preserved by default. Optional GPIO brightness control requires `.venv/bin/python -m pip install -e '.[gpio]'`, a running `pigpiod`, and `--brightness 0` through `--brightness 255`.

## Troubleshooting

Use `make logs` or `PATH="$HOME/.local/bin:$PATH" pm2 describe lenia-client` to inspect failures. For Wayland errors, check that `/run/user/1000/wayland-0` exists and belongs to the desktop user. For connection errors, check the server address and server logs. After changing Python dependencies, rerun `make setup` and `make restart`.

[Wiki index](index.md)
