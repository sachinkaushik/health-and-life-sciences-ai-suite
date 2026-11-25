// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

'use client'

import {
  ArrowRight,
  CalendarDays,
  ClipboardList,
  FileText,
  Mic,
  ShieldCheck,
  Stethoscope,
  UserRound,
} from 'lucide-react'
import Link from 'next/link'
import {
  shapedStatusDotClass,
  TONES,
  type Tone,
} from '@/components/common/tones'
import { MetricCard } from '@/components/dashboard/metric-card'
import { CONSULTATION_HREF } from '@/components/shell/app-pages'
import { PageHeading } from '@/components/shell/page-heading'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  useServiceApiBase,
  useServiceStatus,
} from '@/context/service-status-context'
import { STATE_LABEL } from '@/lib/instances/service-presentation'
import { cn } from '@/lib/utils'
import { useDoctorProfiles } from '@/samples/medical-scribe/hooks/use-doctor-profiles'
import { useSessions } from '@/samples/medical-scribe/hooks/use-sessions'
import { formatTimestamp } from '@/samples/medical-scribe/lib/timestamps'
import type { Session } from '@/samples/medical-scribe/lib/types'
import { getServiceLiveStatus } from '@/services/types'

const RECENT_COUNT = 6

/** The pipeline stages, in clinician terms, by the service that runs each. */
const PIPELINE = [
  { serviceId: 'speech-to-text', label: 'Transcription' },
  { serviceId: 'diarization', label: 'Speaker identification' },
  { serviceId: 'text-generation', label: 'Clinical note writer' },
  { serviceId: 'medical-scribe-database', label: 'Encounter store' },
] as const

function encounterHref(id: string): string {
  return `${CONSULTATION_HREF}?session=${encodeURIComponent(id)}`
}

function encounterState(session: Session): { label: string; tone: Tone } {
  if (session.status === 'recording')
    return { label: 'Recording', tone: 'warning' }
  if (session.status === 'processing')
    return { label: 'Processing', tone: 'info' }
  if (session.status === 'error')
    return { label: 'Failed', tone: 'destructive' }
  if (session.soapReport) return { label: 'Note ready', tone: 'success' }
  if (session.transcripts.length > 0)
    return { label: 'Needs note', tone: 'warning' }
  return { label: 'Not recorded', tone: 'muted' }
}

function isToday(iso: string): boolean {
  const date = new Date(iso)
  return (
    !Number.isNaN(date.getTime()) &&
    date.toDateString() === new Date().toDateString()
  )
}

/** The Medical Scribe home: start a consultation, pick up recent ones, see the AI is ready. */
export function ScribeHome() {
  const apiBase = useServiceApiBase('medical-scribe-database')
  const { sessions, isLoading } = useSessions(apiBase)
  const { profiles } = useDoctorProfiles(apiBase)
  const { serviceById, loading: servicesLoading } = useServiceStatus()

  const stages = PIPELINE.map((stage) => {
    const service = serviceById.get(stage.serviceId)
    return {
      ...stage,
      service,
      status: service ? getServiceLiveStatus(service) : 'offline',
    }
  })
  const notReady = stages.filter((s) => s.status !== 'online')
  const ready = !servicesLoading && notReady.length === 0
  const awaitingNote = sessions.filter(
    (s) => s.transcripts.length > 0 && !s.soapReport,
  )
  const enrolled = profiles.filter((p) => p.embedding?.length).length
  const loadingSessions = isLoading || !apiBase

  return (
    <div className="space-y-8">
      <PageHeading
        title="Today"
        description={new Date().toLocaleDateString(undefined, {
          weekday: 'long',
          day: 'numeric',
          month: 'long',
          year: 'numeric',
        })}
      />

      <section
        aria-labelledby="scribe-hero-title"
        className="studio-hero relative overflow-hidden rounded-2xl px-6 py-8 text-white sm:px-8 sm:py-9"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 overflow-hidden"
        >
          <div className="hero-orbit opacity-50 sm:opacity-100" />
          <div className="hero-chip absolute top-14 right-20 hidden size-28 items-center justify-center rounded-3xl border border-white/25 bg-white/10 lg:flex">
            <Stethoscope className="size-14 text-white/90" strokeWidth={1} />
          </div>
        </div>
        <div className="relative max-w-xl lg:max-w-[65%]">
          <h2
            id="scribe-hero-title"
            className="text-2xl leading-tight font-semibold tracking-tight sm:text-3xl"
          >
            Medical Scribe
          </h2>
          <p className="mt-3 max-w-md text-sm leading-6 text-white/85">
            Record or upload a consultation. It is transcribed, the speakers are
            told apart and a SOAP note is drafted, all on this machine.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/10 px-3 py-1">
              <ShieldCheck aria-hidden="true" className="size-3.5" />
              On-device · no cloud
            </span>
            <span
              role="status"
              className="inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/10 px-3 py-1"
            >
              <span
                aria-hidden="true"
                className={cn(
                  'size-2 rounded-full',
                  servicesLoading
                    ? 'bg-white/50'
                    : ready
                      ? 'bg-emerald-300'
                      : 'bg-amber-300',
                )}
              />
              {servicesLoading
                ? 'Checking AI services…'
                : ready
                  ? 'AI ready'
                  : `${notReady.length} of ${PIPELINE.length} AI services not ready`}
            </span>
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button
              asChild
              className="text-intel-blue h-10 border-white bg-white px-4 shadow-sm hover:bg-white/90"
            >
              <Link href={CONSULTATION_HREF}>
                <Mic />
                Start consultation
              </Link>
            </Button>
            {sessions[0] && (
              <Button
                asChild
                variant="outline"
                className="h-10 border-white/30 bg-white/5 px-4 text-white hover:bg-white/15 hover:text-white"
              >
                <Link href={encounterHref(sessions[0].id)}>
                  Open last encounter
                  <ArrowRight />
                </Link>
              </Button>
            )}
          </div>
        </div>
      </section>

      <section aria-label="Encounter overview" aria-busy={loadingSessions}>
        <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
          <MetricCard
            label="Encounters today"
            value={
              loadingSessions
                ? '—'
                : String(
                    sessions.filter((s) => isToday(s.sessionCreatedAt)).length,
                  )
            }
            icon={CalendarDays}
            tone="primary"
            index={0}
          />
          <MetricCard
            label="Awaiting a note"
            value={loadingSessions ? '—' : String(awaitingNote.length)}
            icon={ClipboardList}
            tone="warning"
            index={1}
            href={
              awaitingNote[0] ? encounterHref(awaitingNote[0].id) : undefined
            }
          />
          <MetricCard
            label="All encounters"
            value={loadingSessions ? '—' : String(sessions.length)}
            icon={FileText}
            index={2}
            href={CONSULTATION_HREF}
          />
          <MetricCard
            label="Doctor voices enrolled"
            value={loadingSessions ? '—' : String(enrolled)}
            icon={UserRound}
            tone="info"
            index={3}
          />
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-5">
        <section
          aria-labelledby="recent-encounters-title"
          className="glass-card rounded-2xl p-4 sm:p-5 lg:col-span-3"
        >
          <div className="flex items-center justify-between gap-3">
            <h2
              id="recent-encounters-title"
              className="text-foreground text-base font-semibold"
            >
              Recent encounters
            </h2>
            <Link
              href={CONSULTATION_HREF}
              className="text-primary text-sm font-medium hover:underline"
            >
              All encounters
            </Link>
          </div>
          {loadingSessions ? (
            <div role="status" className="mt-3 space-y-2">
              <span className="sr-only">Loading encounters…</span>
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : sessions.length === 0 ? (
            <p className="text-muted-foreground mt-4 text-sm">
              No encounters yet. Start a consultation to record the first one.
            </p>
          ) : (
            <ul className="-mx-2 mt-2">
              {sessions.slice(0, RECENT_COUNT).map((session) => {
                const state = encounterState(session)
                return (
                  <li key={session.id}>
                    <Link
                      href={encounterHref(session.id)}
                      className="group hover:bg-accent/60 focus-visible:ring-ring/50 flex items-center gap-3 rounded-xl px-2 py-2 outline-none focus-visible:ring-[3px]"
                    >
                      <span
                        className={cn(
                          'flex size-9 shrink-0 items-center justify-center rounded-lg',
                          TONES.primary.iconBg,
                        )}
                      >
                        <Stethoscope aria-hidden="true" className="size-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="text-foreground block truncate text-sm font-medium">
                          {session.name}
                        </span>
                        <span className="text-muted-foreground block truncate text-xs">
                          {[
                            formatTimestamp(session.sessionCreatedAt),
                            session.doctorProfileName,
                            session.language.toUpperCase(),
                          ]
                            .filter(Boolean)
                            .join(' · ')}
                        </span>
                      </span>
                      <span
                        className={cn(
                          'shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium',
                          TONES[state.tone].pill,
                        )}
                      >
                        {state.label}
                      </span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}
        </section>

        <section
          aria-labelledby="pipeline-title"
          className="glass-card rounded-2xl p-4 sm:p-5 lg:col-span-2"
        >
          <h2
            id="pipeline-title"
            className="text-foreground text-base font-semibold"
          >
            AI pipeline
          </h2>
          <ul className="-mx-2 mt-2">
            {stages.map((stage) => (
              <li key={stage.serviceId}>
                <div className="flex items-center gap-3 rounded-xl px-2 py-2">
                  <span
                    aria-hidden="true"
                    className={cn(
                      'size-2.5 shrink-0',
                      shapedStatusDotClass(stage.status),
                    )}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="text-foreground block text-sm font-medium">
                      {stage.label}
                    </span>
                    <span className="text-muted-foreground block truncate text-xs">
                      {[
                        stage.service?.currentModel,
                        stage.service?.currentDevice,
                      ]
                        .filter(Boolean)
                        .join(' · ') || stage.service?.name}
                    </span>
                  </span>
                  <span className="text-muted-foreground shrink-0 text-xs">
                    {servicesLoading ? '…' : STATE_LABEL[stage.status]}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  )
}
