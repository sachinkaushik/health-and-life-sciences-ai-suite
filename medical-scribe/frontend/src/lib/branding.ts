// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

/**
 * What the app presents itself as, from env `APP_MODE` (read at run time, so one image serves
 * both): `studio` is the Edge AI Demo Studio shell; `medical-scribe` is the clinician-facing app.
 */
export const APP_MODES = ['studio', 'medical-scribe'] as const
export type AppMode = (typeof APP_MODES)[number]

export interface Branding {
  name: string
  description: string
}

export const BRANDING: Record<AppMode, Branding> = {
  studio: {
    name: 'Edge AI Demo Studio',
    description:
      'Explore and manage Intel AI microservices and interactive samples powered by OpenVINO and Intel hardware.',
  },
  'medical-scribe': {
    name: 'Medical Scribe',
    description:
      'Record a consultation and get a SOAP note, transcribed, diarized and written on this machine.',
  },
}

export function parseAppMode(raw: string | undefined): AppMode {
  const value = raw?.trim()
  return APP_MODES.find((mode) => mode === value) ?? 'studio'
}
