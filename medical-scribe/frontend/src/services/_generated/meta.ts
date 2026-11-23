// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

// THIS FILE IS AUTO-GENERATED. DO NOT EDIT MANUALLY.
// Source of truth: scripts/generate-registries.mjs
// Run "npm run codegen" to regenerate.

import { service as diarizationMeta } from "../diarization/data";
import { service as medicalScribeDatabaseMeta } from "../medical-scribe-database/data";
import { service as speechToTextMeta } from "../speech-to-text/data";
import { service as textGenerationMeta } from "../text-generation/data";

/** Metadata-only map — safe to import in non-React/config contexts. */
import type { ServiceMeta } from "../types";

export const metaMap: Record<string, ServiceMeta> = {
  diarization: diarizationMeta,
  "medical-scribe-database": medicalScribeDatabaseMeta,
  "speech-to-text": speechToTextMeta,
  "text-generation": textGenerationMeta,
};
