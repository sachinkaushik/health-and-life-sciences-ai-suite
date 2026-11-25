# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Settings from the environment (docker-compose.yaml / .env)."""

from __future__ import annotations

import os
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip() or default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


STT_URL = _env("STT_URL", "http://speech-to-text:8002")
DIARIZATION_URL = _env("DIARIZATION_URL", "http://diarization:8003")
LLM_URL = _env("LLM_URL", "http://llm:8004")
STORE_URL = _env("STORE_URL", "http://encounter-store:8001")
METRICS_URL = _env("METRICS_URL", "http://host.docker.internal:9000")

LLM_MODEL_NAME = _env("LLM_MODEL_NAME", "OpenVINO/Qwen3.5-4B-int4-ov")
LLM_TEMPERATURE = _float("LLM_TEMPERATURE", 0.7)
LLM_TOP_P = _float("LLM_TOP_P", 0.9)
LLM_REPETITION_PENALTY = _float("LLM_REPETITION_PENALTY", 1.1)
LLM_MAX_TOKENS = int(_float("LLM_MAX_TOKENS", 2048))
STT_MODEL = _env("STT_MODEL", "openai/whisper-large-v3-turbo")
STT_DEVICE = _env("STT_DEVICE", "GPU")
DIARIZATION_DEVICE = _env("DIARIZATION_DEVICE", "cpu")
LLM_DEVICE = _env("LLM_DEVICE", "GPU")

SPEAKER_MATCH_THRESHOLD = _float("SPEAKER_MATCH_THRESHOLD", 0.5)
DIARIZATION_POLL_SECONDS = 1.0
JOB_TIMEOUT_SECONDS = _float("JOB_TIMEOUT_SECONDS", 1800)
MAX_UPLOAD_BYTES = int(_float("MAX_UPLOAD_MB", 200) * 1024 * 1024)

SOAP_PROMPT_FILE = Path(_env("SOAP_PROMPT_FILE", "/configs/prompts/soap.md"))


def soap_prompt() -> str:
    """Read on every note, so an edit to configs/prompts/soap.md applies without a restart."""
    return SOAP_PROMPT_FILE.read_text(encoding="utf-8").strip()
