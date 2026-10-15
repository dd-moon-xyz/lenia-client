---
type: Documentation
title: Lenia Client Setup
---

# Setup

## Display and server

CRUX uses a HyperPixel 2.1 Round display and a Wayland desktop. The client uses uv-managed Python 3.14. The desktop must run as `bastian` for the fullscreen client. Enable desktop autologin with `sudo raspi-config` if the display should work after reboot without manual login.

Following `../hprs`, add this line to `/boot/firmware/config.txt`:

```text
dtoverlay=vc4-kms-dpi-hyperpixel2r
```

Disable I2C with `sudo raspi-config nonint do_i2c 1`, then reboot. CRUX already has a working display; these steps are for a fresh installation. The hprs reference recommends archived Raspberry Pi OS `raspios_arm64-2024-11-19` because HyperPixel compatibility depends on the OS/kernel. Preserve a known working display setup when updating the Pi.

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

The [ecosystem configuration](../ecosystem.config.js) launches `~/.local/bin/uv run --no-sync lenia-client` with the project directory as its working directory. Run `make setup` first to sync the environment. It selects the Wayland driver, defaults `WAYLAND_DISPLAY` to `wayland-0`, and derives `XDG_RUNTIME_DIR` from the current user's UID. Existing values of those two variables take precedence. Output is unbuffered for PM2 logs.

PM2 restarts the client after an exit, with a three-second delay. This allows recovery from server restarts or waiting for the desktop to become available. `make start`, `make stop`, and `make restart` save the PM2 process list. They target only `lenia-client`, leaving other PM2 applications alone. Use `make stop` to keep it stopped; closing the window causes PM2 to restart it.

To change the server or supply a custom configuration, add an `args` entry to the application in `ecosystem.config.js`, then run `make restart`:

```javascript
args: ["run", "--no-sync", "lenia-client", "--url", "ws://192.168.0.15:9876/ws", "--config", "/absolute/path/config.json"],
```

The client preserves the preset FPS, population, simulation resolution, and timestep. It adds `output_size` matching the shorter display dimension, requesting 480×480 JPEGs on CRUX while retaining the 1024×1024 simulation. It adds no client FPS cap.

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

Use `uv run lenia-client --windowed` for a 480×480 window. Escape or Ctrl+C exits a foreground client. In circle mode, hold Space/C for outward steering or V for fast inward steering; release to restore inward movement.

`make run` selects Wayland and defaults to `XDG_RUNTIME_DIR=/run/user/<your UID>` and `WAYLAND_DISPLAY=wayland-0`, matching PM2. Override those variables when the desktop uses a different socket. Startup logs show the SDL driver and display size. When launching with `uv run` directly from SSH, supply these variables too; otherwise SDL may select an invisible offscreen display.

Backlight brightness is preserved by default. Optional GPIO brightness control requires `uv sync --extra gpio`, a running `pigpiod`, and `--brightness 0` through `--brightness 255`. Use `uv run --extra gpio lenia-client` for foreground runs with GPIO support; rerun `uv sync --extra gpio` after `make setup` before restarting PM2.

## Troubleshooting

Use `make logs` or `PATH="$HOME/.local/bin:$PATH" pm2 describe lenia-client` to inspect failures. For Wayland errors, check that `/run/user/1000/wayland-0` exists and belongs to the desktop user. For connection errors, check the server address and server logs. After changing Python dependencies, rerun `make setup` and `make restart`.

[Wiki index](index.md)
