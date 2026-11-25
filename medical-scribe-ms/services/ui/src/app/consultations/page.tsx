// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
'use client'

import {
  CheckCircle2,
  Copy,
  FileAudio,
  Loader2,
  Mic,
  Pencil,
  Plus,
  Save,
  Sparkles,
  Square,
  Trash2,
  Upload,
  Users,
} from 'lucide-react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense, useEffect, useRef, useState } from 'react'
import { DoctorsDialog } from '@/components/doctors-dialog'
import { Markdown } from '@/components/markdown'
import {
  api,
  type Encounter,
  encounterState,
  formatClock,
  formatTime,
  LANGUAGES,
  streamNote,
  TONE_PILL,
} from '@/lib/api'
import { type LiveSession, startLive } from '@/lib/live'
import { usePolling } from '@/lib/use-polling'

const SPEAKER_COLOR: Record<string, string> = { Doctor: 'text-[#0068b5]', Patient: 'text-emerald-600' }

export default function ConsultationsPage() {
  return (
    <Suspense fallback={null}>
      <Consultations />
    </Suspense>
  )
}

function Consultations() {
  const router = useRouter()
  const params = useSearchParams()
  const encounters = usePolling(api.encounters, 3000)
  const doctors = usePolling(api.doctors, 30000)
  const status = usePolling(api.status, 5000)

  const list = encounters.data ?? []
  const selectedId = params.get('id') ?? list[0]?.id ?? null
  const selected = list.find((e) => e.id === selectedId) ?? null
  const select = (id: string) => router.replace(`/consultations?id=${id}`)

  const ready = new Map((status.data?.services ?? []).map((s) => [s.id, s.ready]))
  const canTranscribe = ready.get('speech-to-text') && ready.get('diarization') && ready.get('encounter-store')
  const canWrite = ready.get('text-generation') && ready.get('encounter-store')
  const notReady = (status.data?.services ?? []).filter((s) => !s.ready)

  // New encounter
  const [name, setName] = useState('')
  const [doctorId, setDoctorId] = useState('')
  const [language, setLanguage] = useState('auto')
  const nameRef = useRef<HTMLInputElement>(null)
  useEffect(() => {
    if (params.get('new')) nameRef.current?.focus()
  }, [params])
  const [showDoctors, setShowDoctors] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createEncounter = async () => {
    setError(null)
    try {
      const e = await api.createEncounter({ name: name.trim(), doctor_id: doctorId || null, language })
      setName('')
      encounters.setData([e, ...list])
      select(e.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the encounter')
    }
  }

  // Live recording
  const live = useRef<LiveSession | null>(null)
  const [recordingId, setRecordingId] = useState<string | null>(null)
  const [liveLines, setLiveLines] = useState<string[]>([])
  const [level, setLevel] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  useEffect(() => {
    if (!recordingId) return
    const started = Date.now()
    const timer = setInterval(() => setElapsed((Date.now() - started) / 1000), 500)
    return () => clearInterval(timer)
  }, [recordingId])
  useEffect(() => () => live.current?.stop(), [])

  const startRecording = async (e: Encounter) => {
    setError(null)
    setLiveLines([])
    setElapsed(0)
    try {
      live.current = await startLive(e.id, {
        onUtterance: (text) => setLiveLines((lines) => [...lines, text]),
        onLevel: setLevel,
        onProcessing: () => encounters.reload(),
        onError: (message) => setError(message),
        onClosed: () => {
          live.current = null
          setRecordingId(null)
          setLevel(0)
          encounters.reload()
        },
      })
      setRecordingId(e.id)
      encounters.reload()
    } catch (err) {
      setError(err instanceof Error ? `Microphone: ${err.message}` : 'Could not open the microphone')
    }
  }

  const fileInput = useRef<HTMLInputElement>(null)
  const upload = async (file: File) => {
    if (!selected) return
    setError(null)
    try {
      await api.uploadAudio(selected.id, file)
      encounters.reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    }
  }

  // SOAP note
  const [streaming, setStreaming] = useState<{ id: string; text: string } | null>(null)
  const [noteError, setNoteError] = useState<string | null>(null)
  const [draft, setDraft] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    setDraft(null)
    setNoteError(null)
  }, [selectedId])

  const generate = async (e: Encounter) => {
    setNoteError(null)
    setDraft(null)
    setStreaming({ id: e.id, text: '' })
    await streamNote(e.id, {
      onDelta: (text) => setStreaming((s) => (s ? { ...s, text: s.text + text } : s)),
      onDone: () => encounters.reload(),
      onError: (message) => setNoteError(message),
    }).catch((err) => setNoteError(err instanceof Error ? err.message : 'Note generation failed'))
    setStreaming(null)
    encounters.reload()
  }

  const saveDraft = async () => {
    if (!selected || draft === null) return
    await api.updateEncounter(selected.id, { note: draft, reviewed: false })
    setDraft(null)
    encounters.reload()
  }

  const toggleReviewed = async (e: Encounter) => {
    await api.updateEncounter(e.id, { reviewed: !e.reviewed })
    encounters.reload()
  }

  const remove = async (e: Encounter) => {
    if (!confirm(`Delete "${e.name}" and its transcript and note?`)) return
    await api.deleteEncounter(e.id)
    if (e.id === selectedId) router.replace('/consultations')
    encounters.reload()
  }

  const isRecording = Boolean(selected && recordingId === selected.id)
  const busy = selected && (selected.status === 'processing' || selected.status === 'recording')
  const noteText = streaming && streaming.id === selected?.id ? streaming.text : selected?.note
  const generating = Boolean(streaming && streaming.id === selected?.id)

  return (
    <div className="mx-auto flex h-[calc(100dvh-3rem)] max-w-[1500px] flex-col gap-4">
      <header className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Consultations</h1>
        {status.data && (
          <span
            role="status"
            className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${status.data.ready ? TONE_PILL.success : TONE_PILL.warning}`}
          >
            {status.data.ready ? 'AI ready' : `Waiting for: ${notReady.map((s) => s.label).join(', ')}`}
          </span>
        )}
        <button className="btn btn-outline ml-auto" onClick={() => setShowDoctors(true)}>
          <Users className="size-4" aria-hidden /> Doctors
        </button>
      </header>
      {error && (
        <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[18rem_1fr_1fr]">
        {/* Encounters */}
        <section className="card flex min-h-0 flex-col p-4" aria-label="Encounters">
          <form
            className="space-y-2"
            onSubmit={(e) => {
              e.preventDefault()
              if (name.trim()) createEncounter()
            }}
          >
            <h2 className="text-sm font-semibold">New encounter</h2>
            <input ref={nameRef} className="field" placeholder="Encounter name" value={name} onChange={(e) => setName(e.target.value)} maxLength={200} />
            <select className="field" value={doctorId} onChange={(e) => setDoctorId(e.target.value)} aria-label="Doctor">
              <option value="">No doctor (2 speakers)</option>
              {(doctors.data ?? []).map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                  {d.enrolled ? '' : ' (voice not enrolled)'}
                </option>
              ))}
            </select>
            <select className="field" value={language} onChange={(e) => setLanguage(e.target.value)} aria-label="Language">
              {LANGUAGES.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </select>
            <button className="btn btn-primary w-full justify-center" disabled={!name.trim()}>
              <Plus className="size-4" aria-hidden /> Create encounter
            </button>
          </form>
          <ul className="-mx-2 mt-4 min-h-0 flex-1 overflow-y-auto border-t border-slate-100 pt-2">
            {list.map((e) => {
              const state = encounterState(e)
              return (
                <li key={e.id} className="group flex items-center">
                  <button
                    onClick={() => select(e.id)}
                    className={`min-w-0 flex-1 rounded-lg px-2 py-2 text-left ${e.id === selectedId ? 'bg-sky-50' : 'hover:bg-slate-50'}`}
                  >
                    <span className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium">{e.name}</span>
                      <span className={`ml-auto shrink-0 rounded-full border px-1.5 text-[11px] ${TONE_PILL[state.tone]}`}>{state.label}</span>
                    </span>
                    <span className="block truncate text-xs text-slate-500">
                      {[e.doctor_name, formatTime(e.created_at)].filter(Boolean).join(' · ')}
                    </span>
                  </button>
                  <button className="p-2 text-slate-400 opacity-0 group-hover:opacity-100 hover:text-red-600 focus:opacity-100" aria-label={`Delete ${e.name}`} onClick={() => remove(e)}>
                    <Trash2 className="size-4" />
                  </button>
                </li>
              )
            })}
            {encounters.data && list.length === 0 && <li className="px-2 py-3 text-sm text-slate-500">No encounters yet.</li>}
          </ul>
        </section>

        {/* Transcript */}
        <section className="card flex min-h-0 flex-col" aria-label="Transcript">
          <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-5 py-3">
            <h2 className="font-semibold">Transcript</h2>
            {selected && (
              <div className="ml-auto flex gap-2">
                {isRecording ? (
                  <button className="btn btn-danger" onClick={() => live.current?.stop()}>
                    <Square className="size-4" aria-hidden /> Stop · {formatClock(elapsed)}
                  </button>
                ) : (
                  <button className="btn btn-primary" disabled={!canTranscribe || Boolean(busy) || recordingId !== null} onClick={() => startRecording(selected)}>
                    <Mic className="size-4" aria-hidden /> Record
                  </button>
                )}
                <button className="btn btn-outline" disabled={!canTranscribe || Boolean(busy) || recordingId !== null} onClick={() => fileInput.current?.click()}>
                  <Upload className="size-4" aria-hidden /> Upload
                </button>
                <input
                  ref={fileInput}
                  type="file"
                  accept="audio/*,.wav,.mp3,.m4a,.flac,.ogg,.webm"
                  hidden
                  onChange={(ev) => {
                    const file = ev.target.files?.[0]
                    if (file) upload(file)
                    ev.target.value = ''
                  }}
                />
              </div>
            )}
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
            {!selected && <p className="text-sm text-slate-500">Create or pick an encounter.</p>}
            {isRecording && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-medium text-red-600">
                  <span className="size-2 animate-pulse rounded-full bg-red-600" aria-hidden /> Live
                  <span className="h-1.5 w-24 overflow-hidden rounded bg-slate-100" aria-hidden>
                    <span className="block h-full bg-emerald-500 transition-[width]" style={{ width: `${Math.min(100, level * 300)}%` }} />
                  </span>
                </div>
                {liveLines.map((line, i) => (
                  <p key={i} className="text-sm text-slate-700">
                    {line}
                  </p>
                ))}
                {liveLines.length === 0 && <p className="text-sm text-slate-500">Listening…</p>}
              </div>
            )}
            {selected && !isRecording && selected.status === 'processing' && (
              <p className="flex items-center gap-2 text-sm text-slate-600">
                <Loader2 className="size-4 animate-spin" aria-hidden /> Transcribing and identifying speakers…
              </p>
            )}
            {selected && !isRecording && selected.status === 'error' && (
              <p className="text-sm text-red-600">{selected.error ?? 'Processing failed'}. Record or upload again.</p>
            )}
            {selected && !isRecording && selected.status !== 'processing' && selected.transcript.length === 0 && selected.status !== 'error' && (
              <div className="flex flex-col items-center gap-2 py-16 text-center text-sm text-slate-500">
                <FileAudio className="size-8 text-slate-300" aria-hidden />
                Record the consultation or upload a recording.
              </div>
            )}
            {selected && !isRecording && selected.status !== 'processing' && (
              <ol className="space-y-3">
                {selected.transcript.map((t, i) => (
                  <li key={i}>
                    <p className="text-xs">
                      <span className={`font-semibold ${SPEAKER_COLOR[t.speaker] ?? 'text-violet-600'}`}>{t.speaker || 'Speaker'}</span>{' '}
                      <span className="text-slate-400">
                        {formatClock(t.start)} – {formatClock(t.end)}
                      </span>
                    </p>
                    <p className="text-sm text-slate-800">{t.text}</p>
                  </li>
                ))}
              </ol>
            )}
          </div>
          {selected?.transcribed_at && (
            <p className="border-t border-slate-100 px-5 py-2 text-xs text-slate-500">
              {formatTime(selected.transcribed_at)}
              {selected.timings.audio_seconds ? ` · ${formatClock(selected.timings.audio_seconds)} audio` : ''}
              {selected.timings.stt_seconds ? ` · transcribed in ${selected.timings.stt_seconds}s` : ''}
              {selected.timings.diarization_seconds ? ` · speakers in ${selected.timings.diarization_seconds}s` : ''}
            </p>
          )}
        </section>

        {/* SOAP note */}
        <section className="card flex min-h-0 flex-col" aria-label="SOAP note">
          <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-5 py-3">
            <h2 className="font-semibold">SOAP note</h2>
            {selected?.note && !generating && (
              <span className={`rounded-full border px-2 py-0.5 text-xs ${selected.reviewed ? TONE_PILL.success : TONE_PILL.muted}`}>
                {selected.reviewed ? 'Reviewed' : 'Draft'}
              </span>
            )}
            {selected && (
              <div className="ml-auto flex gap-2">
                {selected.note && !generating && draft === null && (
                  <>
                    <button className="btn btn-outline px-2" aria-label="Edit note" onClick={() => setDraft(selected.note ?? '')}>
                      <Pencil className="size-4" />
                    </button>
                    <button
                      className="btn btn-outline px-2"
                      aria-label="Copy note"
                      onClick={async () => {
                        await navigator.clipboard.writeText(selected.note ?? '')
                        setCopied(true)
                        setTimeout(() => setCopied(false), 1500)
                      }}
                    >
                      {copied ? <CheckCircle2 className="size-4 text-emerald-600" /> : <Copy className="size-4" />}
                    </button>
                  </>
                )}
                <button
                  className="btn btn-primary"
                  disabled={!canWrite || generating || selected.transcript.length === 0 || selected.status === 'processing'}
                  onClick={() => generate(selected)}
                >
                  {generating ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Sparkles className="size-4" aria-hidden />}
                  {selected.note ? 'Regenerate' : 'Generate note'}
                </button>
              </div>
            )}
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
            {noteError && <p className="mb-3 text-sm text-red-600">{noteError}</p>}
            {draft !== null ? (
              <textarea className="field h-full min-h-80 font-mono text-xs" value={draft} onChange={(e) => setDraft(e.target.value)} aria-label="Edit SOAP note" />
            ) : noteText ? (
              <Markdown text={noteText} />
            ) : (
              <p className="text-sm text-slate-500">
                {selected?.transcript.length ? 'Generate the SOAP note from the transcript.' : 'The note is written from the transcript.'}
              </p>
            )}
          </div>
          {selected && (draft !== null || (selected.note && !generating)) && (
            <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 px-5 py-2 text-xs text-slate-500">
              {draft !== null ? (
                <>
                  <button className="btn btn-primary" onClick={saveDraft}>
                    <Save className="size-4" aria-hidden /> Save
                  </button>
                  <button className="btn btn-outline" onClick={() => setDraft(null)}>
                    Cancel
                  </button>
                </>
              ) : (
                <>
                  <label className="flex items-center gap-2 text-sm text-slate-700">
                    <input type="checkbox" checked={selected.reviewed} onChange={() => toggleReviewed(selected)} /> Reviewed by clinician
                  </label>
                  <span className="ml-auto">
                    {formatTime(selected.noted_at)}
                    {selected.timings.note_ttft_seconds ? ` · first words ${selected.timings.note_ttft_seconds}s` : ''}
                    {selected.timings.note_tokens_per_second ? ` · ${selected.timings.note_tokens_per_second} tokens/s` : ''}
                  </span>
                </>
              )}
            </div>
          )}
        </section>
      </div>

      {showDoctors && <DoctorsDialog doctors={doctors.data ?? []} onClose={() => setShowDoctors(false)} onChanged={doctors.reload} />}
    </div>
  )
}
