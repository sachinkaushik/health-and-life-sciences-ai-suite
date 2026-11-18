# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Turns SDC metric/waveform reports into MMPM Vital messages and AI-ECG snapshots."""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

from proto import vital_pb2

from .forwarder import AggregatorStream
from .mapping import AI_ECG, DEVICE, RPPG, VIDEO, Target, lookup

log = logging.getLogger(__name__)

# rPPG sends these as the scalar companion of its waveform, not as standalone numerics.
_RPPG_WAVE_VALUES = {"HEART_RATE", "RESP_RATE"}


@dataclass
class _Bound:
    target: Target
    unit: str
    sample_rate_hz: float


def _unit_name(descr) -> str:
    unit = getattr(descr, "Unit", None)
    if unit is None:
        return ""
    return unit.SymbolicCodeName or unit.Code or ""


def _ts_ms(metric_value) -> int:
    t = getattr(metric_value, "DeterminationTime", None)
    return round(t * 1000) if t else int(time.time() * 1000)


class Translator:
    """Translates one SDC provider (bed). Only the primary bed forwards rPPG and AI-ECG data."""

    def __init__(self, stream: AggregatorStream, bed_id: str, primary: bool, rppg_device_id: str,
                 enabled: threading.Event, wave_window_s: float = 1.0):
        self._stream = stream
        self.bed_id = bed_id
        self.primary = primary
        self._rppg_id = rppg_device_id
        self._enabled = enabled
        self._window_s = wave_window_s
        self._lock = threading.Lock()
        self._handles: dict[str, _Bound] = {}
        self._wave_buf: dict[str, list[float]] = {}
        self._rppg_values: dict[str, float] = {}
        self._ai_wave: tuple[int, list[float]] | None = None
        self._ai_meta: OrderedDict[int, dict] = OrderedDict()
        self._ai_snapshot: dict | None = None
        self.video_url: str | None = None
        self.has_video = False
        self.has_ai = False

    # ---- control ----
    def clear_buffers(self) -> None:
        with self._lock:
            self._wave_buf.clear()

    def ai_ecg_snapshot(self) -> dict | None:
        with self._lock:
            return self._ai_snapshot

    # ---- binding ----
    def bind(self, mdib) -> int:
        handles: dict[str, _Bound] = {}
        for descr in mdib.descriptions.objects:
            if not getattr(descr, "is_metric_descriptor", False):
                continue
            target = lookup(descr.Type)
            if target is None:
                continue
            if not self.primary and target.group in (RPPG, AI_ECG):
                continue
            period = getattr(descr, "SamplePeriod", None)
            # xsd:duration carries ~µs precision, so 1/120 s comes back as 120.0048 Hz.
            fs = round(1.0 / float(period), 1) if period else 0.0
            handles[descr.Handle] = _Bound(target, target.unit or _unit_name(descr), fs)
        groups = {b.target.group for b in handles.values()}
        with self._lock:
            self._handles = handles
            self._wave_buf.clear()
            self.has_video = VIDEO in groups
            self.has_ai = RPPG in groups or AI_ECG in groups
        for handle, bound in handles.items():
            if bound.target.group == VIDEO:
                state = mdib.states.descriptor_handle.get_one(handle, allow_none=True)
                mv = getattr(state, "MetricValue", None)
                if mv is not None and mv.Value:
                    self.video_url = str(mv.Value)
        log.info("%s: mapped %d SDC metrics to MMPM metrics", self.bed_id, len(handles))
        return len(handles)

    # ---- SDC callbacks ----
    def on_metrics(self, states: dict) -> None:
        for handle, state in states.items():
            bound = self._handles.get(handle)
            mv = getattr(state, "MetricValue", None)
            if bound is None or mv is None or mv.Value is None:
                continue
            t = bound.target
            if t.group == DEVICE:
                if self._enabled.is_set():
                    self._send(t, bound.unit, float(mv.Value))
            elif t.group == RPPG:
                if t.metric in _RPPG_WAVE_VALUES:
                    self._rppg_values[t.metric] = float(mv.Value)
                else:
                    self._send(t, bound.unit, float(mv.Value))
            elif t.group == AI_ECG:
                self._on_ai_ecg_meta(_ts_ms(mv), t.metric, mv.Value)
            elif t.group == VIDEO:
                self.video_url = str(mv.Value) or None

    def on_waves(self, states: dict) -> None:
        for handle, state in states.items():
            bound = self._handles.get(handle)
            mv = getattr(state, "MetricValue", None)
            if bound is None or mv is None or not mv.Samples:
                continue
            samples = [float(s) for s in mv.Samples]
            t = bound.target
            if t.group == DEVICE:
                self._buffer_device_wave(handle, bound, samples)
            elif t.group == RPPG:
                self._send(t, bound.unit, self._rppg_values.get(t.metric, 0.0), samples, bound.sample_rate_hz)
            elif t.group == AI_ECG:
                self._on_ai_ecg_wave(_ts_ms(mv), samples)

    # ---- helpers ----
    def _device_id(self, t: Target) -> str:
        return self._rppg_id if t.group == RPPG else f"{self.bed_id}-{t.device_suffix}"

    def _send(self, t: Target, unit: str, value: float, waveform: list[float] | None = None,
              fs: float = 0.0) -> None:
        vital = vital_pb2.Vital(device_id=self._device_id(t), metric=t.metric, value=value, unit=unit,
                                timestamp=int(time.time() * 1000))
        if waveform:
            vital.waveform.extend(waveform)
            vital.waveform_frequency_hz = int(round(fs))
        if t.device_type:
            vital.metadata["device_type"] = t.device_type
        vital.metadata["bed_id"] = self.bed_id
        vital.metadata["primary"] = "true" if self.primary else "false"
        self._stream.send(vital)

    def _buffer_device_wave(self, handle: str, bound: _Bound, samples: list[float]) -> None:
        # Re-chunk to ~1 s windows: the MMPM UI redraws each waveform message as a full strip.
        with self._lock:
            if not self._enabled.is_set():
                return
            buf = self._wave_buf.setdefault(handle, [])
            buf.extend(samples)
            if len(buf) < bound.sample_rate_hz * self._window_s:
                return
            self._wave_buf[handle] = []
        self._send(bound.target, bound.unit, 0.0, buf, bound.sample_rate_hz)

    def _on_ai_ecg_wave(self, ts: int, samples: list[float]) -> None:
        with self._lock:
            self._ai_wave = (ts, samples)
            self._pair_ai_ecg(ts)

    def _on_ai_ecg_meta(self, ts: int, field: str, value) -> None:
        with self._lock:
            entry = self._ai_meta.setdefault(ts, {})
            entry[field] = float(value) if field == "inference_ms" else str(value)
            while len(self._ai_meta) > 8:
                self._ai_meta.popitem(last=False)
            self._pair_ai_ecg(ts)

    def _pair_ai_ecg(self, ts: int) -> None:
        # Wave and label arrive in separate SDC reports; publish only when both carry the same timestamp.
        meta = self._ai_meta.get(ts)
        if self._ai_wave is None or self._ai_wave[0] != ts or not meta or "result" not in meta:
            return
        signal = self._ai_wave[1]
        self._ai_snapshot = {
            "file": meta.get("file", ""),
            "signal": signal,
            "result": meta["result"],
            "inference_ms": meta.get("inference_ms", 0.0),
            "length": len(signal),
            "timestamp": ts,
        }
