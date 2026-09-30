// Streams one copilot run from POST /api/agent/stream and hands each event to a callback as it arrives.
// The browser's fetch body reader delivers chunks; the pure SSE parser turns them into JSON events.
// The returned promise resolves when the server closes the stream; network failures reject it.
import { toError } from './client'
import { parseSse } from './sse'
import type { AgentEvent, AgentMode } from './types'

export async function streamAgent(question: string, asOf: string, onEvent: (event: AgentEvent) => void,
                                  mode: AgentMode = 'single', signal?: AbortSignal): Promise<void> {
  const response = await fetch('/api/agent/stream', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ question, as_of: asOf, mode }),
    signal,
  })
  if (!response.ok || !response.body) throw await toError(response)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    const parsed = parseSse(buffer + decoder.decode(value, { stream: true }))
    buffer = parsed.rest
    parsed.events.forEach((data) => onEvent(JSON.parse(data) as AgentEvent))
  }
}
