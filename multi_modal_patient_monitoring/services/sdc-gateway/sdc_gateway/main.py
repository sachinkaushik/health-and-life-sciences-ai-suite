# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""SDC gateway: publishes MMPM device, rPPG and AI-ECG data as one IEEE 11073 SDC provider."""

from __future__ import annotations

import logging
import os
import signal
import socket
import threading

from sdc11073.certloader import mk_ssl_contexts_from_folder
from sdc11073.location import SdcLocation
from sdc11073.provider import SdcProvider
from sdc11073.wsdiscovery import WSDiscovery
from sdc11073.xml_types.dpws_types import ThisDeviceType, ThisModelType

from .ai_ecg_poller import AiEcgPoller
from .mdib_model import build_mdib
from .rppg_ingest import start_rppg_server
from .simulator import DeviceSimulator
from .writer import MdibWriter

log = logging.getLogger("sdc_gateway")

DEFAULT_EPR = "urn:uuid:6b3e0c1e-5f7a-4d2b-9c8e-1a2b3c4d5e01"


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


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
    epr = os.getenv("SDC_EPR", DEFAULT_EPR)
    ssl_dir = os.getenv("SDC_SSL_DIR")
    rppg_port = int(os.getenv("RPPG_GRPC_PORT", "50061"))
    wave_chunk_s = int(os.getenv("WAVE_CHUNK_MS", "200")) / 1000.0

    mdib = build_mdib()
    writer = MdibWriter(mdib)

    wsd = WSDiscovery(bind_ip)
    wsd.start()
    ssl_ctx = mk_ssl_contexts_from_folder(ssl_dir) if ssl_dir else None
    provider = SdcProvider(
        ws_discovery=wsd,
        this_model=ThisModelType(manufacturer="Intel", model_name="MMPM SDC Gateway",
                                 model_number="1.0", model_url="https://www.intel.com"),
        this_device=ThisDeviceType(friendly_name=os.getenv("SDC_FRIENDLY_NAME", "MMPM Patient Monitor"),
                                   firmware_version="1.0", serial_number=os.getenv("SDC_SERIAL", "MMPM-0001")),
        device_mdib_container=mdib,
        epr=epr,
        ssl_context_container=ssl_ctx,
    )
    provider.start_all(start_rtsample_loop=False)
    provider.set_location(SdcLocation(fac=os.getenv("SDC_FACILITY", "MMPM"),
                                      poc=os.getenv("SDC_POINT_OF_CARE", "ICU"),
                                      bed=os.getenv("SDC_BED", "BED01")))
    log.info("SDC provider %s up on %s (TLS %s)", epr, bind_ip, "on" if ssl_ctx else "off")

    sim = DeviceSimulator(writer, wave_chunk_s=wave_chunk_s) if _env_bool("SIM_ENABLED", True) else None
    if sim:
        sim.start()
    rppg_server = start_rppg_server(writer, rppg_port) if _env_bool("RPPG_ENABLED", True) else None
    poller = None
    if _env_bool("AI_ECG_ENABLED", True):
        poller = AiEcgPoller(writer, os.getenv("AI_ECG_URL", "http://localhost:8000/predict_stream_next"),
                             float(os.getenv("AI_ECG_POLL_SECONDS", "1.0")))
        poller.start()

    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    stop.wait()

    log.info("shutting down")
    if poller:
        poller.stop()
    if sim:
        sim.stop()
    if rppg_server:
        rppg_server.stop(grace=1)
    provider.stop_all()
    wsd.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
