# Lenia Client

Fullscreen Raspberry Pi viewer for the Lenia WebSocket server. The GPU server runs the simulation; the Pi displays JPEG frames and sends camera-based person proximity and motion controls.

```bash
make setup
make start
```

See the [wiki](wiki/index.md) for installation, configuration, sensor wiring, recording, replay, and troubleshooting.

Configure the live client in `.env`; [.env.example](.env.example) lists all settings. Environment variables override the file. Set `LENIA_PERSON_PROXIMITY` lower to react to people farther away (default `0.5`).
