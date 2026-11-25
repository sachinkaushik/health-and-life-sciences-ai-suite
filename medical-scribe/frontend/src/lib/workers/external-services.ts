// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

/**
 * Services that run outside the app (e.g. the docker compose containers) on fixed loopback ports:
 * `EXTERNAL_SERVICES="speech-to-text=8190,diarization=8191"`. The app neither spawns nor stops them;
 * it gives the type's instance that port, polls its health check and proxies to it. The ports must
 * be in the instance port range, the only ports the app probes and proxies to.
 */

import { logger } from '@/lib/logger'
import { isInstancePort } from '@/lib/workers/instance-ports'
import type { Service } from '@/payload-types'

const ENTRY = /^([a-z0-9-]+)=(\d{2,5})$/

let cached: { raw: string; ports: Map<string, number> } | undefined

function externalPorts(): Map<string, number> {
  const raw = process.env.EXTERNAL_SERVICES?.trim() ?? ''
  if (cached?.raw === raw) return cached.ports

  const ports = new Map<string, number>()
  for (const part of raw.split(',')) {
    const entry = part.trim()
    if (!entry) continue
    const match = entry.match(ENTRY)
    const port = match ? Number(match[2]) : 0
    if (!match || !isInstancePort(port)) {
      logger.warn(
        `EXTERNAL_SERVICES entry "${entry}" is invalid (expected <type>=<port> with the port in the instance port range), ignored`,
      )
      continue
    }
    ports.set(match[1], port)
  }
  cached = { raw, ports }
  return ports
}

/** The fixed port of an externally run service type, if it is one. */
export function getExternalPort(
  type: string | null | undefined,
): number | undefined {
  return type ? externalPorts().get(type) : undefined
}

export function isExternalService(service: Pick<Service, 'type'>): boolean {
  return getExternalPort(service.type) !== undefined
}

/** Every port an external service listens on: never the app's to clean up. */
export function getExternalServicePorts(): Set<number> {
  return new Set(externalPorts().values())
}
