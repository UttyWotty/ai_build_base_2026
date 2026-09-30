// Pure arithmetic on the demo clock's "YYYY-MM-DDTHH:MM" strings: advancing by hours and formatting for display.
// Times are treated as UTC wall-clock values, exactly as the backend states them, so no local time zone creeps in.
// Live mode uses these on every tick.

const PAD = 2
const MS_PER_HOUR = 3_600_000
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function toDate(clock: string): Date {
  return new Date(`${clock.slice(0, 16)}:00Z`)
}

function pad(n: number): string {
  return String(n).padStart(PAD, '0')
}

export function addHours(clock: string, hours: number): string {
  const d = new Date(toDate(clock).getTime() + hours * MS_PER_HOUR)
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`
}

export function longClock(clock: string): string {
  const d = toDate(clock)
  return `${DAYS[d.getUTCDay()]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}, ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`
}

export function isAfter(a: string, b: string): boolean {
  return toDate(a).getTime() > toDate(b).getTime()
}
