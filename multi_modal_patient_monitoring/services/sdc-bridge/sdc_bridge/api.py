# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""HTTP API: dds-bridge compatible /start /stop /status and AI-ECG compatible /predict_stream_next."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .sdc_client import SdcConnector
from .translator import Translator


def create_app(translator: Translator, connector: SdcConnector) -> FastAPI:
    app = FastAPI(title="MMPM SDC Bridge")

    @app.post("/start")
    def start():
        translator.set_device_enabled(True)
        return {"status": "started"}

    @app.post("/stop")
    def stop():
        translator.set_device_enabled(False)
        return {"status": "stopped"}

    @app.get("/status")
    def status():
        return {
            "enabled": translator.device_enabled,
            "connected": connector.connected,
            "provider": connector.provider,
        }

    @app.get("/health")
    def health():
        return {"status": "ok", "sdc_connected": connector.connected}

    @app.get("/predict_stream_next")
    def predict_stream_next():
        snapshot = translator.ai_ecg_snapshot()
        if snapshot is None:
            raise HTTPException(status_code=503, detail="no AI-ECG result received over SDC yet")
        return snapshot

    return app
