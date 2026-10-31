---
type: Documentation
title: Run with PM2
---

# Run with PM2

```bash
make start
make logs
make restart
make stop
```

The [ecosystem configuration](../../ecosystem.config.js) launches `~/.local/bin/uv run --no-sync lenia-client` with the project directory as its working directory. Run `make setup` first to sync the environment. It selects the Wayland driver, defaults `WAYLAND_DISPLAY` to `wayland-0`, and derives `XDG_RUNTIME_DIR` from the current user's UID. Existing values of those two variables take precedence. Output is unbuffered for PM2 logs.

PM2 restarts the client after an exit, with a three-second delay. This allows recovery from server restarts or waiting for the desktop to become available. `make start`, `make stop`, and `make restart` save the PM2 process list. They target only `lenia-client`, leaving other PM2 applications alone. Use `make stop` to keep it stopped; closing the window causes PM2 to restart it.

[Section index](index.md) · [Wiki index](../index.md)
