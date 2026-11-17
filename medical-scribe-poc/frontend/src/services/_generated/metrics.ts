// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

// THIS FILE IS AUTO-GENERATED. DO NOT EDIT MANUALLY.
// Source of truth: scripts/generate-registries.mjs
// Run "npm run codegen" to regenerate.

import type { MetricFigure } from "../common/metrics/types";

import { figures as diarizationFigures } from "../diarization/metrics";
import { figures as speechToTextFigures } from "../speech-to-text/metrics";
import { figures as textGenerationFigures } from "../text-generation/metrics";

/** Figures of each service's Live metrics panel (`metrics.tsx`), keyed by service ID. */
export const metricsRegistry: Partial<Record<string, MetricFigure[]>> = {
  diarization: diarizationFigures,
  "speech-to-text": speechToTextFigures,
  "text-generation": textGenerationFigures,
};
