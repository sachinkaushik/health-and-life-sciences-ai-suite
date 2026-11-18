# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Maps SDC metric codes to the metric names MMPM's aggregator and UI already use."""

from __future__ import annotations

from dataclasses import dataclass

MDC_CS = "urn:oid:1.2.840.10004.1.1.1.0.0.1"
VENDOR_CS = "urn:intel:hls:mmpm"

DEVICE = "device"
RPPG = "rppg"
AI_ECG = "ai-ecg"


@dataclass(frozen=True)
class Target:
    group: str
    metric: str
    device_type: str | None = None
    device_suffix: str = ""
    unit: str | None = None


def _ecg(metric: str) -> Target:
    return Target(DEVICE, metric, "ECG_Simulator", "ecg")


def _co2(metric: str) -> Target:
    return Target(DEVICE, metric, "CO2_Simulator", "co2")


def _ibp(metric: str) -> Target:
    return Target(DEVICE, metric, "IBP_Simulator", "ibp")


# Device-type names match what dds-bridge reports for the OpenICE simulators.
CODE_MAP: dict[tuple[str, str], Target] = {
    (MDC_CS, "147842"): _ecg("MDC_ECG_HEART_RATE"),
    (MDC_CS, "151570"): _ecg("MDC_TTHOR_RESP_RATE"),
    (MDC_CS, "131329"): _ecg("MDC_ECG_LEAD_I"),
    (MDC_CS, "131330"): _ecg("MDC_ECG_LEAD_II"),
    (MDC_CS, "131389"): _ecg("MDC_ECG_LEAD_III"),
    (MDC_CS, "151708"): _co2("MDC_AWAY_CO2_ET"),
    (MDC_CS, "151586"): _co2("MDC_CO2_RESP_RATE"),
    (MDC_CS, "151704"): _co2("MDC_AWAY_CO2"),
    (MDC_CS, "150037"): _ibp("MDC_PRESS_BLD_ART_ABP_SYS"),
    (MDC_CS, "150038"): _ibp("MDC_PRESS_BLD_ART_ABP_DIA"),
    (MDC_CS, "150036"): _ibp("MDC_PRESS_BLD"),
    (VENDOR_CS, "RPPG_HEART_RATE"): Target(RPPG, "HEART_RATE", unit="BPM"),
    (VENDOR_CS, "RPPG_RESP_RATE"): Target(RPPG, "RESP_RATE", unit="BrPM"),
    (VENDOR_CS, "RPPG_HEART_RATE_AVG"): Target(RPPG, "HEART_RATE_AVG", unit="BPM"),
    (VENDOR_CS, "RPPG_RESP_RATE_AVG"): Target(RPPG, "RESP_RATE_AVG", unit="BrPM"),
    (VENDOR_CS, "RPPG_PULSE_WAVE"): Target(RPPG, "HEART_RATE", unit="BPM"),
    (VENDOR_CS, "RPPG_RESP_WAVE"): Target(RPPG, "RESP_RATE", unit="BrPM"),
    (VENDOR_CS, "AIECG_SIGNAL"): Target(AI_ECG, "signal"),
    (VENDOR_CS, "AIECG_RHYTHM"): Target(AI_ECG, "result"),
    (VENDOR_CS, "AIECG_SOURCE"): Target(AI_ECG, "file"),
    (VENDOR_CS, "AIECG_INFERENCE_MS"): Target(AI_ECG, "inference_ms"),
}


def lookup(coded_value) -> Target | None:
    if coded_value is None:
        return None
    return CODE_MAP.get((coded_value.CodingSystem or MDC_CS, coded_value.Code))
