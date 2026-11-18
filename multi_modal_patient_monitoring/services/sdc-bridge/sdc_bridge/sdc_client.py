# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Discovers the SDC provider, subscribes to its reports and reconnects when it goes away."""

from __future__ import annotations

import logging
import threading

from sdc11073 import observableproperties
from sdc11073.consumer import SdcConsumer
from sdc11073.definitions_sdc import SdcV1Definitions
from sdc11073.mdib.consumermdib import ConsumerMdib
from sdc11073.wsdiscovery import WSDiscovery

from .translator import Translator

log = logging.getLogger(__name__)


class SdcConnector:
    def __init__(self, translator: Translator, bind_ip: str, provider_epr: str | None,
                 provider_xaddr: str | None = None, ssl_context=None, retry_s: float = 5.0):
        self._translator = translator
        self._bind_ip = bind_ip
        self._epr = provider_epr
        self._xaddr = provider_xaddr
        self._ssl = ssl_context
        self._retry_s = retry_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="sdc-connector")
        self._wsd: WSDiscovery | None = None
        self._client: SdcConsumer | None = None
        self._mdib: ConsumerMdib | None = None
        self.provider: str | None = None

    @property
    def connected(self) -> bool:
        return self._client is not None and bool(self._client.is_connected)

    def start(self) -> None:
        if not self._xaddr:
            self._wsd = WSDiscovery(self._bind_ip)
            self._wsd.start()
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=10)
        self._disconnect()
        if self._wsd:
            self._wsd.stop()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                if self._connect():
                    while not self._stop.is_set() and self.connected:
                        self._stop.wait(1.0)
                    if not self._stop.is_set():
                        log.warning("lost SDC provider %s, reconnecting", self.provider)
            except Exception as exc:
                log.warning("SDC connection attempt failed: %s", exc)
                log.debug("connection failure detail", exc_info=True)
            self._disconnect()
            self._stop.wait(self._retry_s)

    def _connect(self) -> bool:
        if self._xaddr:
            client = SdcConsumer(self._xaddr, SdcV1Definitions, self._ssl)
            self.provider = self._xaddr
        else:
            # Drop cached entries so a restarted provider's new address is picked up.
            self._wsd.clear_remote_services()
            services = self._wsd.search_services(types=SdcV1Definitions.MedicalDeviceTypesFilter, timeout=5)
            match = [s for s in services if not self._epr or s.epr == self._epr]
            if not match:
                log.info("SDC provider %s not found yet (%d SDC devices seen)", self._epr or "<any>", len(services))
                return False
            client = SdcConsumer.from_wsd_service(match[0], ssl_context_container=self._ssl)
            self.provider = match[0].epr
        client.start_all(not_subscribed_actions=None)
        self._client = client
        mdib = ConsumerMdib(client)
        mdib.init_mdib()
        self._translator.bind(mdib)
        observableproperties.bind(mdib, metrics_by_handle=self._translator.on_metrics,
                                  waveform_by_handle=self._translator.on_waves)
        self._mdib = mdib
        log.info("subscribed to SDC provider %s", self.provider)
        return True

    def _disconnect(self) -> None:
        client, self._client, self._mdib = self._client, None, None
        if client is not None:
            try:
                client.stop_all(unsubscribe=True)
            except Exception:
                log.debug("stop_all failed", exc_info=True)
