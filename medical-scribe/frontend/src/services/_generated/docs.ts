// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

// THIS FILE IS AUTO-GENERATED. DO NOT EDIT MANUALLY.
// Source of truth: scripts/generate-registries.mjs
// Run "npm run codegen" to regenerate.

import type { DocsFactoryOptions, ServiceDocsData } from "../types";

export type DocsFactory = (opts: DocsFactoryOptions) => ServiceDocsData;

import { getDocsData as diarizationDocs } from "../diarization/docs";
import { getDocsData as speechToTextDocs } from "../speech-to-text/docs";
import { getDocsData as textGenerationDocs } from "../text-generation/docs";

/** Registry of docs factory functions keyed by service ID. */
export const docsRegistry: Record<string, DocsFactory> = {
  diarization: diarizationDocs,
  "speech-to-text": speechToTextDocs,
  "text-generation": textGenerationDocs,
};
