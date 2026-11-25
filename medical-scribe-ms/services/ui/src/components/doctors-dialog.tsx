// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
'use client'

import { Check, Mic, Trash2, UserPlus, X } from 'lucide-react'
import { useState } from 'react'
import { api, type Doctor } from '@/lib/api'
import { recordSample } from '@/lib/live'

const SAMPLE_SECONDS = 10

/** Add doctors and enrol their voice, so diarization labels them "Doctor". */
export function DoctorsDialog({ doctors, onClose, onChanged }: { doctors: Doctor[]; onClose: () => void; onChanged: () => void }) {
  const [name, setName] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const [countdown, setCountdown] = useState(0)
  const [error, setError] = useState<string | null>(null)

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
      setCountdown(0)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4" role="dialog" aria-modal="true" aria-labelledby="doctors-title">
      <div className="card w-full max-w-lg p-6">
        <div className="flex items-center justify-between">
          <h2 id="doctors-title" className="text-lg font-semibold">
            Doctors
          </h2>
          <button className="btn btn-outline px-2" onClick={onClose} aria-label="Close">
            <X className="size-4" />
          </button>
        </div>
        <p className="mt-1 text-sm text-slate-500">
          Enrol a doctor&apos;s voice ({SAMPLE_SECONDS} s of speech) so transcripts label them as Doctor and the other speaker as
          Patient.
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

        <ul className="mt-4 divide-y divide-slate-100">
          {doctors.map((d) => (
            <li key={d.id} className="flex items-center gap-3 py-2.5">
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
              <button
                className="btn btn-outline"
                disabled={busy !== null}
                onClick={() => run(`voice-${d.id}`, async () => api.enrolVoice(d.id, await recordSample(SAMPLE_SECONDS, setCountdown)))}
              >
                <Mic className="size-4" aria-hidden />
                {busy === `voice-${d.id}` ? (countdown > 0 ? `Speak… ${countdown}s` : 'Enrolling…') : d.enrolled ? 'Re-enrol' : 'Enrol voice'}
              </button>
              <button
                className="btn btn-outline px-2"
                aria-label={`Delete ${d.name}`}
                disabled={busy !== null}
                onClick={() => confirm(`Delete ${d.name}?`) && run(`del-${d.id}`, () => api.deleteDoctor(d.id))}
              >
                <Trash2 className="size-4" />
              </button>
            </li>
          ))}
          {doctors.length === 0 && <li className="py-3 text-sm text-slate-500">No doctors yet.</li>}
        </ul>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>
    </div>
  )
}
