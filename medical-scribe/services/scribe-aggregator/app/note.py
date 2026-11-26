# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""SOAP note generation: the labelled transcript and the SOAP prompt (prompts.soap in
configs/model-config.yaml) to the LLM, streamed back as server-sent events and saved with its
timings once complete."""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from . import clients, config

log = logging.getLogger("scribe.note")

_FENCE = re.compile(r"^```(?:\s*(?:markdown|md))?\s*\r?\n", re.IGNORECASE)


def strip_markdown_fence(text: str) -> str:
    """Removes the ```markdown fence some models wrap the note in."""
    trimmed = text.lstrip()
    match = _FENCE.match(trimmed)
    if not match:
        return text
    return re.sub(r"(?:\r?\n)?```\s*$", "", trimmed[match.end() :])


def dialogue(transcript: list[dict[str, Any]]) -> str:
    return "\n\n".join(f"{t.get('speaker') or 'Speaker'}: {t.get('text', '').strip()}" for t in transcript)


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def generate(encounter: dict[str, Any]) -> AsyncIterator[str]:
    encounter_id = encounter["id"]
    started = time.perf_counter()
    first_token_s: float | None = None
    parts: list[str] = []
    usage: dict[str, Any] = {}
    try:
        async for chunk in clients.chat_stream(config.soap_prompt(), dialogue(encounter["transcript"])):
            if chunk.get("usage"):
                usage = chunk["usage"]
            for choice in chunk.get("choices") or []:
                delta = (choice.get("delta") or {}).get("content") or ""
                if delta:
                    if first_token_s is None:
                        first_token_s = time.perf_counter() - started
                    parts.append(delta)
                    yield _sse("delta", {"text": delta})
        note = strip_markdown_fence("".join(parts)).strip()
        total_s = time.perf_counter() - started
        tokens = int(usage.get("completion_tokens") or 0)
        timings: dict[str, float] = {"note_seconds": round(total_s, 2)}
        if first_token_s is not None:
            timings["note_ttft_seconds"] = round(first_token_s, 3)
        if tokens:
            timings["note_tokens"] = float(tokens)
            gen_s = total_s - (first_token_s or 0)
            if gen_s > 0:
                timings["note_tokens_per_second"] = round(tokens / gen_s, 1)
        if not note:
            raise clients.ServiceError("The model returned an empty note")
        saved = await clients.update_encounter(
            encounter_id,
            note=note,
            reviewed=False,
            timings=timings,
            noted_at=datetime.now(timezone.utc).isoformat(),
        )
        yield _sse("done", {"note": note, "timings": saved.get("timings", timings)})
        log.info("encounter %s note written: %s", encounter_id, timings)
    except clients.ServiceError as exc:
        yield _sse("error", {"message": str(exc)})
    except Exception:  # noqa: BLE001
        log.exception("note for %s failed", encounter_id)
        yield _sse("error", {"message": "Note generation failed"})
