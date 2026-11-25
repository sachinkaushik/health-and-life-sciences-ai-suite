// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0

'use client'

import { STATE_LABEL } from '@/lib/instances/service-presentation'
import { cn } from '@/lib/utils'
import type { SampleReadinessView } from '@/samples/common/readiness'
import { dependencyStyle, readinessStyle } from './readiness-styles'

/**
 * Readiness without controls, for services the app does not run (the `make up` containers): it
 * can only wait for them.
 */
export function ServicesWaitingPanel({ view }: { view: SampleReadinessView }) {
  const style = readinessStyle(view.state)
  const StateIcon = style.icon
  return (
    <section
      role="status"
      aria-labelledby="services-waiting-title"
      className="surface-panel rounded-xl p-5"
    >
      <div className="flex items-start gap-3">
        <StateIcon
          aria-hidden
          className={cn(
            'mt-0.5 h-5 w-5 shrink-0',
            style.text,
            style.spin && 'animate-spin',
          )}
        />
        <div>
          <h2
            id="services-waiting-title"
            className="text-foreground text-base font-semibold"
          >
            Getting the AI ready
          </h2>
          <p className="text-muted-foreground mt-1 text-sm">
            {view.requiredReady} of {view.requiredTotal} AI services are
            running. This page opens by itself once all of them are.
          </p>
        </div>
      </div>
      <ul className="mt-4 divide-y">
        {view.required.map((dep) => {
          const depStyle = dependencyStyle(dep.status)
          const DepIcon = depStyle.icon
          return (
            <li
              key={dep.serviceId}
              className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5"
            >
              <DepIcon
                aria-hidden
                className={cn(
                  'h-4 w-4 shrink-0',
                  depStyle.text,
                  depStyle.spin && 'animate-spin',
                )}
              />
              <span className="text-foreground min-w-40 flex-1 text-sm font-medium">
                {dep.name}
              </span>
              <span className={cn('text-xs', depStyle.text)}>
                {dep.status === 'missing'
                  ? 'Not set up'
                  : STATE_LABEL[dep.status]}
              </span>
              {dep.status === 'error' && dep.service?.statusMessage && (
                <p className="text-destructive w-full pl-7 text-xs">
                  {dep.service.statusMessage}
                </p>
              )}
            </li>
          )
        })}
      </ul>
      {(view.failed.length > 0 || view.missing.length > 0) && (
        <p className="text-muted-foreground mt-3 text-xs">
          The services run as containers: check them with{' '}
          <code>make status</code> and <code>make logs</code>.
        </p>
      )}
    </section>
  )
}
