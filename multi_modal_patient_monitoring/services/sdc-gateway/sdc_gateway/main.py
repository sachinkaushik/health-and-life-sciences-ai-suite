# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""SDC gateway: publishes MMPM beds (patient monitors / multimodal devices) as IEEE 11073 SDC providers."""

from __future__ import annotations

import logging
import os
import socket

import uvicorn
from sdc11073.certloader import mk_ssl_contexts_from_folder
from sdc11073.wsdiscovery import WSDiscovery

from . import mdib_model as m
from .ai_ecg_poller import AiEcgPoller
from .api import create_app
from .devices import DeviceConfig, DeviceManager
from .rppg_ingest import start_rppg_server

log = logging.getLogger("sdc_gateway")

DEFAULT_EPR = "urn:uuid:6b3e0c1e-5f7a-4d2b-9c8e-1a2b3c4d5e01"


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _env_list(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


def detect_bind_ip() -> str:
    """IP of the interface holding the default route (WS-Discovery needs a concrete address)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def main() -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    for noisy in ("sdc", "sdc11073"):
        logging.getLogger(noisy).setLevel(os.getenv("SDC_LOG_LEVEL", "WARNING"))

    bind_ip = os.getenv("SDC_BIND_IP") or detect_bind_ip()
    ssl_dir = os.getenv("SDC_SSL_DIR")
    rppg_port = int(os.getenv("RPPG_GRPC_PORT", "50061"))
    cfg = DeviceConfig(
        facility=os.getenv("SDC_FACILITY", "MMPM"),
        point_of_care=os.getenv("SDC_POINT_OF_CARE", "ICU"),
        sim_enabled=_env_bool("SIM_ENABLED", True),
        wave_chunk_s=int(os.getenv("WAVE_CHUNK_MS", "200")) / 1000.0,
        # Default camera feed for multimodal beds: the pose-estimation MJPEG stream on this host.
        video_urls=tuple(_env_list("VIDEO_STREAM_URLS") or [f"http://{bind_ip}:8085/video_feed"]),
        max_devices=int(os.getenv("SDC_MAX_DEVICES", "16")),
    )

    wsd = WSDiscovery(bind_ip)
    wsd.start()
    ssl_ctx = mk_ssl_contexts_from_folder(ssl_dir) if ssl_dir else None
    manager = DeviceManager(wsd, ssl_ctx, cfg)

    # bed-01 is the primary multimodal bed: it carries the live rPPG and AI-ECG workloads.
    primary = manager.add(m.MULTIMODAL, ai=True, primary=True, epr=os.getenv("SDC_EPR", DEFAULT_EPR))
    for kind in _env_list("SDC_EXTRA_DEVICES"):
        try:
            manager.add(kind)
        except Exception as exc:
            log.error("cannot add extra device %r: %s", kind, exc)
    log.info("SDC gateway up on %s (TLS %s), %d bed(s)", bind_ip, "on" if ssl_ctx else "off",
             len(manager.list()))

    rppg_server = start_rppg_server(primary.writer, rppg_port) if _env_bool("RPPG_ENABLED", True) else None
    poller = None
    if _env_bool("AI_ECG_ENABLED", True):
        poller = AiEcgPoller(primary.writer, os.getenv("AI_ECG_URL", "http://localhost:8000/predict_stream_next"),
                             float(os.getenv("AI_ECG_POLL_SECONDS", "1.0")))
        poller.start()

    # Blocks until SIGINT/SIGTERM (uvicorn installs the handlers).
    uvicorn.run(create_app(manager), host=os.getenv("SDC_MGMT_HOST", "127.0.0.1"),
                port=int(os.getenv("SDC_MGMT_PORT", "8093")), log_level="warning")

    log.info("shutting down")
    if poller:
        poller.stop()
    if rppg_server:
        rppg_server.stop(grace=1)
    manager.stop_all()
    wsd.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
