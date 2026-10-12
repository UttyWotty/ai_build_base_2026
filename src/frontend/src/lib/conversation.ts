// Builds the question sent to the agent for one turn of an in-place conversation about a part of the app.
// The agent run itself is stateless, so each turn carries the topic and the last few turns as plain text.
// Earlier answers are trimmed so a long conversation never grows the prompt without limit.

export interface Turn {
  question: string
  answer: string
}

// How many earlier turns ride along with a new question, and how much of each earlier answer.
export const HISTORY_TURNS = 3
export const ANSWER_CHARS = 800
const ELLIPSIS = '...'

export function trimAnswer(answer: string, limit: number = ANSWER_CHARS): string {
  const text = answer.trim()
  return text.length <= limit ? text : `${text.slice(0, limit - ELLIPSIS.length).trimEnd()}${ELLIPSIS}`
}

export function composeQuestion(topic: string, history: Turn[], question: string): string {
  const earlier = history.slice(-HISTORY_TURNS)
  const parts = [`Topic: ${topic.trim()}`]
  if (earlier.length) {
    parts.push('Earlier in this conversation:')
    earlier.forEach((t) => parts.push(`Q: ${t.question.trim()}\nA: ${trimAnswer(t.answer)}`))
  }
  parts.push(`Question: ${question.trim()}`)
  return parts.join('\n\n')
}
