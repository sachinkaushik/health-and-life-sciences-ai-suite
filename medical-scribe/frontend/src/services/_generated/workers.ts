// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

// THIS FILE IS AUTO-GENERATED. DO NOT EDIT MANUALLY.
// Source of truth: scripts/generate-registries.mjs
// Run "npm run codegen" to regenerate.

import type { Service } from "@/payload-types";
import type { WorkerConfig } from "../types";

import { worker as diarizationWorker } from "../diarization/data";
import { worker as medicalScribeDatabaseWorker } from "../medical-scribe-database/data";
import { worker as speechToTextWorker } from "../speech-to-text/data";

/** Worker configuration registry keyed by Payload service type. */
const workerRegistry: Partial<Record<Service["type"], WorkerConfig>> = {
  diarization: diarizationWorker,
  "medical-scribe-database": medicalScribeDatabaseWorker,
  "speech-to-text": speechToTextWorker,
};

export function getWorkerConfig(
  type: Service["type"],
): WorkerConfig | undefined {
  return workerRegistry[type];
}
