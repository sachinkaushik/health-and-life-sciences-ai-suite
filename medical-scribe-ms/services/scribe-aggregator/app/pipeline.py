# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""The encounter pipeline: transcription and diarization in parallel, speaker alignment, then the
labelled transcript and per-stage timings saved to the encounter store. Runs as a server-side task,
so it finishes even when the browser that started it is closed."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

from . import clients
from .align import align_transcript

log = logging.getLogger("scribe.pipeline")

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


async def _both(first: Any, second: Any) -> tuple[Any, Any]:
    """Runs both; when one fails the other is cancelled (an orphaned diarization job would run on)."""
    tasks = [asyncio.ensure_future(first), asyncio.ensure_future(second)]
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        for task in done:
            if task.exception() is not None:
                raise task.exception()  # type: ignore[misc]
        return tasks[0].result(), tasks[1].result()
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


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

        (stt, stt_s), (segments, diar_s) = await _both(
            _timed(clients.transcribe(audio, filename, encounter.get("language") or "auto")),
            _timed(clients.diarize(audio, filename, embedding)),
        )
        started = time.perf_counter()
        words = [
            {"text": str(w.get("word", "")).strip(), "start": float(w.get("start", 0)), "end": float(w.get("end", 0))}
            for w in stt.get("words") or []
        ]
        stt_segments = [
            {"text": str(s.get("text", "")).strip(), "start": float(s.get("start", 0)), "end": float(s.get("end", 0))}
            for s in stt.get("segments") or []
        ]
        text = str(stt.get("text") or "").strip()
        # Without an enrolled doctor pyannote names speakers SPEAKER_00, SPEAKER_01, …
        segments = [
            {**s, "speaker": re.sub(r"^SPEAKER_(\d+)$", lambda m: f"Speaker {int(m.group(1)) + 1}", str(s.get("speaker", "")))}
            for s in segments
        ]
        transcript = align_transcript(text, segments, words, stt_segments)
        if not transcript and text:
            end = stt_segments[-1]["end"] if stt_segments else 0.0
            transcript = [{"speaker": "Speaker", "text": text, "start": 0.0, "end": end}]
        align_s = time.perf_counter() - started

        audio_s = float(stt.get("duration") or (stt_segments[-1]["end"] if stt_segments else 0.0))
        timings = {
            "audio_seconds": round(audio_s, 2),
            "stt_seconds": round(stt_s, 2),
            "diarization_seconds": round(diar_s, 2),
            "align_seconds": round(align_s, 3),
        }
        if audio_s > 0:
            timings["stt_rtf"] = round(stt_s / audio_s, 3)
            timings["diarization_rtf"] = round(diar_s / audio_s, 3)
        await clients.update_encounter(
            encounter_id,
            status="transcribed",
            transcript=transcript,
            timings=timings,
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
