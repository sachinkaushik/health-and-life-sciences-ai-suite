# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Management REST API: list, add and remove simulated SDC beds."""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

from .devices import DeviceConflict, DeviceManager, UnknownDevice


class NewDevice(BaseModel):
    type: Literal["monitor", "multimodal"]


def create_app(manager: DeviceManager) -> FastAPI:
    app = FastAPI(title="MMPM SDC gateway", version="1.0")

    @app.get("/health")
    def health():
        return {"status": "ok", "devices": len(manager.list())}

    @app.get("/devices")
    def list_devices():
        return {"devices": manager.list()}

    @app.post("/devices", status_code=201)
    def add_device(req: NewDevice):
        try:
            return manager.add(req.type).info()
        except DeviceConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None

    @app.delete("/devices/{bed_id}", status_code=204)
    def remove_device(bed_id: str):
        try:
            manager.remove(bed_id)
        except UnknownDevice:
            raise HTTPException(status_code=404, detail="unknown device") from None
        except DeviceConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None
        return Response(status_code=204)

    return app
