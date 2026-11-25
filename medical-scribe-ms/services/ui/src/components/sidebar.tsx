// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
'use client'

import { Activity, House, Stethoscope } from 'lucide-react'
import Image from 'next/image'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const SECTIONS = [
  {
    label: 'Scribe',
    pages: [
      { href: '/', label: 'Today', icon: House },
      { href: '/consultations', label: 'Consultations', icon: Stethoscope },
    ],
  },
  { label: 'Monitor', pages: [{ href: '/system', label: 'System', icon: Activity }] },
]

export function Sidebar() {
  const pathname = usePathname()
  return (
    <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col bg-gradient-to-b from-[#00285a] to-[#003d7a] text-white md:flex">
      <div className="flex h-16 items-center gap-3 border-b border-white/10 px-5">
        <Image src="/logo-classicblue-white.svg" alt="Intel" width={64} height={26} priority />
        <span className="text-sm font-semibold">Medical Scribe</span>
      </div>
      <nav className="flex-1 space-y-6 px-3 pt-5">
        {SECTIONS.map((section) => (
          <div key={section.label}>
            <p className="mb-2 px-2 text-xs font-semibold tracking-wider text-white/50 uppercase">{section.label}</p>
            {section.pages.map(({ href, label, icon: Icon }) => {
              const active = href === '/' ? pathname === '/' : pathname.startsWith(href)
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={active ? 'page' : undefined}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${
                    active ? 'bg-white/15 text-white' : 'text-white/70 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  <Icon className="size-4" aria-hidden />
                  {label}
                </Link>
              )
            })}
          </div>
        ))}
      </nav>
      <p className="px-5 py-4 text-xs text-white/50">On-device AI · Intel® Core™ Ultra</p>
    </aside>
  )
}
