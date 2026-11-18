# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Polls the AI-ECG service and publishes each analysed strip on SDC."""

from __future__ import annotations

import logging
import threading
import time

import requests

from . import mdib_model as m
from .writer import MdibWriter

log = logging.getLogger(__name__)


class AiEcgPoller:
    def __init__(self, writer: MdibWriter, url: str, interval_s: float = 1.0):
        self._writer = writer
        self._url = url
        self._interval = interval_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="ai-ecg-poller")

    def start(self) -> None:
        self._thread.start()
        log.info("AI-ECG poller started: %s every %.1f s", self._url, self._interval)

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        failures = 0
        while not self._stop.is_set():
            try:
                resp = requests.get(self._url, timeout=10)
                resp.raise_for_status()
                self._publish(resp.json())
                failures = 0
            except Exception as exc:
                failures += 1
                # Log the first failure and then every 30th to keep logs readable while AI-ECG starts.
                if failures == 1 or failures % 30 == 0:
                    log.warning("AI-ECG poll failed (%d): %s", failures, exc)
            self._stop.wait(self._interval)

    def _publish(self, data: dict) -> None:
        signal = data.get("signal") or []
        # Millisecond precision so wave and label share the exact BICEPS timestamp.
        t = round(time.time(), 3)
        self._writer.push_samples({m.W_AI_STRIP: signal}, determination_time=t, places=5)
        self._writer.set_metrics({
            m.H_AI_RHYTHM: str(data.get("result", "Unknown")),
            m.H_AI_SOURCE: str(data.get("file", "")),
            m.H_AI_LATENCY: float(data.get("inference_ms", 0.0)),
        }, determination_time=t)
