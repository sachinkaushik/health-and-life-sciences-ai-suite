// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
'use client'

import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js'
import { ChevronDown, ChevronLeft, ChevronRight, Maximize2, Minimize2 } from 'lucide-react'
import Link from 'next/link'
import { type PointerEvent as ReactPointerEvent, type ReactNode, useEffect, useState } from 'react'
import { Line } from 'react-chartjs-2'
import { api, formatClock } from '@/lib/api'
import { usePolling } from '@/lib/use-polling'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip)

type Point = [string, ...number[]]

interface CollectorMetrics {
  cpu_utilization?: Point[]
  gpu_utilization?: Point[]
  npu_utilization?: Point[]
  memory?: Point[]
  power?: Point[]
}

const HISTORY = 60
const COLLAPSED_KEY = 'scribe.performancePanel.collapsed'
const WIDTH_KEY = 'scribe.performancePanel.width'
const DEFAULT_WIDTH = 340
const MIN_WIDTH = 300
const EXPANDED_WIDTH = 760
/** From this width the charts sit two per row. */
const TWO_COLUMNS_FROM = 600

/** The panel never takes more than 70% of the window, so the page stays usable. */
const clampWidth = (width: number) =>
  Math.round(Math.min(Math.max(width, MIN_WIDTH), Math.max(MIN_WIDTH, window.innerWidth * 0.7)))

function Accordion({ title, children, defaultOpen = true }: { title: string; children: ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <section className="border-b border-slate-200">
      <button
        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold text-slate-800 hover:bg-slate-50"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        {title}
        <ChevronDown className={`size-4 text-slate-500 transition-transform ${open ? '' : '-rotate-90'}`} aria-hidden />
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </section>
  )
}

function UtilizationChart({ title, points, index = 1, color, unit = '%', max = 100, height = 110 }: {
  title: string
  points: Point[] | undefined
  index?: number
  color: string
  unit?: string
  max?: number
  height?: number
}) {
  const series = (points ?? []).slice(-HISTORY)
  const latest = series.at(-1)?.[index]
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <h4 className="text-xs font-semibold text-slate-600">{title}</h4>
        <span className="text-sm font-semibold tabular-nums" style={{ color }}>
          {latest === undefined ? '—' : `${Number(latest).toFixed(1)} ${unit}`}
        </span>
      </div>
      <div className="mt-1" style={{ height }}>
        {series.length > 1 ? (
          <Line
            data={{
              labels: series.map((p) => new Date(p[0]).toLocaleTimeString()),
              datasets: [
                {
                  data: series.map((p) => Number(p[index] ?? 0)),
                  borderColor: color,
                  backgroundColor: `${color}22`,
                  fill: true,
                  tension: 0.35,
                  pointRadius: 0,
                  borderWidth: 1.8,
                },
              ],
            }}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              animation: false,
              plugins: { legend: { display: false }, tooltip: { intersect: false, mode: 'index' } },
              scales: {
                y: { beginAtZero: true, suggestedMax: max, ticks: { font: { size: 10 }, maxTicksLimit: 4 } },
                x: { ticks: { font: { size: 9 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 4 } },
              },
            }}
          />
        ) : (
          <div className="flex h-full items-center justify-center rounded-lg bg-slate-50 text-xs text-slate-400">Waiting for data…</div>
        )}
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <p className="flex justify-between gap-3 py-0.5 text-xs">
      <span className="shrink-0 text-slate-500">{label}</span>
      <span className="text-right font-medium text-slate-800">{value}</span>
    </p>
  )
}

/** The right-hand performance panel, as in the patient-monitoring app: platform, live resource charts, last encounter. */
export function PerformancePanel() {
  const [collapsed, setCollapsed] = useState(false)
  useEffect(() => {
    setCollapsed(localStorage.getItem(COLLAPSED_KEY) === '1')
  }, [])
  const toggle = () =>
    setCollapsed((c) => {
      localStorage.setItem(COLLAPSED_KEY, c ? '0' : '1')
      return !c
    })

  const [width, setWidth] = useState(DEFAULT_WIDTH)
  const [dragging, setDragging] = useState(false)
  useEffect(() => {
    const saved = Number(localStorage.getItem(WIDTH_KEY))
    if (saved) setWidth(clampWidth(saved))
  }, [])
  const saveWidth = (next: number) => {
    const clamped = clampWidth(next)
    setWidth(clamped)
    localStorage.setItem(WIDTH_KEY, String(clamped))
  }
  const startDrag = (event: ReactPointerEvent) => {
    event.preventDefault()
    setDragging(true)
    const move = (e: PointerEvent) => setWidth(clampWidth(window.innerWidth - e.clientX))
    const up = (e: PointerEvent) => {
      saveWidth(window.innerWidth - e.clientX)
      setDragging(false)
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
    }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
  }
  const expanded = width >= EXPANDED_WIDTH - 20
  const twoColumns = width >= TWO_COLUMNS_FROM
  const chartHeight = Math.min(220, Math.max(110, Math.round(width / (twoColumns ? 4 : 3))))

  const metrics = usePolling(api.metrics, 3000)
  const encounters = usePolling(api.encounters, 10000)

  const m = (metrics.data?.metrics ?? {}) as CollectorMetrics
  const platform = (metrics.data?.platform ?? {}) as Record<string, string>
  const memory = m.memory?.at(-1)
  const lastUpdated = m.cpu_utilization?.at(-1)?.[0]
  const latest = (encounters.data ?? []).find((e) => e.timings.stt_seconds || e.timings.note_seconds)

  if (collapsed) {
    return (
      <aside className="sticky top-14 hidden h-[calc(100dvh-3.5rem)] w-8 shrink-0 border-l border-slate-200 bg-white xl:block">
        <button className="flex h-full w-full items-start justify-center pt-5 text-slate-500 hover:bg-slate-50" onClick={toggle} title="Show performance panel" aria-label="Show performance panel">
          <ChevronLeft className="size-4" />
        </button>
      </aside>
    )
  }

  return (
    <aside
      className={`sticky top-14 hidden h-[calc(100dvh-3.5rem)] shrink-0 flex-col border-l border-slate-200 bg-white xl:flex ${dragging ? 'select-none' : ''}`}
      style={{ width }}
      aria-label="System performance"
    >
      <div
        role="separator"
        aria-orientation="vertical"
        aria-label="Resize performance panel"
        aria-valuenow={width}
        aria-valuemin={MIN_WIDTH}
        tabIndex={0}
        title="Drag to resize · double-click to reset"
        onPointerDown={startDrag}
        onDoubleClick={() => saveWidth(DEFAULT_WIDTH)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowLeft') saveWidth(width + 40)
          if (e.key === 'ArrowRight') saveWidth(width - 40)
        }}
        className={`group absolute top-0 -left-1.5 z-10 flex h-full w-3 cursor-col-resize items-center justify-center outline-none`}
      >
        <span
          className={`h-12 w-1 rounded-full transition-colors ${dragging ? 'bg-[#0068b5]' : 'bg-slate-300 group-hover:bg-[#0068b5] group-focus-visible:bg-[#0068b5]'}`}
        />
      </div>
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 px-4">
        <div>
          <p className="text-sm font-semibold">System performance</p>
          <p className="text-[11px] text-slate-500">
            {metrics.data && !metrics.data.available
              ? 'Metrics collector not reachable'
              : lastUpdated
                ? `Last updated ${new Date(lastUpdated).toLocaleTimeString()}`
                : 'Connecting…'}
          </p>
        </div>
        <div className="flex items-center gap-1">
          <Link href="/system" className="rounded-md px-2 py-1 text-xs font-medium text-[#0068b5] hover:bg-sky-50">
            Details
          </Link>
          <button
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100"
            onClick={() => saveWidth(expanded ? DEFAULT_WIDTH : EXPANDED_WIDTH)}
            title={expanded ? 'Restore panel size' : 'Expand panel'}
            aria-label={expanded ? 'Restore panel size' : 'Expand panel'}
          >
            {expanded ? <Minimize2 className="size-4" /> : <Maximize2 className="size-4" />}
          </button>
          <button className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100" onClick={toggle} title="Hide performance panel" aria-label="Hide performance panel">
            <ChevronRight className="size-4" />
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <Accordion title="Configuration">
          <Row label="Processor" value={platform.Processor ?? 'Loading…'} />
          <Row label="iGPU" value={platform.iGPU ?? 'N/A'} />
          <Row label="NPU" value={platform.NPU ?? 'N/A'} />
          <Row label="Memory" value={platform.Memory ?? 'Loading…'} />
          <Row label="Storage" value={platform.Storage ?? 'Loading…'} />
        </Accordion>

        <Accordion title="Resource utilization">
          <div className={`grid gap-x-5 gap-y-4 ${twoColumns ? 'grid-cols-2' : 'grid-cols-1'}`}>
            <UtilizationChart title="CPU utilization" points={m.cpu_utilization} color="#2563eb" height={chartHeight} />
            <UtilizationChart title="GPU utilization" points={m.gpu_utilization} color="#0d9488" height={chartHeight} />
            <UtilizationChart title="NPU utilization" points={m.npu_utilization} color="#7c3aed" height={chartHeight} />
            <div>
              <UtilizationChart title="Memory utilization" points={m.memory} index={4} color="#e11d48" height={chartHeight} />
              {memory && (
                <p className="mt-1 text-[11px] text-slate-500">
                  {Number(memory[2]).toFixed(1)} of {Number(memory[1]).toFixed(0)} GB used
                </p>
              )}
            </div>
            <UtilizationChart title="Package power" points={m.power} color="#d97706" unit="W" max={10} height={chartHeight} />
          </div>
        </Accordion>

        <Accordion title="Last encounter">
          {latest ? (
            <>
              <p className="mb-1 truncate text-xs font-medium">{latest.name}</p>
              <Row label="Audio" value={latest.timings.audio_seconds ? formatClock(latest.timings.audio_seconds) : '—'} />
              <Row
                label="Speech to text + speakers"
                value={latest.timings.stt_seconds ? `${latest.timings.stt_seconds}s · RTF ${latest.timings.stt_rtf ?? '—'}` : '—'}
              />
              <Row label="Note: first words" value={latest.timings.note_ttft_seconds ? `${latest.timings.note_ttft_seconds}s` : '—'} />
              <Row label="Note: speed" value={latest.timings.note_tokens_per_second ? `${latest.timings.note_tokens_per_second} tokens/s` : '—'} />
            </>
          ) : (
            <p className="text-xs text-slate-500">No processed encounter yet.</p>
          )}
        </Accordion>
      </div>
    </aside>
  )
}
