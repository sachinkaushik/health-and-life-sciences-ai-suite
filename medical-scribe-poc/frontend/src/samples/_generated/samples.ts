// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

// THIS FILE IS AUTO-GENERATED. DO NOT EDIT MANUALLY.
// Source of truth: scripts/generate-registries.mjs
// Run "npm run codegen" to regenerate.

import type { Sample } from "../types";

import { sample as medicalScribe } from "../medical-scribe/data";

/** Auto-discovered sample map. */
export const sampleMap: Record<string, Sample> = {
  "medical-scribe": medicalScribe,
};
