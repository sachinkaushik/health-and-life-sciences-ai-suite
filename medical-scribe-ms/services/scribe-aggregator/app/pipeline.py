# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""The encounter pipeline: speech to text with speakers (audio-analyzer diarizes the whole file and
recognises the enrolled doctor), then the labelled transcript and timings saved to the encounter
store. Runs as a server-side task, so it finishes even when the browser that started it is closed."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

from . import clients

log = logging.getLogger("scribe.pipeline")

_CJK = re.compile("[\u3000-\u303f\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff01-\uff65]")

_tasks: dict[str, asyncio.Task[None]] = {}


def is_running(encounter_id: str) -> bool:
    task = _tasks.get(encounter_id)
    return task is not None and not task.done()


def cancel(encounter_id: str) -> None:
    task = _tasks.pop(encounter_id, None)
    if task is not None:
        task.cancel()


def start(encounter_id: str, audio: bytes, filename: str) -> None:
    cancel(encounter_id)
    task = asyncio.create_task(_run(encounter_id, audio, filename), name=f"pipeline-{encounter_id}")
    _tasks[encounter_id] = task
    task.add_done_callback(lambda t: _tasks.pop(encounter_id, None) if _tasks.get(encounter_id) is t else None)


async def _timed(coro: Any) -> tuple[Any, float]:
    started = time.perf_counter()
    result = await coro
    return result, time.perf_counter() - started


def _join(left: str, right: str) -> str:
    """Joins with a space, except next to CJK characters."""
    if not left or not right:
        return left or right
    return left + ("" if _CJK.match(left[-1]) or _CJK.match(right[0]) else " ") + right


def _speaker_names(segments: list[dict[str, Any]]) -> dict[str, str]:
    """Doctor / Patient when the enrolled doctor was recognised, else Speaker 1, 2, … in speaking order."""
    order = list(dict.fromkeys(s["speaker"] for s in segments if s.get("speaker")))
    doctor = {s["speaker"] for s in segments if s.get("speaker") and s.get("speaker_label") == "Doctor"}
    if doctor:
        return {sid: "Doctor" if sid in doctor else "Patient" for sid in order}
    return {sid: f"Speaker {i + 1}" for i, sid in enumerate(order)}


def labelled_transcript(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Consecutive segments of one speaker merged into one entry."""
    names = _speaker_names(segments)
    entries: list[dict[str, Any]] = []
    for segment in segments:
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        # A segment no speaker turn overlapped stays with the previous speaker.
        speaker = names.get(segment.get("speaker") or "") or (entries[-1]["speaker"] if entries else "Speaker")
        start, end = float(segment.get("start", 0)), float(segment.get("end", 0))
        if entries and entries[-1]["speaker"] == speaker:
            entries[-1]["text"] = _join(entries[-1]["text"], text)
            entries[-1]["end"] = end
        else:
            entries.append({"speaker": speaker, "text": text, "start": start, "end": end})
    return entries


async def _run(encounter_id: str, audio: bytes, filename: str) -> None:
    try:
        encounter = await clients.update_encounter(encounter_id, status="processing", error=None)
        embedding = None
        if encounter.get("doctor_id"):
            try:
                doctor = await clients.store("GET", f"/v1/doctors/{encounter['doctor_id']}")
                embedding = doctor.get("embedding")
            except LookupError:
                pass

        stt, stt_s = await _timed(
            clients.transcribe(audio, filename, encounter.get("language") or "auto", embedding)
        )
        segments = list(stt.get("segments") or [])
        text = str(stt.get("text") or "").strip()
        transcript = labelled_transcript(segments)
        if not transcript and text:
            end = float(segments[-1].get("end", 0)) if segments else 0.0
            transcript = [{"speaker": "Speaker", "text": text, "start": 0.0, "end": end}]

        audio_s = float(stt.get("duration") or (segments[-1].get("end", 0) if segments else 0.0))
        timings: dict[str, Any] = {
            "audio_seconds": round(audio_s, 2),
            "stt_seconds": round(stt_s, 2),
            # Speakers are now part of speech to text; clears the separate stage of older runs.
            "diarization_seconds": None,
            "diarization_rtf": None,
            "align_seconds": None,
        }
        if audio_s > 0:
            timings["stt_rtf"] = round(stt_s / audio_s, 3)
        # A note written from the previous transcript no longer matches this one.
        stale_note = {k: None for k in ("note_seconds", "note_ttft_seconds", "note_tokens", "note_tokens_per_second")}
        await clients.update_encounter(
            encounter_id,
            status="transcribed",
            transcript=transcript,
            timings={**timings, **stale_note},
            note=None,
            noted_at=None,
            reviewed=False,
            transcribed_at=datetime.now(timezone.utc).isoformat(),
        )
        log.info("encounter %s transcribed: %s", encounter_id, timings)
    except asyncio.CancelledError:
        raise
    except LookupError:
        log.info("encounter %s was deleted while processing", encounter_id)
    except Exception as exc:  # noqa: BLE001 - any failure is shown on the encounter
        log.exception("encounter %s failed", encounter_id)
        message = str(exc) if isinstance(exc, clients.ServiceError) else "Processing failed"
        try:
            await clients.update_encounter(encounter_id, status="error", error=message)
        except Exception:  # noqa: BLE001
            log.exception("could not record the failure of %s", encounter_id)
