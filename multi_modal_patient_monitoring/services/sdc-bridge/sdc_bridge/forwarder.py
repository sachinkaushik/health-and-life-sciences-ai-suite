# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Long-lived gRPC StreamVitals client towards the MMPM aggregator."""

from __future__ import annotations

import logging
import queue
import threading

import grpc

from proto import vital_pb2_grpc

log = logging.getLogger(__name__)


class AggregatorStream:
    def __init__(self, target: str, max_queue: int = 2000, retry_s: float = 2.0):
        self._target = target
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue)
        self._retry_s = retry_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="aggregator-stream")
        self.dropped = 0

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def send(self, vital) -> None:
        try:
            self._queue.put_nowait(vital)
        except queue.Full:
            self.dropped += 1
            if self.dropped % 500 == 1:
                log.warning("aggregator queue full, dropped %d vitals so far", self.dropped)

    def _requests(self):
        while not self._stop.is_set():
            try:
                yield self._queue.get(timeout=1.0)
            except queue.Empty:
                continue

    def _run(self) -> None:
        while not self._stop.is_set():
            channel = grpc.insecure_channel(self._target)
            try:
                log.info("opening StreamVitals to %s", self._target)
                vital_pb2_grpc.VitalServiceStub(channel).StreamVitals(self._requests())
            except grpc.RpcError as exc:
                log.warning("aggregator stream ended: %s", exc.code())
            finally:
                channel.close()
            self._stop.wait(self._retry_s)
