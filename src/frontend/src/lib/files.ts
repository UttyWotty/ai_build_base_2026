// Reads a browser File or a fetched Blob into the base64 upload the API expects.
// The data URL prefix is stripped, so only the raw base64 goes over the wire.
// Used for inspection photos and for PDF supplier messages.
import type { Upload } from '../api/client'

export function toUpload(blob: Blob, mimeType = blob.type): Promise<Upload> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve({ mime_type: mimeType || 'application/octet-stream', data_base64: String(reader.result).split(',')[1] ?? '' })
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(blob)
  })
}
