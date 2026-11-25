# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
# Medical Scribe: `make setup`, `make build`, `make up`. See README.md.

SHELL := /bin/bash
ENV_FILE := .env
COMPOSE := docker compose --env-file $(ENV_FILE)
REGISTRY ?= $(shell grep -s '^REGISTRY=' $(ENV_FILE) | cut -d= -f2)
TAG ?= $(shell grep -s '^TAG=' $(ENV_FILE) | cut -d= -f2)
BASE_IMAGE = $(or $(REGISTRY),intel/)hl-ai-medical-scribe-base:$(or $(TAG),latest)

.DEFAULT_GOAL := help
.PHONY: help setup build build-base up down restart logs status import-models

help: ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

setup: ## Create .env (device groups, NPU) and the host folders
	@test -f $(ENV_FILE) || { cp .env.example $(ENV_FILE); chmod 600 $(ENV_FILE); echo "Created $(ENV_FILE)"; }
	@grep -q '^RENDER_GID=.\+' $(ENV_FILE) || sed -i "s/^RENDER_GID=.*/RENDER_GID=$$(getent group render | cut -d: -f3)/" $(ENV_FILE)
	@grep -q '^VIDEO_GID=.\+' $(ENV_FILE) || sed -i "s/^VIDEO_GID=.*/VIDEO_GID=$$(getent group video | cut -d: -f3)/" $(ENV_FILE)
	@if [ -e /dev/accel/accel0 ]; then sed -i "s|^NPU_DEVICE=.*|NPU_DEVICE=/dev/accel/accel0|" $(ENV_FILE); fi
	@mkdir -p models logs metrics data/encounter-store data/speech-to-text data/diarization
	@grep -q '^HF_TOKEN=.\+' $(ENV_FILE) || echo "Set HF_TOKEN in $(ENV_FILE) before 'make up' (diarization needs it on every start)."
	@echo "Setup done."

build-base: setup ## Build the shared GPU/NPU runtime image
	docker build -f docker/base.Dockerfile -t $(BASE_IMAGE) \
		--build-arg http_proxy --build-arg https_proxy --build-arg no_proxy .

build: build-base ## Build every image
	$(COMPOSE) build

up: setup ## Start every service and wait until they are healthy
	@grep -q '^HF_TOKEN=.\+' $(ENV_FILE) || { echo "HF_TOKEN is empty in $(ENV_FILE)."; exit 1; }
	$(COMPOSE) up -d --wait
	@source $(ENV_FILE) && echo "Medical Scribe: http://$${BIND_ADDRESS:-127.0.0.1}:$${UI_PORT:-8080}"

down: ## Stop and remove the containers (models and data stay)
	$(COMPOSE) down

restart: ## Restart every service
	$(COMPOSE) restart

logs: ## Follow the logs (make logs SERVICE=scribe-aggregator for one)
	$(COMPOSE) logs -f --tail=100 $(SERVICE)

status: ## Container state and health
	$(COMPOSE) ps --format 'table {{.Service}}\t{{.State}}\t{{.Status}}'

import-models: setup ## Reuse models already downloaded by the Demo Studio app (FROM=<its models dir>)
	@test -n "$(FROM)" || { echo "Usage: make import-models FROM=../medical-scribe/models"; exit 1; }
	@for d in stt diarization huggingface; do \
		if [ -d "$(FROM)/$$d" ]; then cp -al "$(FROM)/$$d" models/ 2>/dev/null || cp -a "$(FROM)/$$d" models/; echo "imported $$d"; fi; \
	done
	@src="$(FROM)/multiserve/text-generation/OV/text_generation"; \
	if [ -d "$$src" ]; then mkdir -p models/llm && \
		rsync -a --link-dest="$$(realpath $$src)" --exclude graph.pbtxt --exclude .git "$$src/" models/llm/ && echo "imported llm"; fi
