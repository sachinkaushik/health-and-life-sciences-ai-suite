# Medical Scribe: `make setup`, `make download-models`, `make run`.
SHELL := /bin/bash

BACKEND ?= sycl
CONFIG  ?= configs/models.yaml
MODELS  ?=
PY      := workers/.venv/bin/python

.PHONY: help setup download-models list-models run

help:
	@echo "make setup             install tools, Python envs and frontend (BACKEND=$(BACKEND))"
	@echo "make download-models   download models from $(CONFIG) (MODELS=name1,name2 to pick)"
	@echo "make list-models       show model folders and their size"
	@echo "make run               start the web UI (port from frontend/.env)"

setup:
	bash scripts/setup.sh --backend $(BACKEND)
	@[ -f frontend/.env ] || cp frontend/.env.example frontend/.env

$(PY):
	@echo "Run 'make setup' first"; exit 1

download-models: $(PY)
	$(PY) scripts/download_models.py --config $(CONFIG) $(if $(MODELS),--only $(MODELS))

list-models:
	@du -sh models/*/ models/multiserve/text-generation/OV/*/ models/diarization/*/*/ 2>/dev/null || echo "No models downloaded yet"

run:
	bash scripts/start.sh
