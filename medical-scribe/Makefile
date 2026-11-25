# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
# Medical Scribe as containers (docker/docker-compose.yaml). The native flow (./setup.sh, ./start.sh)
# is unchanged. Stop the native app before `make up`: both use port 8080 and the same GPU.

SHELL := /bin/bash
ENV_FILE := docker/.env
COMPOSE := docker compose -f docker/docker-compose.yaml --env-file $(ENV_FILE)

.DEFAULT_GOAL := help
.PHONY: help setup build up down restart logs status ps

help: ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-8s %s\n", $$1, $$2}'

setup: ## Create docker/.env (secret, device groups) and the host folders
	@test -f $(ENV_FILE) || { cp docker/.env.example $(ENV_FILE); chmod 600 $(ENV_FILE); echo "Created $(ENV_FILE)"; }
	@grep -q '^PAYLOAD_SECRET=.\+' $(ENV_FILE) || sed -i "s/^PAYLOAD_SECRET=.*/PAYLOAD_SECRET=$$(openssl rand -hex 32)/" $(ENV_FILE)
	@grep -q '^RENDER_GID=.\+' $(ENV_FILE) || sed -i "s/^RENDER_GID=.*/RENDER_GID=$$(getent group render | cut -d: -f3)/" $(ENV_FILE)
	@grep -q '^VIDEO_GID=.\+' $(ENV_FILE) || sed -i "s/^VIDEO_GID=.*/VIDEO_GID=$$(getent group video | cut -d: -f3)/" $(ENV_FILE)
	@if [ -e /dev/accel/accel0 ]; then sed -i "s|^NPU_DEVICE=.*|NPU_DEVICE=/dev/accel/accel0|" $(ENV_FILE); fi
	@mkdir -p models logs data/ui
	@echo "Setup done."
	@grep -q '^HF_TOKEN=.\+' $(ENV_FILE) || echo "Set HF_TOKEN in $(ENV_FILE) before 'make up': diarization (gated pyannote model) needs it on every start."

build: setup ## Build the images
	$(COMPOSE) build

up: setup ## Start every service and wait until they are healthy
	@grep -q '^HF_TOKEN=.\+' $(ENV_FILE) || { echo "HF_TOKEN is empty in $(ENV_FILE). Add a Hugging Face token with the pyannote/speaker-diarization-community-1 terms accepted."; exit 1; }
	$(COMPOSE) up -d --wait
	@source $(ENV_FILE) && echo "Medical Scribe: http://127.0.0.1:$${UI_PORT:-8080}"

down: ## Stop and remove the containers (models and data stay)
	$(COMPOSE) down

restart: ## Restart every service
	$(COMPOSE) restart

logs: ## Follow the logs (make logs SERVICE=speech-to-text for one)
	$(COMPOSE) logs -f --tail=100 $(SERVICE)

status: ## Container state and health
	$(COMPOSE) ps --format 'table {{.Service}}\t{{.State}}\t{{.Status}}'

ps: status
