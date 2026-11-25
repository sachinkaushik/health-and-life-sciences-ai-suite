// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
import type { Metadata } from 'next'
import { Sidebar } from '@/components/sidebar'
import './globals.css'

export const metadata: Metadata = {
  title: { default: 'Medical Scribe', template: '%s · Medical Scribe' },
  description: 'Record a consultation and get a SOAP note, transcribed, diarized and written on this machine.',
  icons: { icon: '/logo.svg' },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex min-h-dvh">
        <Sidebar />
        <main className="min-w-0 flex-1 px-4 py-6 sm:px-8">{children}</main>
      </body>
    </html>
  )
}
