# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""SDC bridge: SDC consumer that feeds the MMPM aggregator (gRPC) and AI-ECG pollers (HTTP)."""

from __future__ import annotations

import logging
import os
import socket

import uvicorn
from sdc11073.certloader import mk_ssl_contexts_from_folder

from .api import create_app
from .forwarder import AggregatorStream
from .sdc_client import SdcConnector
from .translator import Translator

log = logging.getLogger("sdc_bridge")

DEFAULT_PROVIDER_EPR = "urn:uuid:6b3e0c1e-5f7a-4d2b-9c8e-1a2b3c4d5e01"


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

    ssl_dir = os.getenv("SDC_SSL_DIR")
    stream = AggregatorStream(f"{os.getenv('GRPC_HOST', 'localhost')}:{os.getenv('GRPC_PORT', '50051')}")
    translator = Translator(
        stream,
        device_id_prefix=os.getenv("DEVICE_ID_PREFIX", "sdc-monitor"),
        rppg_device_id=os.getenv("RPPG_DEVICE_ID", "rppg-001"),
        wave_window_s=int(os.getenv("WAVE_FORWARD_MS", "1000")) / 1000.0,
    )
    connector = SdcConnector(
        translator,
        bind_ip=os.getenv("SDC_BIND_IP") or detect_bind_ip(),
        provider_epr=os.getenv("SDC_PROVIDER_EPR", DEFAULT_PROVIDER_EPR) or None,
        provider_xaddr=os.getenv("SDC_PROVIDER_XADDR") or None,
        ssl_context=mk_ssl_contexts_from_folder(ssl_dir) if ssl_dir else None,
    )
    stream.start()
    connector.start()
    try:
        uvicorn.run(create_app(translator, connector), host="0.0.0.0",
                    port=int(os.getenv("CONTROL_PORT", "8092")), log_level="warning")
    finally:
        connector.stop()
        stream.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
