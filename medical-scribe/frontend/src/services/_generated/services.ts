// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

// THIS FILE IS AUTO-GENERATED. DO NOT EDIT MANUALLY.
// Source of truth: scripts/generate-registries.mjs
// Run "npm run codegen" to regenerate.

import type { Service as ServiceType } from "@/payload-types";

// Data imports
import { service as diarizationMeta } from "../diarization/data";
import { service as medicalScribeDatabaseMeta } from "../medical-scribe-database/data";
import { service as speechToTextMeta } from "../speech-to-text/data";
import { service as textGenerationMeta } from "../text-generation/data";

// Demo imports
import { DiarizationDemo } from "../diarization/demo";
import { SpeechToTextDemo } from "../speech-to-text/demo";
import { TextGenerationDemo } from "../text-generation/demo";

import type { Service } from "../types";

/** Full service map including React demo components. */
export const serviceMap: Record<string, Service> = {
  diarization: {
    ...diarizationMeta,
    status: "offline",
    demo: DiarizationDemo,
  },
  "medical-scribe-database": {
    ...medicalScribeDatabaseMeta,
    status: "offline",
  },
  "speech-to-text": {
    ...speechToTextMeta,
    status: "offline",
    demo: SpeechToTextDemo,
  },
  "text-generation": {
    ...textGenerationMeta,
    status: "offline",
    demo: TextGenerationDemo,
  },
};
