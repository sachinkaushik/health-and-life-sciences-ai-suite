# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Runs one SDC provider per simulated bed (patient monitor or multimodal device)."""

from __future__ import annotations

import itertools
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field

from sdc11073.location import SdcLocation
from sdc11073.provider import SdcProvider
from sdc11073.wsdiscovery import WSDiscovery
from sdc11073.xml_types.dpws_types import ThisDeviceType, ThisModelType

from . import mdib_model as m
from .simulator import DeviceSimulator
from .writer import MdibWriter

log = logging.getLogger(__name__)

_MODEL_NAMES = {m.MONITOR: "MMPM Patient Monitor", m.MULTIMODAL: "MMPM Multimodal Monitor"}


class UnknownDevice(KeyError):
    pass


class DeviceConflict(Exception):
    pass


@dataclass
class Bed:
    id: str
    kind: str
    ai: bool
    primary: bool
    epr: str
    serial: str
    video_url: str | None
    provider: SdcProvider
    writer: MdibWriter
    sim: DeviceSimulator | None
    created: float = field(default_factory=time.time)

    def info(self) -> dict:
        return {"bed_id": self.id, "type": self.kind, "ai": self.ai, "primary": self.primary,
                "epr": self.epr, "serial": self.serial, "video_url": self.video_url,
                "created": self.created}


@dataclass
class DeviceConfig:
    facility: str = "MMPM"
    point_of_care: str = "ICU"
    sim_enabled: bool = True
    wave_chunk_s: float = 0.2
    video_urls: tuple[str, ...] = ()
    max_devices: int = 16


class DeviceManager:
    def __init__(self, wsd: WSDiscovery, ssl_ctx, cfg: DeviceConfig):
        self._wsd = wsd
        self._ssl_ctx = ssl_ctx
        self._cfg = cfg
        self._beds: dict[str, Bed] = {}
        self._lock = threading.Lock()
        self._video_rr = itertools.cycle(cfg.video_urls) if cfg.video_urls else None

    def _next_bed_id(self) -> str:
        n = 1
        while f"bed-{n:02d}" in self._beds:
            n += 1
        return f"bed-{n:02d}"

    def _stable_epr(self, bed_id: str) -> str:
        # Stable across restarts so consumers can recognise a bed they have seen before.
        return f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, f'mmpm-sdc/{self._cfg.facility}/{bed_id}')}"

    def add(self, kind: str, ai: bool = False, primary: bool = False, epr: str | None = None) -> Bed:
        if kind not in m.DEVICE_KINDS:
            raise ValueError(f"unknown device type {kind!r}")
        with self._lock:
            if len(self._beds) >= self._cfg.max_devices:
                raise DeviceConflict(f"device limit reached ({self._cfg.max_devices})")
            bed_id = self._next_bed_id()
            number = int(bed_id.split("-")[1])
            epr = epr or self._stable_epr(bed_id)
            serial = f"MMPM-{number:04d}"
            video_url = next(self._video_rr) if (kind == m.MULTIMODAL and self._video_rr) else None

            mdib = m.build_mdib(m.vmds_for(kind, ai))
            writer = MdibWriter(mdib)
            provider = SdcProvider(
                ws_discovery=self._wsd,
                this_model=ThisModelType(manufacturer="Intel", model_name=_MODEL_NAMES[kind],
                                         model_number="1.0", model_url="https://www.intel.com"),
                this_device=ThisDeviceType(friendly_name=f"{_MODEL_NAMES[kind]} {bed_id}",
                                           firmware_version="1.0", serial_number=serial),
                device_mdib_container=mdib,
                epr=epr,
                ssl_context_container=self._ssl_ctx,
            )
            provider.start_all(start_rtsample_loop=False)
            try:
                if video_url:
                    writer.set_metrics({m.H_VIDEO_URL: video_url})
                provider.set_location(SdcLocation(fac=self._cfg.facility, poc=self._cfg.point_of_care,
                                                  bed=bed_id))
                sim = DeviceSimulator(writer, wave_chunk_s=self._cfg.wave_chunk_s) if self._cfg.sim_enabled else None
                if sim:
                    sim.start()
            except Exception:
                provider.stop_all()
                raise
            bed = Bed(bed_id, kind, ai, primary, epr, serial, video_url, provider, writer, sim)
            self._beds[bed_id] = bed
        log.info("added %s %s (%s, ai=%s, video=%s)", kind, bed_id, epr, ai, video_url or "-")
        return bed

    def remove(self, bed_id: str) -> None:
        with self._lock:
            bed = self._beds.get(bed_id)
            if bed is None:
                raise UnknownDevice(bed_id)
            if bed.primary:
                raise DeviceConflict(f"{bed_id} is the primary bed and cannot be removed")
            del self._beds[bed_id]
        self._stop_bed(bed)
        log.info("removed %s (%s)", bed_id, bed.epr)

    def get(self, bed_id: str) -> Bed:
        with self._lock:
            bed = self._beds.get(bed_id)
        if bed is None:
            raise UnknownDevice(bed_id)
        return bed

    def list(self) -> list[dict]:
        with self._lock:
            return [b.info() for b in sorted(self._beds.values(), key=lambda b: b.id)]

    def stop_all(self) -> None:
        with self._lock:
            beds, self._beds = list(self._beds.values()), {}
        for bed in beds:
            self._stop_bed(bed)

    @staticmethod
    def _stop_bed(bed: Bed) -> None:
        if bed.sim:
            bed.sim.stop()
        # Sends WS-Discovery Bye and ends subscriptions, so consumers drop the bed.
        bed.provider.stop_all()
