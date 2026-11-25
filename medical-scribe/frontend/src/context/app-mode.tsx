// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

'use client'

import { createContext, type ReactNode, useContext } from 'react'
import { type AppMode, BRANDING, type Branding } from '@/lib/branding'

const AppModeContext = createContext<AppMode>('studio')

/** `mode` is the one the server read from env `APP_MODE`. */
export function AppModeProvider({
  mode,
  children,
}: {
  mode: AppMode
  children: ReactNode
}) {
  return (
    <AppModeContext.Provider value={mode}>{children}</AppModeContext.Provider>
  )
}

export function useAppMode(): AppMode {
  return useContext(AppModeContext)
}

export function useBranding(): Branding {
  return BRANDING[useAppMode()]
}
