// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

import type { Metadata } from 'next'
import { connection } from 'next/server'
import './globals.css'
import { DashboardShell } from '@/components/shell/dashboard-shell'
import { Toaster } from '@/components/ui/sonner'
import { AppModeProvider } from '@/context/app-mode'
import { Providers } from '@/context/providers'
import { type AppMode, BRANDING, parseAppMode } from '@/lib/branding'
import {
  APP_SETTINGS_DEFAULTS,
  isTheme,
  type Theme,
} from '@/lib/settings/app-settings'
import { readAppSettingsSafe } from '@/lib/settings/app-settings-store'

/** Read per request, not at build: one image serves every mode. */
async function readAppMode(): Promise<AppMode> {
  await connection()
  return parseAppMode(process.env.APP_MODE)
}

export async function generateMetadata(): Promise<Metadata> {
  const { name, description } = BRANDING[await readAppMode()]
  return {
    title: { default: name, template: `%s · ${name}` },
    icons: {
      icon: '/logo.svg',
    },
    description,
  }
}

/**
 * Sets the theme class on `<html>` before first paint, resolving `system` from the OS. It reads
 * `data-theme-preference` so nothing is interpolated into this unescaped script text.
 */
const THEME_INIT_SCRIPT = `(function(){try{var d=document.documentElement,t=d.getAttribute('data-theme-preference');if(t!=='light'&&t!=='dark'){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}d.classList.remove('light','dark');d.classList.add(t)}catch(e){}})()`

/** The saved theme, read per request: it lives in the database, not the build. */
async function readSavedTheme(): Promise<Theme> {
  await connection()
  const { theme } = await readAppSettingsSafe()
  return isTheme(theme) ? theme : APP_SETTINGS_DEFAULTS.theme
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const theme = await readSavedTheme()
  const appMode = await readAppMode()
  return (
    // The class is the saved theme when it is explicit; for `system` the
    // inline script picks it, hence suppressHydrationWarning.
    <html
      lang="en"
      className={theme === 'system' ? undefined : theme}
      data-theme-preference={theme}
      suppressHydrationWarning
    >
      <head>
        <script>{THEME_INIT_SCRIPT}</script>
      </head>
      <body className="font-sans antialiased">
        <Providers initialTheme={theme}>
          <AppModeProvider mode={appMode}>
            <DashboardShell>{children}</DashboardShell>
          </AppModeProvider>
          <Toaster richColors closeButton />
        </Providers>
      </body>
    </html>
  )
}
