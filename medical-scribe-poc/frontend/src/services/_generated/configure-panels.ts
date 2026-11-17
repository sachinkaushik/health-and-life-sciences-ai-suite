// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

// THIS FILE IS AUTO-GENERATED. DO NOT EDIT MANUALLY.
// Source of truth: scripts/generate-registries.mjs
// Run "npm run codegen" to regenerate.

import type { ComponentType } from "react";
import type { Service } from "../types";

import { SttConfigurePanel } from "../speech-to-text/components/configure-panel";

export type ServiceConfigurePanelComponent = ComponentType<{
  service: Service;
}>;

/** Optional service-specific configure panel keyed by service ID. */
export const configurePanelRegistry: Partial<Record<string, ServiceConfigurePanelComponent>> = {
  "speech-to-text": SttConfigurePanel,
};
