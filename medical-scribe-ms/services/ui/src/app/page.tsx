// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
'use client'

import { ArrowRight, CalendarDays, ClipboardList, FileText, Mic, ShieldCheck, Stethoscope, UserRound } from 'lucide-react'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api, type AppConfig, encounterState, formatTime, TONE_PILL } from '@/lib/api'
import { usePolling } from '@/lib/use-polling'

function isToday(iso: string) {
  return new Date(iso).toDateString() === new Date().toDateString()
}

function Metric({ label, value, icon: Icon }: { label: string; value: string; icon: typeof Mic }) {
  return (
    <div className="card px-5 py-4">
      <div className="flex items-center justify-between text-xs font-medium text-slate-500">
        {label}
        <Icon className="size-4 text-[#0068b5]" aria-hidden />
      </div>
      <p className="mt-2 text-3xl font-semibold tabular-nums">{value}</p>
    </div>
  )
}

export default function TodayPage() {
  const encounters = usePolling(api.encounters, 5000)
  const doctors = usePolling(api.doctors, 30000)
  const status = usePolling(api.status, 5000)
  const [config, setConfig] = useState<AppConfig | null>(null)
  useEffect(() => {
    api.config().then(setConfig).catch(() => {})
  }, [])

  const list = encounters.data ?? []
  const awaiting = list.filter((e) => e.transcript.length > 0 && !e.note)
  const loading = encounters.data === undefined
  const notReady = status.data?.services.filter((s) => !s.ready) ?? []
  const modelOf: Record<string, string | undefined> = config
    ? {
        'speech-to-text': `${config.stt.model} · ${config.stt.device}, speakers on ${config.diarization.device}`,
        'text-generation': `${config.text_generation.model} · ${config.text_generation.device}`,
      }
    : {}

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Today</h1>
        <p className="mt-1 text-sm text-slate-500">
          {new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
        </p>
      </header>

      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#00285a] via-[#0068b5] to-[#00a3e0] px-8 py-8 text-white">
        <Stethoscope className="absolute top-8 right-10 hidden size-24 text-white/20 lg:block" strokeWidth={1} aria-hidden />
        <h2 className="text-2xl font-semibold">Medical Scribe</h2>
        <p className="mt-2 max-w-lg text-sm text-white/85">
          Record or upload a consultation. It is transcribed, the speakers are told apart and a SOAP note is
          drafted, all on this machine.
        </p>
        <div className="mt-4 flex flex-wrap gap-2 text-xs">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/10 px-3 py-1">
            <ShieldCheck className="size-3.5" aria-hidden /> On-device · no cloud
          </span>
          <span role="status" className="inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/10 px-3 py-1">
            <span
              className={`size-2 rounded-full ${!status.data ? 'bg-white/50' : status.data.ready ? 'bg-emerald-300' : 'bg-amber-300'}`}
              aria-hidden
            />
            {!status.data
              ? 'Checking AI services…'
              : status.data.ready
                ? 'AI ready'
                : `${notReady.length} of ${status.data.services.length} AI services not ready`}
          </span>
        </div>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/consultations?new=1" className="btn bg-white text-[#0068b5] hover:bg-white/90">
            <Mic className="size-4" aria-hidden /> Start consultation
          </Link>
          {list[0] && (
            <Link href={`/consultations?id=${list[0].id}`} className="btn border border-white/30 bg-white/5 text-white hover:bg-white/15">
              Open last encounter <ArrowRight className="size-4" aria-hidden />
            </Link>
          )}
        </div>
      </section>

      <section className="grid grid-cols-2 gap-4 xl:grid-cols-4" aria-label="Overview">
        <Metric label="Encounters today" value={loading ? '—' : String(list.filter((e) => isToday(e.created_at)).length)} icon={CalendarDays} />
        <Metric label="Awaiting a note" value={loading ? '—' : String(awaiting.length)} icon={ClipboardList} />
        <Metric label="All encounters" value={loading ? '—' : String(list.length)} icon={FileText} />
        <Metric
          label="Doctor voices enrolled"
          value={doctors.data ? String(doctors.data.filter((d) => d.enrolled).length) : '—'}
          icon={UserRound}
        />
      </section>

      <div className="grid gap-4 lg:grid-cols-5">
        <section className="card p-5 lg:col-span-3" aria-labelledby="recent-title">
          <div className="flex items-center justify-between">
            <h2 id="recent-title" className="font-semibold">
              Recent encounters
            </h2>
            <Link href="/consultations" className="text-sm font-medium text-[#0068b5] hover:underline">
              All encounters
            </Link>
          </div>
          {encounters.error && <p className="mt-3 text-sm text-red-600">{encounters.error}</p>}
          {!loading && list.length === 0 && (
            <p className="mt-4 text-sm text-slate-500">No encounters yet. Start a consultation to record the first one.</p>
          )}
          <ul className="-mx-2 mt-2">
            {list.slice(0, 6).map((e) => {
              const state = encounterState(e)
              return (
                <li key={e.id}>
                  <Link href={`/consultations?id=${e.id}`} className="flex items-center gap-3 rounded-xl px-2 py-2 hover:bg-slate-50">
                    <span className="flex size-9 items-center justify-center rounded-lg bg-sky-50 text-[#0068b5]">
                      <Stethoscope className="size-4" aria-hidden />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium">{e.name}</span>
                      <span className="block truncate text-xs text-slate-500">
                        {[formatTime(e.created_at), e.doctor_name, e.language.toUpperCase()].filter(Boolean).join(' · ')}
                      </span>
                    </span>
                    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${TONE_PILL[state.tone]}`}>{state.label}</span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </section>

        <section className="card p-5 lg:col-span-2" aria-labelledby="pipeline-title">
          <h2 id="pipeline-title" className="font-semibold">
            AI pipeline
          </h2>
          <ul className="mt-3 space-y-3">
            {(status.data?.services ?? []).map((s) => (
              <li key={s.id} className="flex items-center gap-3">
                <span className={`size-2.5 rounded-full ${s.ready ? 'bg-emerald-500' : 'bg-amber-400'}`} aria-hidden />
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium">{s.label}</span>
                  {modelOf[s.id] && <span className="block truncate text-xs text-slate-500">{modelOf[s.id]}</span>}
                </span>
                <span className="text-xs text-slate-500">{s.ready ? 'Ready' : 'Starting'}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  )
}
