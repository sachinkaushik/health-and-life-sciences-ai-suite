# syntax=docker/dockerfile:1.7
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
# Speaker diarization: pyannote speaker-diarization-community-1, doctor voice embeddings, live
# diarization. Installed from the pinned uv workspace in libs/workers. Build context: the app root.

ARG BASE_IMAGE=intel/hl-ai-medical-scribe-base:latest
FROM ${BASE_IMAGE}

COPY --chown=appuser:appuser libs/scripts/bash scripts/bash
COPY --chown=appuser:appuser libs/workers workers
COPY --chown=appuser:appuser libs/scripts/model_config.py scripts/model_config.py

RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=1000,gid=1000 \
    workers/upstream-setup.sh fetch common/downloader \
    && uv sync --frozen --inexact --project workers --package diarization

ENV SERVER_HOST=0.0.0.0
WORKDIR /opt/medical-scribe/workers/services/diarization

EXPOSE 8003
# Device: configs/model-config.yaml (diarization).
CMD ["sh", "-c", "eval \"$(/opt/medical-scribe/workers/.venv/bin/python /opt/medical-scribe/scripts/model_config.py diarization)\" && exec /opt/medical-scribe/workers/.venv/bin/python main.py --port=8003 --device=\"$DEVICE\" --source=huggingface --instance-id=diarization --data-dir=/opt/medical-scribe/data/diarization"]
