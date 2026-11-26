// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
'use client'

import { useEffect, useRef, useState } from 'react'

/** Polls `load` every `intervalMs` (and on mount); `reload` refreshes at once. */
export function usePolling<T>(load: () => Promise<T>, intervalMs: number) {
  const [data, setData] = useState<T | undefined>(undefined)
  const [error, setError] = useState<string | null>(null)
  const loadRef = useRef(load)
  loadRef.current = load
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      try {
        const value = await loadRef.current()
        if (!cancelled) {
          setData(value)
          setError(null)
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Request failed')
      }
    }
    run()
    const timer = setInterval(run, intervalMs)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [intervalMs, tick])

  return { data, error, reload: () => setTick((t) => t + 1), setData }
}
