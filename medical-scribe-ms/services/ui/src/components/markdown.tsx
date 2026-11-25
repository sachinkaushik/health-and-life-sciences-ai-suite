// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
import type { ReactNode } from 'react'

/** The Markdown a SOAP note uses: headings, bullet and numbered lists, **bold**, paragraphs. */
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : part,
  )
}

export function Markdown({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let list: { ordered: boolean; items: string[] } | null = null
  const flush = () => {
    if (!list) return
    const Tag = list.ordered ? 'ol' : 'ul'
    blocks.push(
      <Tag key={blocks.length} className={list.ordered ? 'ml-5 list-decimal space-y-1' : 'ml-5 list-disc space-y-1'}>
        {list.items.map((item, i) => (
          <li key={i}>{inline(item)}</li>
        ))}
      </Tag>,
    )
    list = null
  }
  for (const raw of text.split('\n')) {
    const line = raw.trimEnd()
    const heading = /^(#{1,4})\s+(.*)$/.exec(line)
    const bullet = /^\s*[-*•]\s+(.*)$/.exec(line)
    const numbered = /^\s*\d+[.)]\s+(.*)$/.exec(line)
    if (heading) {
      flush()
      blocks.push(
        <h3 key={blocks.length} className="mt-4 text-sm font-semibold tracking-wide text-[#0068b5] uppercase first:mt-0">
          {inline(heading[2])}
        </h3>,
      )
    } else if (bullet || numbered) {
      const ordered = Boolean(numbered)
      if (list && list.ordered !== ordered) flush()
      list ??= { ordered, items: [] }
      list.items.push((bullet ?? numbered)![1])
    } else if (line.trim()) {
      flush()
      blocks.push(
        <p key={blocks.length} className="leading-relaxed">
          {inline(line)}
        </p>,
      )
    } else {
      flush()
    }
  }
  flush()
  return <div className="space-y-2 text-sm text-slate-800">{blocks}</div>
}
