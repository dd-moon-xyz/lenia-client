.PHONY: setup run start stop restart logs

export PATH := $(HOME)/.local/bin:$(PATH)
export XDG_RUNTIME_DIR ?= /run/user/$(shell id -u)
export WAYLAND_DISPLAY ?= wayland-0
export SDL_VIDEODRIVER := wayland

setup:
	uv sync

run:
	uv run lenia-client

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
