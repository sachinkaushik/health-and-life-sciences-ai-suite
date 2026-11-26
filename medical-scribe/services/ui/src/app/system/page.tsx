// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
'use client'

import { Activity, Cpu, Gauge, MemoryStick, Zap } from 'lucide-react'
import { api, formatClock, formatTime } from '@/lib/api'
import { usePolling } from '@/lib/use-polling'

type Point = [string, ...number[]]

interface CollectorMetrics {
  cpu_utilization?: Point[]
  gpu_utilization?: Point[]
  npu_utilization?: Point[]
  memory?: Point[]
  power?: Point[]
}

const HISTORY = 90

function Sparkline({ values, max }: { values: number[]; max: number }) {
  if (values.length < 2) return <div className="h-12" />
  const top = Math.max(max, ...values, 1)
  const points = values.map((v, i) => `${(i / (values.length - 1)) * 100},${40 - (v / top) * 38}`).join(' ')
  return (
    <svg viewBox="0 0 100 40" preserveAspectRatio="none" className="h-12 w-full" aria-hidden>
      <polyline points={points} fill="none" stroke="#0068b5" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

function HardwareCard({
  label,
  icon: Icon,
  series,
  unit,
  max,
  detail,
}: {
  label: string
  icon: typeof Cpu
  series: number[]
  unit: string
  max: number
  detail?: string
}) {
  const latest = series.at(-1)
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between text-sm font-medium text-slate-600">
        {label}
        <Icon className="size-4 text-[#0068b5]" aria-hidden />
      </div>
      <p className="mt-2 text-3xl font-semibold tabular-nums">
        {latest === undefined ? '—' : latest.toFixed(1)}
        <span className="ml-1 text-base font-normal text-slate-500">{unit}</span>
      </p>
      {detail && <p className="text-xs text-slate-500">{detail}</p>}
      <Sparkline values={series} max={max} />
    </div>
  )
}

const value = (points: Point[] | undefined, index = 1) => (points ?? []).slice(-HISTORY).map((p) => Number(p[index] ?? 0))

export default function SystemPage() {
  const metrics = usePolling(api.metrics, 3000)
  const encounters = usePolling(api.encounters, 15000)
  const m = (metrics.data?.metrics ?? {}) as CollectorMetrics
  const platform = (metrics.data?.platform ?? {}) as Record<string, string>
  const memory = m.memory?.at(-1)
  const timed = (encounters.data ?? []).filter((e) => e.timings.stt_seconds || e.timings.note_seconds)

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <p className="text-xs font-semibold tracking-[0.18em] text-[#0068b5] uppercase">Edge AI performance</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">System</h1>
        <p className="mt-1 text-sm text-slate-500">
          Hardware use from the performance-tools metrics collector, and how long each AI stage took per encounter.
        </p>
      </header>

      {metrics.data && !metrics.data.available && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          The metrics collector is not reachable. Check it with <code>make status</code> (service metrics-collector).
        </p>
      )}

      {Object.keys(platform).length > 0 && (
        <section className="card flex flex-wrap gap-x-8 gap-y-2 px-5 py-4 text-sm" aria-label="Platform">
          {Object.entries(platform).map(([k, v]) => (
            <span key={k}>
              <span className="text-slate-500">{k}: </span>
              <span className="font-medium">{v}</span>
            </span>
          ))}
        </section>
      )}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5" aria-label="Hardware">
        <HardwareCard label="CPU" icon={Cpu} series={value(m.cpu_utilization)} unit="%" max={100} />
        <HardwareCard label="GPU" icon={Gauge} series={value(m.gpu_utilization)} unit="%" max={100} />
        <HardwareCard label="NPU" icon={Activity} series={value(m.npu_utilization)} unit="%" max={100} />
        <HardwareCard
          label="Memory"
          icon={MemoryStick}
          series={value(m.memory, 4)}
          unit="%"
          max={100}
          detail={memory ? `${Number(memory[2]).toFixed(1)} of ${Number(memory[1]).toFixed(0)} GB` : undefined}
        />
        <HardwareCard label="Package power" icon={Zap} series={value(m.power)} unit="W" max={10} />
      </section>

      <section className="card overflow-x-auto p-5" aria-labelledby="timings-title">
        <h2 id="timings-title" className="font-semibold">
          AI pipeline per encounter
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          RTF = processing time ÷ audio length (below 1 is faster than real time). Time to first words and tokens/s are for the
          SOAP note.
        </p>
        <table className="mt-3 w-full text-left text-sm">
          <thead className="text-xs text-slate-500">
            <tr>
              <th className="py-2 pr-4 font-medium">Encounter</th>
              <th className="py-2 pr-4 font-medium">Audio</th>
              <th className="py-2 pr-4 font-medium">Speech to text + speakers</th>
              <th className="py-2 pr-4 font-medium">Note: first words</th>
              <th className="py-2 pr-4 font-medium">Note: tokens/s</th>
              <th className="py-2 font-medium">Note total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 tabular-nums">
            {timed.map((e) => {
              const t = e.timings
              return (
                <tr key={e.id}>
                  <td className="py-2 pr-4">
                    <span className="font-medium">{e.name}</span>
                    <span className="block text-xs text-slate-500">{formatTime(e.created_at)}</span>
                  </td>
                  <td className="py-2 pr-4">{t.audio_seconds ? formatClock(t.audio_seconds) : '—'}</td>
                  <td className="py-2 pr-4">{t.stt_seconds ? `${t.stt_seconds}s · RTF ${t.stt_rtf ?? '—'}` : '—'}</td>
                  <td className="py-2 pr-4">{t.note_ttft_seconds ? `${t.note_ttft_seconds}s` : '—'}</td>
                  <td className="py-2 pr-4">{t.note_tokens_per_second ?? '—'}</td>
                  <td className="py-2">{t.note_seconds ? `${t.note_seconds}s` : '—'}</td>
                </tr>
              )
            })}
            {timed.length === 0 && (
              <tr>
                <td colSpan={7} className="py-4 text-slate-500">
                  No processed encounters yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  )
}
