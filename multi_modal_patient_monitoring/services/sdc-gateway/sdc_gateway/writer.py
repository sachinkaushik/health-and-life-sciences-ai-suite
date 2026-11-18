# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Write helpers around ProviderMdib transactions."""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Iterable, Mapping

from sdc11073.mdib import ProviderMdib


def _dec(value: float, places: int | None) -> Decimal:
    return Decimal(str(value)) if places is None else Decimal(f"{value:.{places}f}")


class MdibWriter:
    def __init__(self, mdib: ProviderMdib):
        self._mdib = mdib

    def set_metrics(self, values: Mapping[str, float | str], determination_time: float | None = None,
                    places: int | None = 2) -> None:
        """Update numeric/string metrics in one episodic report (places=None keeps each value's own precision)."""
        t = determination_time if determination_time is not None else time.time()
        with self._mdib.metric_state_transaction(set_determination_time=False) as tr:
            for handle, value in values.items():
                state = tr.get_state(handle)
                state.MetricValue.Value = value if isinstance(value, str) else _dec(value, places)
                state.MetricValue.DeterminationTime = t

    def push_samples(self, chunks: Mapping[str, Iterable[float]], determination_time: float | None = None,
                     places: int = 3) -> None:
        """Publish waveform chunks in one waveform report."""
        t = determination_time if determination_time is not None else time.time()
        with self._mdib.rt_sample_state_transaction(set_determination_time=False) as tr:
            for handle, samples in chunks.items():
                state = tr.get_state(handle)
                state.MetricValue.Samples = [_dec(v, places) for v in samples]
                state.MetricValue.DeterminationTime = t
