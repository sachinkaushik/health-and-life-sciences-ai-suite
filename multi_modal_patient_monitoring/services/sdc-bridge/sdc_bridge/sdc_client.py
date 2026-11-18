# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Discovers every SDC provider (bed) in the facility, subscribes to each one and drops the ones that go away."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field

from sdc11073 import observableproperties
from sdc11073.consumer import SdcConsumer
from sdc11073.definitions_sdc import SdcV1Definitions
from sdc11073.location import SdcLocation
from sdc11073.mdib.consumermdib import ConsumerMdib
from sdc11073.wsdiscovery import WSDiscovery

from .forwarder import AggregatorStream
from .translator import Translator

log = logging.getLogger(__name__)

# A provider missing from this many discovery rounds in a row is treated as gone.
_MISSED_SCANS_LIMIT = 3


@dataclass
class _Session:
    epr: str
    bed_id: str
    location: str
    client: SdcConsumer
    mdib: ConsumerMdib
    translator: Translator
    missed_scans: int = field(default=0)

    @property
    def connected(self) -> bool:
        return bool(self.client.is_connected)

    def info(self) -> dict:
        t = self.translator
        return {"bed_id": self.bed_id, "epr": self.epr, "location": self.location, "primary": t.primary,
                "type": "multimodal" if t.has_video else "monitor", "ai": t.has_ai,
                "video_url": t.video_url, "connected": self.connected}


def _location(service) -> SdcLocation | None:
    for scope in getattr(service.scopes, "text", None) or []:
        try:
            return SdcLocation.from_scope_string(scope)
        except Exception:
            continue
    return None


class SdcFleet:
    def __init__(self, stream: AggregatorStream, bind_ip: str, facility: str | None, primary_epr: str | None,
                 rppg_device_id: str, wave_window_s: float = 1.0, provider_xaddr: str | None = None,
                 ssl_context=None, scan_s: float = 5.0):
        self._stream = stream
        self._bind_ip = bind_ip
        self._facility = facility
        self._primary_epr = primary_epr
        self._rppg_id = rppg_device_id
        self._window_s = wave_window_s
        self._xaddr = provider_xaddr
        self._ssl = ssl_context
        self._scan_s = scan_s
        self.enabled = threading.Event()
        self._sessions: dict[str, _Session] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="sdc-fleet")
        self._wsd: WSDiscovery | None = None

    # ---- public ----
    @property
    def connected(self) -> bool:
        with self._lock:
            return any(s.connected for s in self._sessions.values())

    @property
    def provider(self) -> str | None:
        primary = self._primary()
        return primary.epr if primary else None

    def beds(self) -> list[dict]:
        with self._lock:
            sessions = sorted(self._sessions.values(), key=lambda s: s.bed_id)
        return [s.info() for s in sessions]

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self.enabled.set()
        else:
            self.enabled.clear()
        with self._lock:
            sessions = list(self._sessions.values())
        for s in sessions:
            s.translator.clear_buffers()
        log.info("device streaming %s", "ENABLED" if enabled else "DISABLED")

    def ai_ecg_snapshot(self) -> dict | None:
        primary = self._primary()
        return primary.translator.ai_ecg_snapshot() if primary else None

    def start(self) -> None:
        if not self._xaddr:
            self._wsd = WSDiscovery(self._bind_ip)
            self._wsd.start()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=15)
        with self._lock:
            sessions, self._sessions = list(self._sessions.values()), {}
        for s in sessions:
            self._close(s)
        if self._wsd:
            self._wsd.stop()

    # ---- internals ----
    def _primary(self) -> _Session | None:
        with self._lock:
            return next((s for s in self._sessions.values() if s.translator.primary), None)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._prune_disconnected()
                if self._xaddr:
                    if not self._sessions:
                        self._open(self._xaddr, "bed-01", "", lambda: SdcConsumer(
                            self._xaddr, SdcV1Definitions, self._ssl))
                else:
                    self._scan()
            except Exception as exc:
                log.warning("SDC discovery round failed: %s", exc)
                log.debug("discovery failure detail", exc_info=True)
            self._stop.wait(self._scan_s)

    def _prune_disconnected(self) -> None:
        with self._lock:
            gone = [s for s in self._sessions.values() if not s.connected]
            for s in gone:
                del self._sessions[s.epr]
        for s in gone:
            log.warning("lost SDC provider %s (%s)", s.bed_id, s.epr)
            self._close(s)

    def _scan(self) -> None:
        # Drop cached entries so restarted providers' new addresses are picked up.
        self._wsd.clear_remote_services()
        services = self._wsd.search_services(types=SdcV1Definitions.MedicalDeviceTypesFilter, timeout=3)
        seen = set()
        for service in services:
            loc = _location(service)
            if self._facility and (loc is None or loc.fac != self._facility):
                continue
            seen.add(service.epr)
            if service.epr in self._sessions:
                continue
            bed_id = self._unique_bed_id((loc.bed if loc else None) or service.epr.rsplit(":", 1)[-1][:8])
            try:
                self._open(service.epr, bed_id, f"{loc.fac}/{loc.poc}/{loc.bed}" if loc else "",
                           lambda s=service: SdcConsumer.from_wsd_service(s, ssl_context_container=self._ssl))
            except Exception as exc:
                log.warning("cannot connect to SDC provider %s (%s): %s", bed_id, service.epr, exc)
        self._prune_missing(seen)

    def _prune_missing(self, seen: set[str]) -> None:
        with self._lock:
            gone = []
            for s in self._sessions.values():
                s.missed_scans = 0 if s.epr in seen else s.missed_scans + 1
                if s.missed_scans >= _MISSED_SCANS_LIMIT:
                    gone.append(s)
            for s in gone:
                del self._sessions[s.epr]
        for s in gone:
            log.warning("SDC provider %s (%s) no longer discoverable", s.bed_id, s.epr)
            self._close(s)

    def _unique_bed_id(self, bed_id: str) -> str:
        with self._lock:
            used = {s.bed_id for s in self._sessions.values()}
        candidate, n = bed_id, 2
        while candidate in used:
            candidate, n = f"{bed_id}-{n}", n + 1
        return candidate

    def _open(self, epr: str, bed_id: str, location: str, make_client) -> None:
        primary = bool(self._primary_epr) and epr == self._primary_epr
        if self._xaddr:
            primary = True
        translator = Translator(self._stream, bed_id, primary, self._rppg_id, self.enabled, self._window_s)
        client = make_client()
        client.start_all(not_subscribed_actions=None)
        try:
            mdib = ConsumerMdib(client)
            mdib.init_mdib()
            translator.bind(mdib)
            observableproperties.bind(mdib, metrics_by_handle=translator.on_metrics,
                                      waveform_by_handle=translator.on_waves)
        except Exception:
            client.stop_all(unsubscribe=True)
            raise
        with self._lock:
            self._sessions[epr] = _Session(epr, bed_id, location, client, mdib, translator)
        log.info("subscribed to SDC provider %s (%s%s)", bed_id, epr, ", primary" if primary else "")

    @staticmethod
    def _close(session: _Session) -> None:
        try:
            observableproperties.unbind(session.mdib, metrics_by_handle=session.translator.on_metrics,
                                        waveform_by_handle=session.translator.on_waves)
        except Exception:
            log.debug("unbind failed", exc_info=True)
        try:
            session.client.stop_all(unsubscribe=True)
        except Exception:
            log.debug("stop_all failed", exc_info=True)
