// Pure formatting for the interface: money, hours, percentages, times, and readable names for option kinds.
// Every number the pages show goes through here, so rounding and units are consistent across screens.
// Missing values render as an en dash rather than "null" or "NaN".

export const MISSING = '–'

const OPTION_LABELS: Record<string, string> = {
  own_stock: 'Own stock',
  open_order: 'Open order',
  transfer: 'Air transfer',
  emergency_buy: 'Broker (express)',
  new_order: 'New order',
  no_spare_needed: 'No spare needed',
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const MINUS = '\u2212'

export function money(value: number | null | undefined): string {
  if (value === null || value === undefined) return MISSING
  const sign = value < 0 ? MINUS : ''
  return `${sign}$${Math.abs(Math.round(value)).toLocaleString('en-US')}`
}

export function compactMoney(value: number): string {
  if (Math.abs(value) < 1000) return money(value)
  return `${value < 0 ? MINUS : ''}$${(Math.abs(value) / 1000).toFixed(1)}k`
}

export function hours(value: number | null | undefined): string {
  if (value === null || value === undefined) return MISSING
  return `${value.toFixed(1)} h`
}

export function percent(value: number | null | undefined): string {
  if (value === null || value === undefined) return MISSING
  return `${value.toFixed(1)}%`
}

export const DECISION_PREFIX = 'DEC-'

export function optionLabel(kind: string, source = ''): string {
  if (source.startsWith(DECISION_PREFIX)) return 'Approved plan'
  return OPTION_LABELS[kind] ?? kind
}

export function modeLabel(failureMode: string): string {
  const text = failureMode.replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** "2026-07-25 02:00" or "2026-07-25T02:00" -> "25 Jul 02:00". */
export function shortTime(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(value)
  if (!match) return value
  const [, , month, day, hour, minute] = match
  return `${Number(day)} ${MONTHS[Number(month) - 1]} ${hour}:${minute}`
}

/** "2026-07-25" -> "25 Jul". */
export function shortDate(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
  return match ? `${Number(match[3])} ${MONTHS[Number(match[2]) - 1]}` : value
}
