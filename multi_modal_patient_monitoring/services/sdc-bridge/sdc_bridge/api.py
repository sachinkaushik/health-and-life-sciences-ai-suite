# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""HTTP API: dds-bridge compatible /start /stop /status and AI-ECG compatible /predict_stream_next."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .sdc_client import SdcFleet


def create_app(fleet: SdcFleet) -> FastAPI:
    app = FastAPI(title="MMPM SDC Bridge")

    @app.post("/start")
    def start():
        fleet.set_enabled(True)
        return {"status": "started"}

    @app.post("/stop")
    def stop():
        fleet.set_enabled(False)
        return {"status": "stopped"}

    @app.get("/status")
    def status():
        return {
            "enabled": fleet.enabled.is_set(),
            "connected": fleet.connected,
            "provider": fleet.provider,
            "beds": fleet.beds(),
        }

    @app.get("/beds")
    def beds():
        return {"enabled": fleet.enabled.is_set(), "beds": fleet.beds()}

    @app.get("/health")
    def health():
        return {"status": "ok", "sdc_connected": fleet.connected}

    @app.get("/predict_stream_next")
    def predict_stream_next():
        snapshot = fleet.ai_ecg_snapshot()
        if snapshot is None:
            raise HTTPException(status_code=503, detail="no AI-ECG result received over SDC yet")
        return snapshot

    return app
