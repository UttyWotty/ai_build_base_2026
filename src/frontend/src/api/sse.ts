// Pure parser for server-sent events: turns streamed text chunks into complete "data:" payloads.
// Chunks can split an event anywhere, so the parser keeps the unfinished tail until its blank-line terminator arrives.
// It has no network code, so it is unit-tested directly.

const EVENT_SEPARATOR = '\n\n'
const DATA_PREFIX = 'data: '

export interface SseParse {
  events: string[]
  rest: string
}

export function parseSse(buffer: string): SseParse {
  const blocks = buffer.split(EVENT_SEPARATOR)
  const rest = blocks.pop() ?? ''
  const events = blocks
    .flatMap((block) => block.split('\n'))
    .filter((line) => line.startsWith(DATA_PREFIX))
    .map((line) => line.slice(DATA_PREFIX.length))
  return { events, rest }
}
