// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
import type { Metadata } from 'next'
import { PerformancePanel } from '@/components/performance-panel'
import { TopBar } from '@/components/top-bar'
import './globals.css'

export const metadata: Metadata = {
  title: { default: 'Medical Scribe', template: '%s · Medical Scribe' },
  description: 'Record a consultation and get a SOAP note, transcribed, diarized and written on this machine.',
  icons: { icon: '/logo.svg' },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-dvh flex-col">
        <TopBar />
        <div className="flex min-h-0 flex-1">
          <main className="min-w-0 flex-1 px-4 py-6 sm:px-8">{children}</main>
          <PerformancePanel />
        </div>
      </body>
    </html>
  )
}
