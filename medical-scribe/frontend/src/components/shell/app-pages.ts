// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

import {
  Activity,
  GalleryHorizontalEnd,
  House,
  LayoutDashboard,
  type LucideIcon,
  Server,
  Settings,
  Stethoscope,
} from 'lucide-react'
import type { AppMode } from '@/lib/branding'

/** A top-level page of the studio. */
export interface AppPage {
  href: string
  /** Short name, for the sidebar. */
  label: string
  /** Full name, for the breadcrumb and the command palette. */
  title: string
  icon: LucideIcon
}

/** A labelled group of sidebar entries. */
export interface NavSection {
  label: string
  pages: readonly AppPage[]
}

/** The top-level pages, in sidebar order. */
export const APP_PAGES: readonly AppPage[] = [
  { href: '/', label: 'Dashboard', title: 'Dashboard', icon: LayoutDashboard },
  { href: '/services', label: 'Services', title: 'Services', icon: Server },
  {
    href: '/samples',
    label: 'Samples',
    title: 'Samples',
    icon: GalleryHorizontalEnd,
  },
  {
    href: '/system-monitoring',
    label: 'System',
    title: 'System monitoring',
    icon: Activity,
  },
  { href: '/settings', label: 'Settings', title: 'Settings', icon: Settings },
]

export const CONSULTATION_HREF = '/samples/medical-scribe/demo'

const NAV_SECTIONS: Record<AppMode, readonly NavSection[]> = {
  studio: [{ label: 'Workspace', pages: APP_PAGES }],
  // The containers run the services (`make up`): no gallery, service controls or settings here.
  'medical-scribe': [
    {
      label: 'Scribe',
      pages: [
        { href: '/', label: 'Today', title: 'Today', icon: House },
        {
          href: CONSULTATION_HREF,
          label: 'Consultations',
          title: 'Consultations',
          icon: Stethoscope,
        },
      ],
    },
    { label: 'Monitor', pages: [APP_PAGES[3]] },
  ],
}

export function navSectionsFor(mode: AppMode): readonly NavSection[] {
  return NAV_SECTIONS[mode]
}

export function appPagesFor(mode: AppMode): readonly AppPage[] {
  return NAV_SECTIONS[mode].flatMap((section) => section.pages)
}

/** The page a path belongs to, by longest matching href (`/services/x` → Services). */
export function appPageFor(
  pathname: string,
  pages: readonly AppPage[] = APP_PAGES,
): AppPage {
  let best: AppPage | undefined
  for (const page of pages) {
    const matches =
      page.href === '/'
        ? pathname === '/'
        : pathname === page.href || pathname.startsWith(`${page.href}/`)
    if (matches && (!best || page.href.length > best.href.length)) best = page
  }
  return best ?? pages[0]
}
