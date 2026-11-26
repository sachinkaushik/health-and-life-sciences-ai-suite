# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
# Medical Scribe: `make setup`, `make up` (REGISTRY=false to build from source). See README.md.

SHELL := /bin/bash
ENV_FILE := .env
COMPOSE := docker compose --env-file $(ENV_FILE)
env_value = $(shell grep -s '^$(1)=' $(ENV_FILE) | cut -d= -f2)

# true: run the published images; false: build them from source.
REGISTRY ?= $(or $(call env_value,REGISTRY),true)
REGISTRY_URL ?= $(or $(call env_value,REGISTRY_URL),intel/)
TAG ?= $(or $(call env_value,TAG),latest)
export REGISTRY_URL TAG

.DEFAULT_GOAL := help
.PHONY: help setup build pull download-models up down restart logs status

help: ## List the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

setup: ## Create .env (device groups, NPU) and the host folders
	@test -f $(ENV_FILE) || { cp .env.example $(ENV_FILE); chmod 600 $(ENV_FILE); echo "Created $(ENV_FILE)"; }
	@grep -q '^RENDER_GID=.\+' $(ENV_FILE) || sed -i "s/^RENDER_GID=.*/RENDER_GID=$$(getent group render | cut -d: -f3)/" $(ENV_FILE)
	@grep -q '^VIDEO_GID=.\+' $(ENV_FILE) || sed -i "s/^VIDEO_GID=.*/VIDEO_GID=$$(getent group video | cut -d: -f3)/" $(ENV_FILE)
	@if [ -e /dev/accel/accel0 ]; then sed -i "s|^NPU_DEVICE=.*|NPU_DEVICE=/dev/accel/accel0|" $(ENV_FILE); fi
	@mkdir -p models logs metrics data/encounter-store data/speech-to-text
	@grep -q '^HF_TOKEN=.\+' $(ENV_FILE) || echo "Set HF_TOKEN in $(ENV_FILE) before 'make up' (speaker diarization needs it on every start)."
	@echo "Setup done."

build: setup ## Build the app images from source
	$(COMPOSE) build

pull: setup ## Pull the published images (REGISTRY_URL, TAG; OVMS, metrics)
	$(COMPOSE) pull --ignore-pull-failures

download-models: setup ## Download the models in configs/model-config.yaml (OEP model-download)
	@grep -q '^HF_TOKEN=.\+' $(ENV_FILE) || { echo "HF_TOKEN is empty in $(ENV_FILE)."; exit 1; }
	$(COMPOSE) --profile download up -d --wait model-download
	@status=0; \
	$(COMPOSE) run --rm --no-deps -e AUDIO_ANALYZER_MODEL_DOWNLOAD_URL=http://model-download:8000 \
		-e AUDIO_ANALYZER_MODEL_DIRECT_DOWNLOAD=false speech-to-text download || status=$$?; \
	[ $$status -ne 0 ] || $(COMPOSE) --profile download exec -T model-download \
		/opt/.venv/bin/python /opt/scribe/download_llm.py || status=$$?; \
	$(COMPOSE) --profile download rm -sf model-download; \
	exit $$status

up: setup ## Start every service and wait until healthy (REGISTRY=true|false)
	@grep -q '^HF_TOKEN=.\+' $(ENV_FILE) || { echo "HF_TOKEN is empty in $(ENV_FILE)."; exit 1; }
	@if [ "$(REGISTRY)" = "true" ]; then \
		echo "Using registry images ($(REGISTRY_URL)hl-ai-medical-scribe-*:$(TAG))..."; \
		$(COMPOSE) up -d --wait --pull missing --no-build --remove-orphans; \
	else \
		echo "Building local images from source..."; \
		$(COMPOSE) up -d --wait --build --remove-orphans; \
	fi
	@source $(ENV_FILE) && echo "Medical Scribe: http://$${BIND_ADDRESS:-127.0.0.1}:$${UI_PORT:-8080}"

down: ## Stop and remove the containers (models and data stay)
	$(COMPOSE) down

restart: ## Restart every service
	$(COMPOSE) restart

logs: ## Follow the logs (make logs SERVICE=scribe-aggregator for one)
	$(COMPOSE) logs -f --tail=100 $(SERVICE)

status: ## Container state and health
	$(COMPOSE) ps --format 'table {{.Service}}\t{{.State}}\t{{.Status}}'
