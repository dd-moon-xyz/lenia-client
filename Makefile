.PHONY: setup run start stop restart logs

export PATH := $(HOME)/.local/bin:$(PATH)

setup:
	python3 -m venv --system-site-packages .venv
	.venv/bin/python -m pip install -e .

run:
	.venv/bin/lenia-client

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
