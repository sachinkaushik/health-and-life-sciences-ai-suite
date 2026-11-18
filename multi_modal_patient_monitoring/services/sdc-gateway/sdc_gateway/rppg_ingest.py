# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""gRPC VitalService endpoint that receives rPPG vitals and publishes them on SDC."""

from __future__ import annotations

import logging
from concurrent import futures

import grpc
from google.protobuf.empty_pb2 import Empty

from proto import vital_pb2, vital_pb2_grpc

from .mdib_model import RPPG_FS
from .writer import MdibWriter

log = logging.getLogger(__name__)

# rPPG metric name -> (numeric handle, waveform handle)
_RPPG_MAP = {
    "HEART_RATE": ("rppg.hr", "rppg.pulse"),
    "RESP_RATE": ("rppg.rr", "rppg.resp"),
    "HEART_RATE_AVG": ("rppg.hr_avg", None),
    "RESP_RATE_AVG": ("rppg.rr_avg", None),
}


class RppgIngest(vital_pb2_grpc.VitalServiceServicer):
    def __init__(self, writer: MdibWriter):
        self._writer = writer
        self._warned_fs = False

    def _apply(self, vital) -> None:
        handles = _RPPG_MAP.get(vital.metric)
        if handles is None:
            log.debug("ignoring rPPG metric %s", vital.metric)
            return
        numeric_handle, wave_handle = handles
        t = vital.timestamp / 1000.0 if vital.timestamp else None
        self._writer.set_metrics({numeric_handle: vital.value}, determination_time=t)
        if wave_handle and len(vital.waveform) > 0:
            if vital.waveform_frequency_hz and vital.waveform_frequency_hz != int(RPPG_FS) and not self._warned_fs:
                log.warning("rPPG waveform is %d Hz, SDC descriptor declares %d Hz",
                            vital.waveform_frequency_hz, int(RPPG_FS))
                self._warned_fs = True
            self._writer.push_samples({wave_handle: list(vital.waveform)}, determination_time=t, places=5)

    def StreamVitals(self, request_iterator, context):
        log.info("rPPG stream opened from %s", context.peer())
        count = 0
        for vital in request_iterator:
            try:
                self._apply(vital)
                count += 1
            except Exception:
                log.exception("failed to publish rPPG vital %s", vital.metric)
        log.info("rPPG stream closed after %d vitals", count)
        return Empty()

    def PublishVital(self, request, context):
        try:
            self._apply(request)
            return vital_pb2.VitalResponse(success=True, message="published")
        except Exception as exc:
            return vital_pb2.VitalResponse(success=False, message=str(exc))


def start_rppg_server(writer: MdibWriter, port: int) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    vital_pb2_grpc.add_VitalServiceServicer_to_server(RppgIngest(writer), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    log.info("rPPG gRPC ingest listening on :%d", port)
    return server
