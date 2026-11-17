// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

// THIS FILE IS AUTO-GENERATED. DO NOT EDIT MANUALLY.
// Source of truth: scripts/generate-registries.mjs
// Run "npm run codegen" to regenerate.

import type { ComponentType } from "react";

import { SttFeatureProvider } from "../speech-to-text/feature-provider";

/** Props every optional-service feature provider component accepts. */
export interface FeatureProviderProps {
  /** Called by speech-driven providers (STT) with recognized text. */
  onTranscription?: (text: string) => void;
  /** Host sample id (e.g. for service-specific config links). */
  sampleId?: string;
}

export type FeatureProviderComponent = ComponentType<FeatureProviderProps>;

/** Optional-service feature provider keyed by service ID. Looked up by
 *  `useSampleChatFeatures`; a pruned service folder drops out automatically. */
export const featureProviderRegistry: Partial<Record<string, FeatureProviderComponent>> = {
  "speech-to-text": SttFeatureProvider,
};
