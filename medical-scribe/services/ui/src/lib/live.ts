// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
'use client'

/** Microphone → 16 kHz mono 16-bit PCM → `/api/live/{id}`; the aggregator does the rest. */

const TARGET_RATE = 16000

// Averages the input down to 16 kHz and posts ~100 ms of Int16 samples at a time.
const WORKLET = `
class PcmDownsampler extends AudioWorkletProcessor {
  constructor(options) {
    super()
    this.ratio = sampleRate / ${TARGET_RATE}
    this.acc = 0
    this.count = 0
    this.pos = 0
    this.out = new Int16Array(${TARGET_RATE / 10})
    this.n = 0
  }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0]
    if (!ch) return true
    let level = 0
    for (let i = 0; i < ch.length; i++) {
      const s = ch[i]
      level = Math.max(level, Math.abs(s))
      this.acc += s
      this.count++
      this.pos += 1
      if (this.pos >= this.ratio) {
        this.pos -= this.ratio
        const v = Math.max(-1, Math.min(1, this.acc / this.count))
        this.out[this.n++] = v < 0 ? v * 0x8000 : v * 0x7fff
        this.acc = 0
        this.count = 0
        if (this.n === this.out.length) {
          this.port.postMessage({ pcm: this.out.buffer, level }, [this.out.buffer])
          this.out = new Int16Array(${TARGET_RATE / 10})
          this.n = 0
          level = 0
        }
      }
    }
    return true
  }
}
registerProcessor('pcm-downsampler', PcmDownsampler)
`

export interface LiveHandlers {
  onUtterance: (text: string) => void
  onLevel: (level: number) => void
  onProcessing: () => void
  onError: (message: string) => void
  onClosed: () => void
}

export interface LiveSession {
  stop: () => void
}

export async function startLive(encounterId: string, handlers: LiveHandlers): Promise<LiveSession> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
  })
  const ctx = new AudioContext()
  const url = URL.createObjectURL(new Blob([WORKLET], { type: 'application/javascript' }))
  await ctx.audioWorklet.addModule(url)
  URL.revokeObjectURL(url)
  const source = ctx.createMediaStreamSource(stream)
  const node = new AudioWorkletNode(ctx, 'pcm-downsampler')
  source.connect(node)

  const scheme = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const ws = new WebSocket(`${scheme}//${location.host}/api/live/${encodeURIComponent(encounterId)}`)
  ws.binaryType = 'arraybuffer'

  let stopped = false
  const release = () => {
    node.port.onmessage = null
    source.disconnect()
    node.disconnect()
    stream.getTracks().forEach((t) => t.stop())
    ctx.close().catch(() => {})
  }

  node.port.onmessage = (event: MessageEvent<{ pcm: ArrayBuffer; level: number }>) => {
    handlers.onLevel(event.data.level)
    if (!stopped && ws.readyState === WebSocket.OPEN) ws.send(event.data.pcm)
  }
  ws.onmessage = (event) => {
    const msg = JSON.parse(String(event.data))
    if (msg.type === 'utterance') handlers.onUtterance(msg.text)
    else if (msg.type === 'processing') handlers.onProcessing()
    else if (msg.type === 'error') handlers.onError(msg.message)
  }
  ws.onerror = () => handlers.onError('The live connection failed')
  ws.onclose = () => {
    release()
    handlers.onClosed()
  }

  return {
    stop: () => {
      if (stopped) return
      stopped = true
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'stop' }))
      release()
    },
  }
}

export interface SampleRecorder {
  /** Stops and returns the recording (webm/opus). */
  stop: () => Promise<Blob>
  /** Stops and drops the recording. */
  cancel: () => void
}

/** Microphone recording for voice enrolment, stopped by the user. */
export async function startSampleRecorder(): Promise<SampleRecorder> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const recorder = new MediaRecorder(stream)
  const chunks: Blob[] = []
  recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data)
  const done = new Promise<Blob>((resolve) => {
    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop())
      resolve(new Blob(chunks, { type: recorder.mimeType }))
    }
  })
  recorder.start()
  return {
    stop: () => {
      if (recorder.state !== 'inactive') recorder.stop()
      return done
    },
    cancel: () => {
      if (recorder.state !== 'inactive') recorder.stop()
    },
  }
}
