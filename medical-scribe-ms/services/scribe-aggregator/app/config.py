# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Settings: service URLs from the environment, models / devices / sampling from
configs/model-config.yaml (the same file the model services start from)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip() or default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


STT_URL = _env("STT_URL", "http://speech-to-text:8002")
DIARIZATION_URL = _env("DIARIZATION_URL", "http://diarization:8003")
LLM_URL = _env("LLM_URL", "http://text-generation:8004")
STORE_URL = _env("STORE_URL", "http://encounter-store:8001")
METRICS_URL = _env("METRICS_URL", "http://host.docker.internal:9000")

MODEL_CONFIG_FILE = Path(_env("MODEL_CONFIG", "/configs/model-config.yaml"))
MODEL_CONFIG: dict[str, Any] = yaml.safe_load(MODEL_CONFIG_FILE.read_text(encoding="utf-8")) or {}

_stt = MODEL_CONFIG.get("speech-to-text") or {}
_diarization = MODEL_CONFIG.get("diarization") or {}
_llm = MODEL_CONFIG.get("text-generation") or {}
_generation = _llm.get("generation") or {}

STT_MODEL = str(_stt.get("model", ""))
STT_DEVICE = str(_stt.get("device", ""))
DIARIZATION_MODEL = str(_diarization.get("model", ""))
DIARIZATION_DEVICE = str(_diarization.get("device", ""))
SPEAKER_MATCH_THRESHOLD = float(_diarization.get("speaker_match_threshold", 0.5))
# Must equal the model name the text-generation service serves (it uses the repository id).
LLM_MODEL_NAME = str(_llm.get("model", ""))
LLM_DEVICE = str(_llm.get("device", ""))
LLM_TEMPERATURE = float(_generation.get("temperature", 0.7))
LLM_TOP_P = float(_generation.get("top_p", 0.9))
LLM_REPETITION_PENALTY = float(_generation.get("repetition_penalty", 1.1))
LLM_MAX_TOKENS = int(_generation.get("max_tokens", 2048))

DIARIZATION_POLL_SECONDS = 1.0
JOB_TIMEOUT_SECONDS = _float("JOB_TIMEOUT_SECONDS", 1800)
MAX_UPLOAD_BYTES = int(_float("MAX_UPLOAD_MB", 200) * 1024 * 1024)


def soap_prompt() -> str:
    """Re-read for every note, so an edit to prompts.soap applies without a restart."""
    current = yaml.safe_load(MODEL_CONFIG_FILE.read_text(encoding="utf-8")) or {}
    prompt = str((current.get("prompts") or {}).get("soap") or "").strip()
    if not prompt:
        raise RuntimeError(f"prompts.soap is empty in {MODEL_CONFIG_FILE}")
    return prompt
