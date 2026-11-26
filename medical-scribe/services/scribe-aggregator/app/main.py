# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""scribe-aggregator: the Medical Scribe API. The UI and any other client (EHR integration, batch
jobs) use only this; the model services and the encounter store stay internal."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from . import clients, config, live, note, pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await clients.close()


app = FastAPI(
    title="Medical Scribe API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)


@app.exception_handler(LookupError)
async def not_found(_: Request, exc: LookupError) -> JSONResponse:
    return JSONResponse({"detail": "Not found"}, status_code=404)


@app.exception_handler(clients.ServiceError)
async def service_error(_: Request, exc: clients.ServiceError) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=502)


async def _read_upload(file: UploadFile) -> bytes:
    data = await file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(413, "The audio file is too large")
    if not data:
        raise HTTPException(400, "The audio file is empty")
    return data


# ------------------------------------------------------------------- status --
@app.get("/api/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/status")
async def status() -> dict[str, Any]:
    services = await clients.service_status()
    return {"ready": all(s["ready"] for s in services), "services": services}


@app.get("/api/config")
async def app_config() -> dict[str, Any]:
    return {
        "stt": {"model": config.STT_MODEL, "device": config.STT_DEVICE},
        "diarization": {"model": config.DIARIZATION_MODEL, "device": config.DIARIZATION_DEVICE},
        "text_generation": {"model": config.LLM_MODEL_NAME, "device": config.LLM_DEVICE},
    }


# ------------------------------------------------------------------ doctors --
class DoctorIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


def _public_doctor(doctor: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in doctor.items() if k != "embedding"}


@app.get("/api/doctors")
async def list_doctors() -> list[dict[str, Any]]:
    return [_public_doctor(d) for d in await clients.store("GET", "/v1/doctors")]


@app.post("/api/doctors", status_code=201)
async def create_doctor(body: DoctorIn) -> dict[str, Any]:
    return _public_doctor(await clients.store("POST", "/v1/doctors", json=body.model_dump()))


@app.delete("/api/doctors/{doctor_id}", status_code=204)
async def delete_doctor(doctor_id: str) -> None:
    await clients.store("DELETE", f"/v1/doctors/{doctor_id}")


@app.post("/api/doctors/{doctor_id}/voice")
async def enrol_voice(doctor_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    """A short voice sample (≥ 3 s) becomes the doctor's voice print, so diarization labels them."""
    await clients.store("GET", f"/v1/doctors/{doctor_id}")
    embedding = await clients.voice_embedding(await _read_upload(file), file.filename or "voice.webm")
    return _public_doctor(await clients.store("PATCH", f"/v1/doctors/{doctor_id}", json={"embedding": embedding}))


# --------------------------------------------------------------- encounters --
class EncounterIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    doctor_id: str | None = None
    language: str = Field(default="auto", max_length=16)


class EncounterPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    note: str | None = None
    reviewed: bool | None = None


@app.get("/api/encounters")
async def list_encounters() -> list[dict[str, Any]]:
    return await clients.store("GET", "/v1/encounters")


@app.post("/api/encounters", status_code=201)
async def create_encounter(body: EncounterIn) -> dict[str, Any]:
    return await clients.store("POST", "/v1/encounters", json=body.model_dump())


@app.get("/api/encounters/{encounter_id}")
async def get_encounter(encounter_id: str) -> dict[str, Any]:
    return await clients.store("GET", f"/v1/encounters/{encounter_id}")


@app.patch("/api/encounters/{encounter_id}")
async def update_encounter(encounter_id: str, body: EncounterPatch) -> dict[str, Any]:
    return await clients.update_encounter(encounter_id, **body.model_dump(exclude_unset=True))


@app.delete("/api/encounters/{encounter_id}", status_code=204)
async def delete_encounter(encounter_id: str) -> None:
    pipeline.cancel(encounter_id)
    await clients.store("DELETE", f"/v1/encounters/{encounter_id}")


@app.post("/api/encounters/{encounter_id}/audio", status_code=202)
async def upload_audio(encounter_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    """Starts the pipeline on an uploaded recording; poll the encounter for its status."""
    await clients.store("GET", f"/v1/encounters/{encounter_id}")
    if pipeline.is_running(encounter_id):
        raise HTTPException(409, "This encounter is already being processed")
    audio = await _read_upload(file)
    pipeline.start(encounter_id, audio, file.filename or "audio")
    return {"id": encounter_id, "status": "processing"}


@app.post("/api/encounters/{encounter_id}/note")
async def generate_note(encounter_id: str) -> StreamingResponse:
    """The SOAP note, streamed as server-sent events: `delta`, then `done` or `error`."""
    encounter = await clients.store("GET", f"/v1/encounters/{encounter_id}")
    if not encounter.get("transcript"):
        raise HTTPException(409, "The encounter has no transcript yet")
    return StreamingResponse(
        note.generate(encounter),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.websocket("/api/live/{encounter_id}")
async def live_ws(ws: WebSocket, encounter_id: str) -> None:
    await live.handle(ws, encounter_id)


# ------------------------------------------------------------------ metrics --
@app.get("/api/metrics")
async def metrics() -> dict[str, Any]:
    """Hardware metrics from the performance-tools metrics-collector, when it runs."""
    out: dict[str, Any] = {"available": False}
    try:
        for key, path in (("metrics", "/metrics"), ("platform", "/platform-info")):
            resp = await clients.http().get(f"{config.METRICS_URL}{path}", timeout=5)
            if resp.status_code == 200:
                out[key] = resp.json()
                out["available"] = True
    except httpx.HTTPError:
        pass
    return out
