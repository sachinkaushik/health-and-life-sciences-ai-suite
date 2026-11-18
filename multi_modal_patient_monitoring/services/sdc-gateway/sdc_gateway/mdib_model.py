# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""MDIB layout of the MMPM SDC devices.

Metric handles follow the SDC-Dashboard multiparameter-monitor contract (numeric.* / wave.*), so
any consumer built against that contract renders MMPM beds without extra mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sdc11073.definitions_sdc import SdcV1Definitions
from sdc11073.mdib import ProviderMdib
from sdc11073.xml_types import pm_qnames, pm_types

# Coding system for MMPM-specific codes (rPPG / AI-ECG); None means IEEE 11073-10101.
VENDOR_CS = "urn:intel:hls:mmpm"
VIDEO_CS = "urn:research:video"
UCUM_CS = "urn:oid:1.2.840.10008.2.16.4"

NUMERIC = "numeric"
WAVE = "wave"
STRING = "string"

MONITOR = "monitor"
MULTIMODAL = "multimodal"
DEVICE_KINDS = (MONITOR, MULTIMODAL)

# (UCUM code, IEEE 11073-10101 symbolic name)
U_BEAT_PER_MIN = ("/min", "MDC_DIM_BEAT_PER_MIN")
U_RESP_PER_MIN = ("/min", "MDC_DIM_RESP_PER_MIN")
U_MMHG = ("mm[Hg]", "MDC_DIM_MMHG")
U_MILLI_VOLT = ("mV", "MDC_DIM_MILLI_VOLT")
U_PERCENT = ("%", "MDC_DIM_PERCENT")
U_DEGC = ("Cel", "MDC_DIM_DEGC")
U_DIMLESS = ("1", "MDC_DIM_DIMLESS")
U_MILLI_SEC = ("ms", "MDC_DIM_MILLI_SEC")

# Bedside vitals
H_HR = "numeric.hr"
H_RR = "numeric.rr"
H_SPO2 = "numeric.spo2"
H_TEMP = "numeric.temp"
H_ETCO2 = "numeric.etco2"
H_RR_CO2 = "numeric.rr_co2"
H_BP_SYS = "numeric.nibp_sys"
H_BP_DIA = "numeric.nibp_dia"
H_BP_MAP = "numeric.nibp_map"
W_ECG_II = "wave.ecg_ii"
W_PLETH = "wave.pleth"
W_CO2 = "wave.co2"
W_ABP = "wave.abp"
# rPPG (camera)
H_RPPG_HR = "numeric.rppg_hr"
H_RPPG_RR = "numeric.rppg_rr"
H_RPPG_HR_AVG = "numeric.rppg_hr_avg"
H_RPPG_RR_AVG = "numeric.rppg_rr_avg"
W_RPPG_PULSE = "wave.rppg"
W_RPPG_RESP = "wave.rppg_resp"
# AI-ECG; handles avoid "ecg" because consumers route any "*ecg*" wave to the live ECG strip.
W_AI_STRIP = "wave.ai_rhythm_strip"
H_AI_RHYTHM = "string.ai_rhythm"
H_AI_SOURCE = "string.ai_rhythm_source"
H_AI_LATENCY = "numeric.ai_rhythm_latency"
# Room camera
H_VIDEO_URL = "string.video_stream_url"


@dataclass(frozen=True)
class MetricSpec:
    handle: str
    kind: str
    code: str
    ref_id: str
    unit: tuple[str, str]
    coding_system: str | None = None
    sample_rate_hz: float = 0.0
    resolution: str = "1"


@dataclass(frozen=True)
class ChannelSpec:
    handle: str
    code: str
    ref_id: str
    metrics: tuple[MetricSpec, ...]


@dataclass(frozen=True)
class VmdSpec:
    handle: str
    code: str
    ref_id: str
    channels: tuple[ChannelSpec, ...]


ECG_FS = 250.0
PLETH_FS = 100.0
CO2_FS = 20.0
IBP_FS = 120.0
RPPG_FS = 30.0
AI_ECG_FS = 360.0

MDS_HANDLE = "mds.mmpm"
MDS_CODE = ("69965", "MDC_DEV_MON_PHYSIO_MULTI_PARAM_MDS")

DEVICE_VMD = VmdSpec("vmd.device", "DEVICE_VMD", "MMPM_DEVICE_VMD", (
    ChannelSpec("ch.ecg", "ECG_CHAN", "MMPM_ECG_CHAN", (
        MetricSpec(H_HR, NUMERIC, "147842", "MDC_ECG_HEART_RATE", U_BEAT_PER_MIN),
        MetricSpec(H_RR, NUMERIC, "151570", "MDC_TTHOR_RESP_RATE", U_RESP_PER_MIN),
        MetricSpec(W_ECG_II, WAVE, "131330", "MDC_ECG_ELEC_POTL_II", U_MILLI_VOLT,
                   sample_rate_hz=ECG_FS, resolution="0.001"),
    )),
    ChannelSpec("ch.spo2", "SPO2_CHAN", "MMPM_SPO2_CHAN", (
        MetricSpec(H_SPO2, NUMERIC, "150456", "MDC_PULS_OXIM_SAT_O2", U_PERCENT),
        MetricSpec(W_PLETH, WAVE, "150452", "MDC_PULS_OXIM_PLETH", U_DIMLESS,
                   sample_rate_hz=PLETH_FS, resolution="0.001"),
    )),
    ChannelSpec("ch.temp", "TEMP_CHAN", "MMPM_TEMP_CHAN", (
        MetricSpec(H_TEMP, NUMERIC, "150364", "MDC_TEMP_BODY", U_DEGC, resolution="0.1"),
    )),
    ChannelSpec("ch.co2", "CO2_CHAN", "MMPM_CO2_CHAN", (
        MetricSpec(H_ETCO2, NUMERIC, "151708", "MDC_AWAY_CO2_ET", U_MMHG),
        MetricSpec(H_RR_CO2, NUMERIC, "151586", "MDC_CO2_RESP_RATE", U_RESP_PER_MIN),
        MetricSpec(W_CO2, WAVE, "151704", "MDC_AWAY_CO2", U_MMHG,
                   sample_rate_hz=CO2_FS, resolution="0.1"),
    )),
    # Arterial-line codes under the contract's numeric.nibp_* handles.
    ChannelSpec("ch.ibp", "IBP_CHAN", "MMPM_IBP_CHAN", (
        MetricSpec(H_BP_SYS, NUMERIC, "150037", "MDC_PRESS_BLD_ART_ABP_SYS", U_MMHG),
        MetricSpec(H_BP_DIA, NUMERIC, "150038", "MDC_PRESS_BLD_ART_ABP_DIA", U_MMHG),
        MetricSpec(H_BP_MAP, NUMERIC, "150039", "MDC_PRESS_BLD_ART_ABP_MEAN", U_MMHG),
        MetricSpec(W_ABP, WAVE, "150036", "MDC_PRESS_BLD_ART_ABP", U_MMHG,
                   sample_rate_hz=IBP_FS, resolution="0.1"),
    )),
), )

RPPG_VMD = VmdSpec("vmd.rppg", "RPPG_VMD", "MMPM_RPPG_VMD", (
    ChannelSpec("ch.rppg", "RPPG_CHAN", "MMPM_RPPG_CHAN", (
        MetricSpec(H_RPPG_HR, NUMERIC, "RPPG_HEART_RATE", "RPPG_HEART_RATE", U_BEAT_PER_MIN,
                   coding_system=VENDOR_CS, resolution="0.1"),
        MetricSpec(H_RPPG_RR, NUMERIC, "RPPG_RESP_RATE", "RPPG_RESP_RATE", U_RESP_PER_MIN,
                   coding_system=VENDOR_CS, resolution="0.1"),
        MetricSpec(H_RPPG_HR_AVG, NUMERIC, "RPPG_HEART_RATE_AVG", "RPPG_HEART_RATE_AVG",
                   U_BEAT_PER_MIN, coding_system=VENDOR_CS, resolution="0.1"),
        MetricSpec(H_RPPG_RR_AVG, NUMERIC, "RPPG_RESP_RATE_AVG", "RPPG_RESP_RATE_AVG",
                   U_RESP_PER_MIN, coding_system=VENDOR_CS, resolution="0.1"),
        MetricSpec(W_RPPG_PULSE, WAVE, "RPPG_PULSE_WAVE", "RPPG_PULSE_WAVE", U_DIMLESS,
                   coding_system=VENDOR_CS, sample_rate_hz=RPPG_FS, resolution="0.0001"),
        MetricSpec(W_RPPG_RESP, WAVE, "RPPG_RESP_WAVE", "RPPG_RESP_WAVE", U_DIMLESS,
                   coding_system=VENDOR_CS, sample_rate_hz=RPPG_FS, resolution="0.0001"),
    )),
))

AI_ECG_VMD = VmdSpec("vmd.aiecg", "AIECG_VMD", "MMPM_AIECG_VMD", (
    ChannelSpec("ch.aiecg", "AIECG_CHAN", "MMPM_AIECG_CHAN", (
        MetricSpec(W_AI_STRIP, WAVE, "AIECG_SIGNAL", "AIECG_SIGNAL", U_MILLI_VOLT,
                   coding_system=VENDOR_CS, sample_rate_hz=AI_ECG_FS, resolution="0.0001"),
        MetricSpec(H_AI_RHYTHM, STRING, "AIECG_RHYTHM", "AIECG_RHYTHM", U_DIMLESS,
                   coding_system=VENDOR_CS),
        MetricSpec(H_AI_SOURCE, STRING, "AIECG_SOURCE", "AIECG_SOURCE", U_DIMLESS,
                   coding_system=VENDOR_CS),
        MetricSpec(H_AI_LATENCY, NUMERIC, "AIECG_INFERENCE_MS", "AIECG_INFERENCE_MS",
                   U_MILLI_SEC, coding_system=VENDOR_CS, resolution="0.01"),
    )),
))

VIDEO_VMD = VmdSpec("vmd.video", "VIDEO_VMD", "MMPM_VIDEO_VMD", (
    ChannelSpec("ch.video", "VIDEO_MOD", "VIDEO_MOD", (
        MetricSpec(H_VIDEO_URL, STRING, "VIDEO_STREAM_URL", "VIDEO_STREAM_URL", U_DIMLESS,
                   coding_system=VIDEO_CS),
    )),
))


def vmds_for(kind: str, ai: bool) -> tuple[VmdSpec, ...]:
    """Monitor = bedside vitals; multimodal adds the room camera and, on the AI bed, rPPG + AI-ECG."""
    if kind not in DEVICE_KINDS:
        raise ValueError(f"unknown device kind {kind!r}")
    vmds = [DEVICE_VMD]
    if kind == MULTIMODAL:
        vmds.append(VIDEO_VMD)
        if ai:
            vmds += [RPPG_VMD, AI_ECG_VMD]
    return tuple(vmds)


_DESCRIPTOR_QNAME = {
    NUMERIC: pm_qnames.NumericMetricDescriptor,
    WAVE: pm_qnames.RealTimeSampleArrayMetricDescriptor,
    STRING: pm_qnames.StringMetricDescriptor,
}


def _coded(code: str, ref_id: str, coding_system: str | None = None) -> pm_types.CodedValue:
    return pm_types.CodedValue(code=code, coding_system=coding_system, symbolic_code_name=ref_id)


def build_mdib(vmds: tuple[VmdSpec, ...]) -> ProviderMdib:
    mdib = ProviderMdib(sdc_definitions=SdcV1Definitions)
    model = mdib.data_model

    def add(qname, handle, parent):
        descr = model.mk_descriptor_container(qname, handle=handle, parent_descriptor=parent)
        mdib.descriptions.add_object(descr)
        return descr

    mds = add(pm_qnames.MdsDescriptor, MDS_HANDLE, None)
    mds.Type = _coded(*MDS_CODE)
    add(pm_qnames.SystemContextDescriptor, "mds.mmpm.sc", mds)

    for vmd_spec in vmds:
        vmd = add(pm_qnames.VmdDescriptor, vmd_spec.handle, mds)
        vmd.Type = _coded(vmd_spec.code, vmd_spec.ref_id, VENDOR_CS)
        for ch_spec in vmd_spec.channels:
            ch = add(pm_qnames.ChannelDescriptor, ch_spec.handle, vmd)
            ch.Type = _coded(ch_spec.code, ch_spec.ref_id, VENDOR_CS)
            for m in ch_spec.metrics:
                d = add(_DESCRIPTOR_QNAME[m.kind], m.handle, ch)
                d.Type = _coded(m.code, m.ref_id, m.coding_system)
                d.Unit = _coded(m.unit[0], m.unit[1], UCUM_CS)
                d.MetricCategory = pm_types.MetricCategory.MEASUREMENT
                d.MetricAvailability = pm_types.MetricAvailability.CONTINUOUS
                if m.kind != STRING:
                    d.Resolution = Decimal(m.resolution)
                if m.kind == WAVE:
                    d.SamplePeriod = 1.0 / m.sample_rate_hz

    mdib.xtra.ensure_location_context_descriptor()
    mdib.xtra.mk_state_containers_for_all_descriptors()

    for state in mdib.states.objects:
        if getattr(state, "is_metric_state", False):
            state.ActivationState = pm_types.ComponentActivation.ON
            state.mk_metric_value()
            state.MetricValue.MetricQuality.Validity = pm_types.MeasurementValidity.VALID
    return mdib
