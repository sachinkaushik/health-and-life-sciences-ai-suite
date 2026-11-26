# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Clients for the services behind the aggregator. All internal: no proxy from the environment."""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

import httpx

from . import config


class ServiceError(RuntimeError):
    """A downstream service failed; the message is safe to show."""


_http: httpx.AsyncClient | None = None


def http() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(600, connect=10))
    return _http


async def close() -> None:
    if _http is not None:
        await _http.aclose()


def _check(resp: httpx.Response, what: str) -> None:
    if resp.status_code >= 400:
        detail = resp.text[:300]
        raise ServiceError(f"{what} failed ({resp.status_code}): {detail}")


# -------------------------------------------------------------------- store --
async def store(method: str, path: str, **kwargs: Any) -> Any:
    resp = await http().request(method, f"{config.STORE_URL}{path}", **kwargs)
    if resp.status_code == 404:
        raise LookupError(path)
    _check(resp, "Encounter store")
    return None if resp.status_code == 204 else resp.json()


async def update_encounter(encounter_id: str, **fields: Any) -> dict[str, Any]:
    return await store("PATCH", f"/v1/encounters/{encounter_id}", json=fields)


# ------------------------------------------------------------ speech-to-text --
async def transcribe(
    audio: bytes, filename: str, language: str, doctor_embedding: list[float] | None
) -> dict[str, Any]:
    """verbose_json with speakers: audio-analyzer diarizes the whole file. With an enrolled doctor,
    the matching voice's segments carry speaker_label "Doctor"."""
    data: dict[str, str | list[str]] = {
        "model": "whisper-1",
        "response_format": "verbose_json",
        "language": language or "auto",
        "diarization_mode": "file",
        "num_speakers": str(config.NUM_SPEAKERS),
    }
    if doctor_embedding:
        data["speaker_profiles"] = json.dumps([{"label": "Doctor", "embedding": doctor_embedding}])
        data["speaker_match_threshold"] = str(config.SPEAKER_MATCH_THRESHOLD)
    resp = await http().post(
        f"{config.STT_URL}/v1/audio/transcriptions",
        data=data,
        files={"file": (filename, audio)},
        timeout=httpx.Timeout(config.JOB_TIMEOUT_SECONDS, connect=10),
    )
    _check(resp, "Speech to text")
    return resp.json()


async def voice_embedding(audio: bytes, filename: str) -> list[float]:
    resp = await http().post(f"{config.STT_URL}/v1/audio/speaker-embedding", files={"file": (filename, audio)})
    if resp.status_code == 422:
        raise ServiceError("No speech was found in the voice sample")
    _check(resp, "Voice enrolment")
    return list(resp.json()["embedding"])


# ---------------------------------------------------------- text-generation --
async def chat_stream(system: str, user: str) -> AsyncIterator[dict[str, Any]]:
    """OVMS OpenAI chat completions, streamed: yields each chunk; the last carries usage."""
    body = {
        "model": config.LLM_MODEL_NAME,
        "stream": True,
        "stream_options": {"include_usage": True},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": config.LLM_TEMPERATURE,
        "top_p": config.LLM_TOP_P,
        "repetition_penalty": config.LLM_REPETITION_PENALTY,
        "max_tokens": config.LLM_MAX_TOKENS,
        "chat_template_kwargs": {"enable_thinking": False},
        # With thinking off a `</think>` is an artifact Qwen3.5 int4 may repeat to the limit.
        "stop": ["</think>"],
    }
    async with http().stream("POST", f"{config.LLM_URL}/v3/chat/completions", json=body) as resp:
        if resp.status_code >= 400:
            await resp.aread()
            _check(resp, "Note generation")
        async for line in resp.aiter_lines():
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                return
            yield json.loads(payload)


# ------------------------------------------------------------------- health --
HEALTH_CHECKS = {
    "speech-to-text": ("Speech to text", lambda: f"{config.STT_URL}/health"),
    "text-generation": ("Clinical note writer", lambda: f"{config.LLM_URL}/v2/health/ready"),
    "encounter-store": ("Encounter store", lambda: f"{config.STORE_URL}/healthz"),
}


async def service_status() -> list[dict[str, Any]]:
    async def probe(service_id: str, label: str, url: str) -> dict[str, Any]:
        try:
            resp = await http().get(url, timeout=5)
            ready = resp.status_code == 200
        except httpx.HTTPError:
            ready = False
        return {"id": service_id, "label": label, "ready": ready}

    return list(
        await asyncio.gather(*(probe(sid, label, url()) for sid, (label, url) in HEALTH_CHECKS.items()))
    )
