.PHONY: setup run collect replay start stop restart logs replay-start replay-stop replay-restart replay-logs

export PATH := $(HOME)/.local/bin:$(PATH)
export XDG_RUNTIME_DIR ?= /run/user/$(shell id -u)
export WAYLAND_DISPLAY ?= wayland-0
export SDL_VIDEODRIVER := wayland

setup:
	uv sync

run:
	uv run lenia-client

replay:
	uv run lenia-replay

collect:
	uv run lenia-collect

start:
	pm2 start ecosystem.config.js --only lenia-client
	pm2 save

stop:
	pm2 stop lenia-client
	pm2 save

restart:
	pm2 restart ecosystem.config.js --only lenia-client --update-env
	pm2 save

logs:
	pm2 logs lenia-client

replay-start:
	pm2 start ecosystem.config.js --only lenia-replay
	pm2 save

replay-stop:
	pm2 stop lenia-replay
	pm2 save

replay-restart:
	pm2 restart ecosystem.config.js --only lenia-replay --update-env
	pm2 save

replay-logs:
	pm2 logs lenia-replay
