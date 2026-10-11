# Lenia Client

Fullscreen Raspberry Pi client for the Lenia WebSocket server, based on `../lenia` and `../hprs`. The GPU server runs the simulation; the Pi receives and displays JPEG frames.

See the [setup wiki](wiki/setup.md) for display configuration, installation, PM2 startup, and troubleshooting.

```bash
make setup
make start
```

The client connects to `ws://192.168.0.15:9876/ws` and requests JPEGs matching the display size. Simulation resolution, population, timestep, and the preset FPS remain unchanged.

`make start`, `make stop`, `make restart`, and `make logs` manage the client through [ecosystem.config.js](ecosystem.config.js). `make run` runs it directly in the foreground.
