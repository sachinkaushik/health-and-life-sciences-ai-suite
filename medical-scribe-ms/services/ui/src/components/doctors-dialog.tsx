// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
'use client'

import { Check, Loader2, Mic, Square, Trash2, Upload, UserPlus, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api, type Doctor } from '@/lib/api'
import { type SampleRecorder, startSampleRecorder } from '@/lib/live'

const MIN_SECONDS = 3

/** Add doctors and enrol their voice (record or upload), so diarization labels them "Doctor". */
export function DoctorsDialog({ doctors, onClose, onChanged }: { doctors: Doctor[]; onClose: () => void; onChanged: () => void }) {
  const [name, setName] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [recording, setRecording] = useState<{ id: string; recorder: SampleRecorder; started: number } | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const fileInput = useRef<HTMLInputElement>(null)
  const uploadFor = useRef<string | null>(null)

  useEffect(() => {
    if (!recording) return
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - recording.started) / 1000)), 250)
    return () => clearInterval(timer)
  }, [recording])
  // Closing the dialog mid-recording drops the recording rather than leaving the microphone on.
  const recordingRef = useRef(recording)
  recordingRef.current = recording
  useEffect(() => () => recordingRef.current?.recorder.cancel(), [])

  const run = async (key: string, action: () => Promise<unknown>) => {
    setBusy(key)
    setError(null)
    try {
      await action()
      onChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong')
    } finally {
      setBusy(null)
    }
  }

  const startRecording = async (id: string) => {
    setError(null)
    try {
      setElapsed(0)
      setRecording({ id, recorder: await startSampleRecorder(), started: Date.now() })
    } catch (e) {
      setError(e instanceof Error ? `Microphone: ${e.message}` : 'Could not open the microphone')
    }
  }

  const stopAndEnrol = async () => {
    if (!recording) return
    const { id, recorder } = recording
    const seconds = elapsed
    setRecording(null)
    const audio = await recorder.stop()
    if (seconds < MIN_SECONDS) {
      setError(`Record at least ${MIN_SECONDS} seconds of speech.`)
      return
    }
    await run(`voice-${id}`, () => api.enrolVoice(id, audio))
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" role="dialog" aria-modal="true" aria-labelledby="doctors-title">
      <div className="card w-full max-w-xl p-6">
        <div className="flex items-center justify-between">
          <h2 id="doctors-title" className="text-lg font-semibold">
            Doctors
          </h2>
          <button className="btn btn-outline px-2" onClick={onClose} aria-label="Close">
            <X className="size-4" />
          </button>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          Enrol a doctor&apos;s voice so transcripts label them as Doctor and the other speaker as Patient: record about 10 s of
          speech, or upload a voice sample (WAV, MP3, M4A, WebM).
        </p>

        <form
          className="mt-4 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            if (name.trim()) run('add', () => api.createDoctor(name.trim()).then(() => setName('')))
          }}
        >
          <input className="field" placeholder="Doctor name" value={name} onChange={(e) => setName(e.target.value)} maxLength={200} />
          <button className="btn btn-primary shrink-0" disabled={!name.trim() || busy !== null}>
            <UserPlus className="size-4" aria-hidden /> Add
          </button>
        </form>

        <input
          ref={fileInput}
          type="file"
          accept="audio/*,.wav,.mp3,.m4a,.webm,.ogg,.flac"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0]
            const id = uploadFor.current
            e.target.value = ''
            if (file && id) run(`voice-${id}`, () => api.enrolVoice(id, file))
          }}
        />

        <ul className="mt-4 divide-y divide-slate-100">
          {doctors.map((d) => {
            const isRecording = recording?.id === d.id
            const isEnrolling = busy === `voice-${d.id}`
            const locked = busy !== null || (recording !== null && !isRecording)
            return (
              <li key={d.id} className="flex flex-wrap items-center gap-2 py-2.5">
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium">{d.name}</span>
                  <span className={`text-xs ${d.enrolled ? 'text-emerald-600' : 'text-slate-500'}`}>
                    {d.enrolled ? (
                      <>
                        <Check className="inline size-3" aria-hidden /> Voice enrolled
                      </>
                    ) : (
                      'Voice not enrolled'
                    )}
                  </span>
                </span>
                {isRecording && recording ? (
                  <>
                    <span className="flex items-center gap-1.5 text-xs font-medium text-red-600">
                      <span className="size-2 animate-pulse rounded-full bg-red-600" aria-hidden /> {elapsed}s
                    </span>
                    <button className="btn btn-danger" onClick={stopAndEnrol}>
                      <Square className="size-4" aria-hidden /> Stop and enrol
                    </button>
                    <button
                      className="btn btn-outline"
                      onClick={() => {
                        recording.recorder.cancel()
                        setRecording(null)
                      }}
                    >
                      Cancel
                    </button>
                  </>
                ) : isEnrolling ? (
                  <span className="flex items-center gap-1.5 text-xs text-slate-600">
                    <Loader2 className="size-4 animate-spin" aria-hidden /> Enrolling…
                  </span>
                ) : (
                  <>
                    <button className="btn btn-outline" disabled={locked} onClick={() => startRecording(d.id)}>
                      <Mic className="size-4" aria-hidden /> {d.enrolled ? 'Re-record' : 'Record'}
                    </button>
                    <button
                      className="btn btn-outline"
                      disabled={locked}
                      onClick={() => {
                        uploadFor.current = d.id
                        fileInput.current?.click()
                      }}
                    >
                      <Upload className="size-4" aria-hidden /> Upload
                    </button>
                  </>
                )}
                <button
                  className="btn btn-outline px-2"
                  aria-label={`Delete ${d.name}`}
                  disabled={locked || isRecording}
                  onClick={() => confirm(`Delete ${d.name}?`) && run(`del-${d.id}`, () => api.deleteDoctor(d.id))}
                >
                  <Trash2 className="size-4" />
                </button>
              </li>
            )
          })}
          {doctors.length === 0 && <li className="py-3 text-sm text-slate-500">No doctors yet.</li>}
        </ul>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>
    </div>
  )
}
