// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

'use client'

import type { ReactNode } from 'react'
import { useAppMode } from '@/context/app-mode'
import { ScribeHome } from './scribe-home'

/** The home page for the app mode; the mode is known only at run time, so it is picked here. */
export function HomeForMode({ studio }: { studio: ReactNode }) {
  return useAppMode() === 'medical-scribe' ? <ScribeHome /> : studio
}
