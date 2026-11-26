# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Live consultation over one WebSocket (`/api/live/{encounter_id}`).

Browser → aggregator: binary frames of 16 kHz mono 16-bit PCM, then `{"type": "stop"}`.
Aggregator → browser: `{"type": "utterance", "text"}` as speech-to-text finishes each utterance,
`{"type": "processing"}` once the recording is handed to the pipeline, `{"type": "error", "message"}`.

The audio is relayed to audio-analyzer's OpenAI Realtime-style `/v1/realtime` for the live text and
kept; on stop (or a dropped connection) the whole recording goes through the same pipeline as an
upload, which adds word timings and the Doctor / Patient labels."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import io
import json
import logging
import wave
from urllib.parse import urlencode

from fastapi import WebSocket, WebSocketDisconnect
from websockets.asyncio.client import connect

from . import clients, config, pipeline

log = logging.getLogger("scribe.live")

SAMPLE_RATE = 16000
MAX_SECONDS = 2 * 60 * 60
MIN_SECONDS = 1.0
CLOSE_TIMEOUT_SECONDS = 60


def to_wav(pcm: bytes) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm)
    return out.getvalue()


def _stt_ws_url(language: str) -> str:
    params = {"intent": "transcription"}
    if language and language != "auto":
        params["language"] = language
    base = config.STT_URL.replace("http://", "ws://", 1).replace("https://", "wss://", 1)
    return f"{base}/v1/realtime?{urlencode(params)}"


async def handle(ws: WebSocket, encounter_id: str) -> None:
    await ws.accept()
    try:
        encounter = await clients.store("GET", f"/v1/encounters/{encounter_id}")
    except LookupError:
        await ws.send_json({"type": "error", "message": "Encounter not found"})
        await ws.close()
        return
    if pipeline.is_running(encounter_id):
        await ws.send_json({"type": "error", "message": "This encounter is still being processed"})
        await ws.close()
        return

    pcm = bytearray()
    max_bytes = MAX_SECONDS * SAMPLE_RATE * 2
    try:
        upstream = await connect(_stt_ws_url(encounter.get("language") or "auto"), max_size=None, proxy=None)
    except Exception:  # noqa: BLE001
        log.exception("live speech-to-text unavailable")
        await ws.send_json({"type": "error", "message": "Live speech to text is not available"})
        await ws.close()
        return

    await clients.update_encounter(encounter_id, status="recording", error=None)

    async def relay_transcripts() -> None:
        seen = ""
        async for raw in upstream:
            event = json.loads(raw)
            kind = event.get("type")
            if kind == "conversation.item.input_audio_transcription.completed":
                # `transcript` is cumulative for the session: send the new suffix.
                full = str(event.get("transcript") or "").strip()
                text = full[len(seen) :] if full.startswith(seen) else full
                seen = full
                if text.strip():
                    await ws.send_json({"type": "utterance", "text": text.strip()})
            elif kind == "error":
                message = (event.get("error") or {}).get("message") or "Live transcription error"
                await ws.send_json({"type": "error", "message": message})

    relay = asyncio.create_task(relay_transcripts())
    try:
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                break
            if message.get("bytes"):
                chunk = message["bytes"]
                if len(pcm) + len(chunk) > max_bytes:
                    await ws.send_json({"type": "error", "message": "Recording limit reached"})
                    break
                pcm.extend(chunk)
                await upstream.send(
                    json.dumps({"type": "input_audio_buffer.append", "audio": base64.b64encode(chunk).decode()})
                )
            elif message.get("text"):
                if json.loads(message["text"]).get("type") == "stop":
                    break
    except WebSocketDisconnect:
        pass
    finally:
        with contextlib.suppress(Exception):
            await upstream.send(json.dumps({"type": "session.close"}))
        with contextlib.suppress(Exception):
            await asyncio.wait_for(relay, CLOSE_TIMEOUT_SECONDS)
        relay.cancel()
        with contextlib.suppress(Exception):
            await upstream.close()

    seconds = len(pcm) / (SAMPLE_RATE * 2)
    if seconds < MIN_SECONDS:
        await clients.update_encounter(encounter_id, status="new")
        with contextlib.suppress(Exception):
            await ws.send_json({"type": "error", "message": "The recording was too short"})
            await ws.close()
        return
    pipeline.start(encounter_id, to_wav(bytes(pcm)), "recording.wav")
    with contextlib.suppress(Exception):
        await ws.send_json({"type": "processing", "seconds": round(seconds, 1)})
        await ws.close()
