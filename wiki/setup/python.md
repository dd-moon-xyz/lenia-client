---
type: Documentation
title: Python environment
---

# Python environment

From `/home/bastian/projects/lenia-client`:

```bash
make setup
```

This uses the installed `uv` in `~/.local/bin` to download a uv-managed Python 3.14 and sync the client and its dependencies into `.venv`. The project requires uv-managed Python and does not inherit system Python packages or require the OS's `python3-venv` package.

The display dependency is `pygame-ce`, which supplies the `pygame` module and prebuilt Python 3.14 ARM64 wheels.

[Section index](index.md) · [Wiki index](../index.md)
