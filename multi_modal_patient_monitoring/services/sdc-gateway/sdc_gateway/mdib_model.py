# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""MDIB layout of the MMPM SDC gateway (one MDS, one VMD per data source)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sdc11073.definitions_sdc import SdcV1Definitions
from sdc11073.mdib import ProviderMdib
from sdc11073.xml_types import pm_qnames, pm_types

# Coding system for MMPM-specific codes (rPPG / AI-ECG); None means IEEE 11073-10101.
VENDOR_CS = "urn:intel:hls:mmpm"

NUMERIC = "numeric"
WAVE = "wave"
STRING = "string"

# Context-free codes per IEEE 11073-10101; confirm against NIST RTMMS before clinical use.
DIM_BEAT_PER_MIN = ("264864", "MDC_DIM_BEAT_PER_MIN")
DIM_RESP_PER_MIN = ("264928", "MDC_DIM_RESP_PER_MIN")
DIM_MMHG = ("266016", "MDC_DIM_MMHG")
DIM_MILLI_VOLT = ("266418", "MDC_DIM_MILLI_VOLT")
DIM_DIMLESS = ("262656", "MDC_DIM_DIMLESS")
DIM_MILLI_SEC = ("264338", "MDC_DIM_MILLI_SEC")


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
CO2_FS = 20.0
IBP_FS = 120.0
RPPG_FS = 30.0
AI_ECG_FS = 360.0

MDS_HANDLE = "mds.mmpm"
MDS_CODE = ("69965", "MDC_DEV_MON_PHYSIO_MULTI_PARAM_MDS")

DEVICE_VMD = VmdSpec("vmd.device", "DEVICE_VMD", "MMPM_DEVICE_VMD", (
    ChannelSpec("ch.ecg", "ECG_CHAN", "MMPM_ECG_CHAN", (
        MetricSpec("ecg.hr", NUMERIC, "147842", "MDC_ECG_HEART_RATE", DIM_BEAT_PER_MIN),
        MetricSpec("ecg.rr", NUMERIC, "151570", "MDC_TTHOR_RESP_RATE", DIM_RESP_PER_MIN),
        MetricSpec("ecg.lead_i", WAVE, "131329", "MDC_ECG_ELEC_POTL_I", DIM_MILLI_VOLT,
                   sample_rate_hz=ECG_FS, resolution="0.001"),
        MetricSpec("ecg.lead_ii", WAVE, "131330", "MDC_ECG_ELEC_POTL_II", DIM_MILLI_VOLT,
                   sample_rate_hz=ECG_FS, resolution="0.001"),
        MetricSpec("ecg.lead_iii", WAVE, "131389", "MDC_ECG_ELEC_POTL_III", DIM_MILLI_VOLT,
                   sample_rate_hz=ECG_FS, resolution="0.001"),
    )),
    ChannelSpec("ch.co2", "CO2_CHAN", "MMPM_CO2_CHAN", (
        MetricSpec("co2.et", NUMERIC, "151708", "MDC_AWAY_CO2_ET", DIM_MMHG),
        MetricSpec("co2.rr", NUMERIC, "151586", "MDC_CO2_RESP_RATE", DIM_RESP_PER_MIN),
        MetricSpec("co2.wave", WAVE, "151704", "MDC_AWAY_CO2", DIM_MMHG,
                   sample_rate_hz=CO2_FS, resolution="0.1"),
    )),
    ChannelSpec("ch.ibp", "IBP_CHAN", "MMPM_IBP_CHAN", (
        MetricSpec("ibp.sys", NUMERIC, "150037", "MDC_PRESS_BLD_ART_ABP_SYS", DIM_MMHG),
        MetricSpec("ibp.dia", NUMERIC, "150038", "MDC_PRESS_BLD_ART_ABP_DIA", DIM_MMHG),
        MetricSpec("ibp.mean", NUMERIC, "150039", "MDC_PRESS_BLD_ART_ABP_MEAN", DIM_MMHG),
        MetricSpec("ibp.wave", WAVE, "150036", "MDC_PRESS_BLD_ART_ABP", DIM_MMHG,
                   sample_rate_hz=IBP_FS, resolution="0.1"),
    )),
), )

RPPG_VMD = VmdSpec("vmd.rppg", "RPPG_VMD", "MMPM_RPPG_VMD", (
    ChannelSpec("ch.rppg", "RPPG_CHAN", "MMPM_RPPG_CHAN", (
        MetricSpec("rppg.hr", NUMERIC, "RPPG_HEART_RATE", "RPPG_HEART_RATE", DIM_BEAT_PER_MIN,
                   coding_system=VENDOR_CS, resolution="0.1"),
        MetricSpec("rppg.rr", NUMERIC, "RPPG_RESP_RATE", "RPPG_RESP_RATE", DIM_RESP_PER_MIN,
                   coding_system=VENDOR_CS, resolution="0.1"),
        MetricSpec("rppg.hr_avg", NUMERIC, "RPPG_HEART_RATE_AVG", "RPPG_HEART_RATE_AVG",
                   DIM_BEAT_PER_MIN, coding_system=VENDOR_CS, resolution="0.1"),
        MetricSpec("rppg.rr_avg", NUMERIC, "RPPG_RESP_RATE_AVG", "RPPG_RESP_RATE_AVG",
                   DIM_RESP_PER_MIN, coding_system=VENDOR_CS, resolution="0.1"),
        MetricSpec("rppg.pulse", WAVE, "RPPG_PULSE_WAVE", "RPPG_PULSE_WAVE", DIM_DIMLESS,
                   coding_system=VENDOR_CS, sample_rate_hz=RPPG_FS, resolution="0.0001"),
        MetricSpec("rppg.resp", WAVE, "RPPG_RESP_WAVE", "RPPG_RESP_WAVE", DIM_DIMLESS,
                   coding_system=VENDOR_CS, sample_rate_hz=RPPG_FS, resolution="0.0001"),
    )),
))

AI_ECG_VMD = VmdSpec("vmd.aiecg", "AIECG_VMD", "MMPM_AIECG_VMD", (
    ChannelSpec("ch.aiecg", "AIECG_CHAN", "MMPM_AIECG_CHAN", (
        MetricSpec("aiecg.signal", WAVE, "AIECG_SIGNAL", "AIECG_SIGNAL", DIM_MILLI_VOLT,
                   coding_system=VENDOR_CS, sample_rate_hz=AI_ECG_FS, resolution="0.0001"),
        MetricSpec("aiecg.rhythm", STRING, "AIECG_RHYTHM", "AIECG_RHYTHM", DIM_DIMLESS,
                   coding_system=VENDOR_CS),
        MetricSpec("aiecg.source", STRING, "AIECG_SOURCE", "AIECG_SOURCE", DIM_DIMLESS,
                   coding_system=VENDOR_CS),
        MetricSpec("aiecg.latency", NUMERIC, "AIECG_INFERENCE_MS", "AIECG_INFERENCE_MS",
                   DIM_MILLI_SEC, coding_system=VENDOR_CS, resolution="0.01"),
    )),
))

ALL_VMDS = (DEVICE_VMD, RPPG_VMD, AI_ECG_VMD)

_DESCRIPTOR_QNAME = {
    NUMERIC: pm_qnames.NumericMetricDescriptor,
    WAVE: pm_qnames.RealTimeSampleArrayMetricDescriptor,
    STRING: pm_qnames.StringMetricDescriptor,
}


def _coded(code: str, ref_id: str, coding_system: str | None = None) -> pm_types.CodedValue:
    return pm_types.CodedValue(code=code, coding_system=coding_system, symbolic_code_name=ref_id)


def build_mdib(vmds=ALL_VMDS) -> ProviderMdib:
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
                d.Unit = _coded(*m.unit)
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
