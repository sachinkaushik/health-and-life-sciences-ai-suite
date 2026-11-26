// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

/** The Medical Scribe API (scribe-aggregator), reached through the gateway at /api. */

export interface TranscriptEntry {
  speaker: string
  text: string
  start: number
  end: number
}

export type EncounterStatus =
  'new' | 'recording' | 'processing' | 'transcribed' | 'error'

export interface Encounter {
  id: string
  name: string
  doctor_id: string | null
  doctor_name: string | null
  language: string
  status: EncounterStatus
  error: string | null
  transcript: TranscriptEntry[]
  note: string | null
  reviewed: boolean
  timings: Record<string, number>
  created_at: string
  updated_at: string
  transcribed_at: string | null
  noted_at: string | null
}

export interface Doctor {
  id: string
  name: string
  enrolled: boolean
  created_at: string
}

export interface ServiceState {
  id: string
  label: string
  ready: boolean
}

export interface AppStatus {
  ready: boolean
  services: ServiceState[]
}

export interface AppConfig {
  stt: { model: string; device: string }
  diarization: { model: string; device: string }
  text_generation: { model: string; device: string }
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`/api${path}`, init)
  if (!resp.ok) {
    let detail = resp.statusText
    try {
      const body = await resp.json()
      detail = typeof body.detail === 'string' ? body.detail : detail
    } catch {
      // not JSON
    }
    throw new ApiError(detail || `Request failed (${resp.status})`, resp.status)
  }
  return resp.status === 204 ? (undefined as T) : resp.json()
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  status: () => request<AppStatus>('/status'),
  config: () => request<AppConfig>('/config'),
  metrics: () => request<{ available: boolean; metrics?: unknown; platform?: unknown }>('/metrics'),
  doctors: () => request<Doctor[]>('/doctors'),
  createDoctor: (name: string) => request<Doctor>('/doctors', json('POST', { name })),
  deleteDoctor: (id: string) => request<void>(`/doctors/${id}`, { method: 'DELETE' }),
  enrolVoice: (id: string, audio: Blob) => {
    const form = new FormData()
    form.append('file', audio, audio instanceof File ? audio.name : 'voice.webm')
    return request<Doctor>(`/doctors/${id}/voice`, { method: 'POST', body: form })
  },
  encounters: () => request<Encounter[]>('/encounters'),
  encounter: (id: string) => request<Encounter>(`/encounters/${id}`),
  createEncounter: (body: { name: string; doctor_id: string | null; language: string }) =>
    request<Encounter>('/encounters', json('POST', body)),
  updateEncounter: (id: string, body: Partial<Pick<Encounter, 'name' | 'note' | 'reviewed'>>) =>
    request<Encounter>(`/encounters/${id}`, json('PATCH', body)),
  deleteEncounter: (id: string) => request<void>(`/encounters/${id}`, { method: 'DELETE' }),
  uploadAudio: (id: string, file: File) => {
    const form = new FormData()
    form.append('file', file, file.name)
    return request<{ status: string }>(`/encounters/${id}/audio`, { method: 'POST', body: form })
  },
}

export interface NoteEvents {
  onDelta: (text: string) => void
  onDone: (note: string) => void
  onError: (message: string) => void
}

/** Streams the SOAP note (server-sent events over a POST). */
export async function streamNote(id: string, events: NoteEvents, signal?: AbortSignal) {
  const resp = await fetch(`/api/encounters/${id}/note`, { method: 'POST', signal })
  if (!resp.ok || !resp.body) {
    let detail = `Request failed (${resp.status})`
    try {
      detail = (await resp.json()).detail ?? detail
    } catch {
      // not JSON
    }
    events.onError(detail)
    return
  }
  const reader = resp.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += value
    let cut
    while ((cut = buffer.indexOf('\n\n')) >= 0) {
      const block = buffer.slice(0, cut)
      buffer = buffer.slice(cut + 2)
      const event = /^event: (.*)$/m.exec(block)?.[1]
      const data = /^data: (.*)$/m.exec(block)?.[1]
      if (!event || !data) continue
      const payload = JSON.parse(data)
      if (event === 'delta') events.onDelta(payload.text)
      else if (event === 'done') events.onDone(payload.note)
      else if (event === 'error') events.onError(payload.message)
    }
  }
}

export const LANGUAGES: { value: string; label: string }[] = [
  { value: 'auto', label: 'Auto-detect' },
  { value: 'en', label: 'English' },
  { value: 'zh', label: 'Chinese' },
  { value: 'ms', label: 'Malay' },
  { value: 'ta', label: 'Tamil' },
  { value: 'hi', label: 'Hindi' },
  { value: 'id', label: 'Indonesian' },
  { value: 'th', label: 'Thai' },
  { value: 'vi', label: 'Vietnamese' },
  { value: 'ja', label: 'Japanese' },
  { value: 'ko', label: 'Korean' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'es', label: 'Spanish' },
]

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const date = new Date(iso)
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export function formatClock(seconds: number): string {
  const s = Math.max(0, Math.round(seconds))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

export function encounterState(e: Encounter): { label: string; tone: Tone } {
  if (e.status === 'recording') return { label: 'Recording', tone: 'warning' }
  if (e.status === 'processing') return { label: 'Processing', tone: 'info' }
  if (e.status === 'error') return { label: 'Failed', tone: 'danger' }
  if (e.note && e.reviewed) return { label: 'Reviewed', tone: 'success' }
  if (e.note) return { label: 'Note ready', tone: 'success' }
  if (e.transcript.length > 0) return { label: 'Needs note', tone: 'warning' }
  return { label: 'Not recorded', tone: 'muted' }
}

export type Tone = 'success' | 'warning' | 'info' | 'danger' | 'muted'

export const TONE_PILL: Record<Tone, string> = {
  success: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  warning: 'border-amber-200 bg-amber-50 text-amber-700',
  info: 'border-sky-200 bg-sky-50 text-sky-700',
  danger: 'border-red-200 bg-red-50 text-red-700',
  muted: 'border-slate-200 bg-slate-50 text-slate-500',
}
