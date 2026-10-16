// The confirmation text shown before an operator verdict is recorded on an alert.
// It names the asset and the readable failure mode, so a person sees exactly which machine the note will follow.
// Pure and free of React, so it is tested on its own and the card stays small.
import { modeLabel } from './format'

export function confirmPrompt(assetId: string, failureMode: string): string {
  return `Mark this alert on ${assetId} (${modeLabel(failureMode).toLowerCase()}) as false? `
    + 'Later alerts on this machine and failure mode will carry your note.'
}
