// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
'use client'

import { House, ShieldCheck, Stethoscope } from 'lucide-react'
import Image from 'next/image'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { api } from '@/lib/api'
import { usePolling } from '@/lib/use-polling'

const PAGES = [
  { href: '/', label: 'Today', icon: House },
  { href: '/consultations', label: 'Consultations', icon: Stethoscope },
]

export function TopBar() {
  const pathname = usePathname()
  const status = usePolling(api.status, 5000)
  const notReady = status.data?.services.filter((s) => !s.ready) ?? []

  return (
    <header className="sticky top-0 z-40 flex h-14 shrink-0 items-center gap-6 bg-gradient-to-r from-[#00285a] to-[#0068b5] px-5 text-white shadow-sm">
      <Link href="/" className="flex items-center gap-3">
        <Image src="/logo-classicblue-white.svg" alt="Intel" width={56} height={23} priority />
        <span className="border-l border-white/30 pl-3 text-sm font-semibold whitespace-nowrap">Medical Scribe</span>
      </Link>

      <nav className="flex h-full items-stretch gap-1" aria-label="Main">
        {PAGES.map(({ href, label, icon: Icon }) => {
          const active = href === '/' ? pathname === '/' : pathname.startsWith(href)
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? 'page' : undefined}
              className={`flex items-center gap-2 border-b-2 px-3 text-sm font-medium ${
                active ? 'border-white text-white' : 'border-transparent text-white/70 hover:text-white'
              }`}
            >
              <Icon className="size-4" aria-hidden />
              {label}
            </Link>
          )
        })}
      </nav>

      <div className="ml-auto flex items-center gap-2 text-xs">
        <span className="hidden items-center gap-1.5 rounded-full border border-white/25 bg-white/10 px-3 py-1 sm:inline-flex">
          <ShieldCheck className="size-3.5" aria-hidden /> On-device AI
        </span>
        <span
          role="status"
          title={notReady.length ? `Waiting for: ${notReady.map((s) => s.label).join(', ')}` : undefined}
          className="inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/10 px-3 py-1"
        >
          <span
            className={`size-2 rounded-full ${!status.data ? 'bg-white/50' : status.data.ready ? 'bg-emerald-300' : 'bg-amber-300'}`}
            aria-hidden
          />
          {!status.data ? 'Checking…' : status.data.ready ? 'AI ready' : `${notReady.length} service${notReady.length > 1 ? 's' : ''} starting`}
        </span>
      </div>
    </header>
  )
}
