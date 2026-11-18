# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Built-in SDC patient-monitor simulator (ECG, capnography, invasive BP)."""

from __future__ import annotations

import logging
import math
import random
import threading
import time

from .mdib_model import CO2_FS, ECG_FS, IBP_FS
from .writer import MdibWriter

log = logging.getLogger(__name__)

# (center as fraction of the beat, amplitude mV, width) for P, Q, R, S, T in lead II.
_ECG_WAVES_II = ((0.18, 0.15, 0.025), (0.355, -0.10, 0.010), (0.39, 1.30, 0.011),
                 (0.425, -0.30, 0.012), (0.66, 0.35, 0.045))
_ECG_WAVES_I = ((0.18, 0.08, 0.025), (0.355, -0.05, 0.010), (0.39, 0.75, 0.011),
                (0.425, -0.12, 0.012), (0.66, 0.20, 0.045))


def _ecg(phase: float, waves) -> float:
    return sum(a * math.exp(-((phase - c) ** 2) / (2 * w * w)) for c, a, w in waves)


def _arterial(phase: float) -> float:
    """Normalised (0..1) arterial pulse with upstroke and dicrotic notch."""
    if phase < 0.12:
        return math.sin(phase / 0.12 * math.pi / 2) ** 2
    decay = math.exp(-(phase - 0.12) / 0.32)
    notch = 0.10 * math.exp(-((phase - 0.40) ** 2) / (2 * 0.02 ** 2))
    tail = (phase - 0.12) / 0.88
    return max(0.0, decay * (1 - tail) + notch)


def _capnogram(phase: float) -> float:
    """Normalised (0..1) CO2 curve: inspiration baseline, expiratory upstroke, plateau, drop."""
    if phase < 0.40:
        return 0.0
    if phase < 0.50:
        x = (phase - 0.40) / 0.10
        return 0.92 * (1 - math.cos(x * math.pi)) / 2
    if phase < 0.93:
        return 0.92 + 0.08 * (phase - 0.50) / 0.43
    x = (phase - 0.93) / 0.07
    return (1 + math.cos(x * math.pi)) / 2


class _Vital:
    """Baseline with slow drift and jitter, clamped to a range."""

    def __init__(self, baseline: float, drift: float, period_s: float, jitter: float, lo: float, hi: float):
        self.baseline, self.drift, self.period, self.jitter = baseline, drift, period_s, jitter
        self.lo, self.hi = lo, hi
        self.offset = random.uniform(0, period_s)

    def value(self, t: float) -> float:
        v = self.baseline + self.drift * math.sin(2 * math.pi * (t + self.offset) / self.period)
        v += random.gauss(0, self.jitter)
        return round(min(self.hi, max(self.lo, v)))


class DeviceSimulator:
    def __init__(self, writer: MdibWriter, wave_chunk_s: float = 0.2, numeric_period_s: float = 1.0):
        self._writer = writer
        self._chunk_s = wave_chunk_s
        self._numeric_period = numeric_period_s
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._hr = _Vital(72, 6, 90, 1.0, 40, 180)
        self._rr = _Vital(14, 2, 120, 0.5, 6, 40)
        self._etco2 = _Vital(36, 3, 150, 0.7, 20, 60)
        self._sys = _Vital(120, 8, 110, 1.5, 70, 200)
        self._dia = _Vital(78, 5, 110, 1.0, 40, 120)
        self.current = {"hr": 72.0, "rr": 14.0, "etco2": 36.0, "sys": 120.0, "dia": 78.0}
        self._beat_phase = 0.0
        self._breath_phase = 0.0

    def start(self) -> None:
        for target in (self._numeric_loop, self._wave_loop):
            th = threading.Thread(target=target, daemon=True, name=target.__name__)
            th.start()
            self._threads.append(th)
        log.info("device simulator started (wave chunk %.0f ms)", self._chunk_s * 1000)

    def stop(self) -> None:
        self._stop.set()
        for th in self._threads:
            th.join(timeout=2)

    def _numeric_loop(self) -> None:
        while not self._stop.is_set():
            t = time.time()
            c = self.current
            c["hr"], c["rr"], c["etco2"] = self._hr.value(t), self._rr.value(t), self._etco2.value(t)
            c["sys"] = self._sys.value(t)
            c["dia"] = min(self._dia.value(t), c["sys"] - 20)
            mean = c["dia"] + (c["sys"] - c["dia"]) / 3
            try:
                self._writer.set_metrics({
                    "ecg.hr": c["hr"], "ecg.rr": c["rr"],
                    "co2.et": c["etco2"], "co2.rr": c["rr"],
                    "ibp.sys": c["sys"], "ibp.dia": c["dia"], "ibp.mean": round(mean),
                }, determination_time=t, places=0)
            except Exception:
                log.exception("numeric update failed")
            self._stop.wait(self._numeric_period)

    def _wave_loop(self) -> None:
        next_tick = time.monotonic()
        while not self._stop.is_set():
            try:
                self._writer.push_samples(self._next_chunk())
            except Exception:
                log.exception("waveform update failed")
            next_tick += self._chunk_s
            delay = next_tick - time.monotonic()
            if delay < -self._chunk_s:
                next_tick = time.monotonic()
            self._stop.wait(max(0.0, delay))

    def _next_chunk(self) -> dict[str, list[float]]:
        c = self.current
        beat_hz = c["hr"] / 60.0
        breath_hz = c["rr"] / 60.0
        start_beat, start_breath = self._beat_phase, self._breath_phase

        def beat_phases(fs: float) -> list[float]:
            n = round(fs * self._chunk_s)
            return [(start_beat + i * beat_hz / fs) % 1.0 for i in range(n)]

        ecg_ph = beat_phases(ECG_FS)
        lead_ii = [_ecg(p, _ECG_WAVES_II) + random.gauss(0, 0.01) for p in ecg_ph]
        lead_i = [_ecg(p, _ECG_WAVES_I) + random.gauss(0, 0.01) for p in ecg_ph]
        lead_iii = [ii - i for i, ii in zip(lead_i, lead_ii)]

        span = c["sys"] - c["dia"]
        ibp = [c["dia"] + span * _arterial(p) for p in beat_phases(IBP_FS)]

        n_co2 = round(CO2_FS * self._chunk_s)
        co2 = [c["etco2"] * _capnogram((start_breath + i * breath_hz / CO2_FS) % 1.0) for i in range(n_co2)]

        self._beat_phase = (start_beat + beat_hz * self._chunk_s) % 1.0
        self._breath_phase = (start_breath + breath_hz * self._chunk_s) % 1.0
        return {"ecg.lead_i": lead_i, "ecg.lead_ii": lead_ii, "ecg.lead_iii": lead_iii,
                "co2.wave": co2, "ibp.wave": ibp}
