# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Encounter store: the one owner of encounters (transcript, SOAP note, timings) and doctor profiles
(name, voice embedding). SQLite in DATA_DIR; JSON columns for the transcript, embedding and timings."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Iterator, Literal

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DB_PATH = DATA_DIR / "encounters.db"

Status = Literal["new", "recording", "processing", "transcribed", "error"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS doctors (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    embedding TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS encounters (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    doctor_id TEXT REFERENCES doctors(id) ON DELETE SET NULL,
    language TEXT NOT NULL DEFAULT 'auto',
    status TEXT NOT NULL DEFAULT 'new',
    error TEXT,
    transcript TEXT NOT NULL DEFAULT '[]',
    note TEXT,
    reviewed INTEGER NOT NULL DEFAULT 0,
    timings TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    transcribed_at TEXT,
    noted_at TEXT
);
"""

_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    with _lock:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript(SCHEMA)


class TranscriptEntry(BaseModel):
    speaker: str
    text: str
    start: float
    end: float


class DoctorIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class DoctorPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    embedding: list[float] | None = None


class EncounterIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    doctor_id: str | None = None
    language: str = Field(default="auto", max_length=16)


class EncounterPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    doctor_id: str | None = None
    language: str | None = Field(default=None, max_length=16)
    status: Status | None = None
    error: str | None = None
    transcript: list[TranscriptEntry] | None = None
    note: str | None = None
    reviewed: bool | None = None
    timings: dict[str, float | None] | None = None
    transcribed_at: str | None = None
    noted_at: str | None = None


def doctor_out(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "enrolled": row["embedding"] is not None,
        "embedding": json.loads(row["embedding"]) if row["embedding"] else None,
        "created_at": row["created_at"],
    }


def encounter_out(row: sqlite3.Row) -> dict[str, Any]:
    out = dict(row)
    out["transcript"] = json.loads(row["transcript"])
    out["timings"] = json.loads(row["timings"])
    out["reviewed"] = bool(row["reviewed"])
    return out


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Medical Scribe encounter store", version="1.0.0", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    with db() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


# ------------------------------------------------------------------ doctors --
@app.get("/v1/doctors")
def list_doctors() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM doctors ORDER BY name").fetchall()
    return [doctor_out(r) for r in rows]


@app.post("/v1/doctors", status_code=201)
def create_doctor(body: DoctorIn) -> dict[str, Any]:
    doctor_id = uuid.uuid4().hex
    with db() as conn:
        conn.execute(
            "INSERT INTO doctors (id, name, created_at) VALUES (?, ?, ?)",
            (doctor_id, body.name.strip(), now()),
        )
        row = conn.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,)).fetchone()
    return doctor_out(row)


@app.get("/v1/doctors/{doctor_id}")
def get_doctor(doctor_id: str) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Doctor not found")
    return doctor_out(row)


@app.patch("/v1/doctors/{doctor_id}")
def update_doctor(doctor_id: str, body: DoctorPatch) -> dict[str, Any]:
    fields = body.model_dump(exclude_unset=True)
    if "embedding" in fields and fields["embedding"] is not None:
        fields["embedding"] = json.dumps(fields["embedding"])
    with db() as conn:
        if fields:
            assignments = ", ".join(f"{k} = ?" for k in fields)
            conn.execute(
                f"UPDATE doctors SET {assignments} WHERE id = ?",
                (*fields.values(), doctor_id),
            )
        row = conn.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Doctor not found")
    return doctor_out(row)


@app.delete("/v1/doctors/{doctor_id}", status_code=204)
def delete_doctor(doctor_id: str) -> Response:
    with db() as conn:
        conn.execute("DELETE FROM doctors WHERE id = ?", (doctor_id,))
    return Response(status_code=204)


# --------------------------------------------------------------- encounters --
@app.get("/v1/encounters")
def list_encounters() -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            "SELECT e.*, d.name AS doctor_name FROM encounters e "
            "LEFT JOIN doctors d ON d.id = e.doctor_id ORDER BY e.created_at DESC"
        ).fetchall()
    return [encounter_out(r) for r in rows]


def _get_encounter(conn: sqlite3.Connection, encounter_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT e.*, d.name AS doctor_name FROM encounters e "
        "LEFT JOIN doctors d ON d.id = e.doctor_id WHERE e.id = ?",
        (encounter_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(404, "Encounter not found")
    return encounter_out(row)


@app.post("/v1/encounters", status_code=201)
def create_encounter(body: EncounterIn) -> dict[str, Any]:
    encounter_id = uuid.uuid4().hex
    stamp = now()
    with db() as conn:
        conn.execute(
            "INSERT INTO encounters (id, name, doctor_id, language, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (encounter_id, body.name.strip(), body.doctor_id, body.language, stamp, stamp),
        )
        return _get_encounter(conn, encounter_id)


@app.get("/v1/encounters/{encounter_id}")
def get_encounter(encounter_id: str) -> dict[str, Any]:
    with db() as conn:
        return _get_encounter(conn, encounter_id)


@app.patch("/v1/encounters/{encounter_id}")
def update_encounter(encounter_id: str, body: EncounterPatch) -> dict[str, Any]:
    fields = body.model_dump(exclude_unset=True)
    with db() as conn:
        current = _get_encounter(conn, encounter_id)
        if "transcript" in fields:
            fields["transcript"] = json.dumps(fields["transcript"])
        if "timings" in fields:
            # Timings accumulate: transcription and note generation each add theirs; null removes one.
            merged = {**current["timings"], **(fields["timings"] or {})}
            fields["timings"] = json.dumps({k: v for k, v in merged.items() if v is not None})
        if "reviewed" in fields:
            fields["reviewed"] = int(bool(fields["reviewed"]))
        fields["updated_at"] = now()
        assignments = ", ".join(f"{k} = ?" for k in fields)
        conn.execute(
            f"UPDATE encounters SET {assignments} WHERE id = ?",
            (*fields.values(), encounter_id),
        )
        return _get_encounter(conn, encounter_id)


@app.delete("/v1/encounters/{encounter_id}", status_code=204)
def delete_encounter(encounter_id: str) -> Response:
    with db() as conn:
        conn.execute("DELETE FROM encounters WHERE id = ?", (encounter_id,))
    return Response(status_code=204)
