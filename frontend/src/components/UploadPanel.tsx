import { useRef, useState } from 'react'

import { getErrorMessage } from '../lib/errors'
import { uploadDocument } from '../services/api'

interface UploadPanelProps {
  onUploaded: () => void
}

export function UploadPanel({ onUploaded }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleUpload = async (file: File | undefined) => {
    if (!file) return

    setUploading(true)
    setMessage(null)
    setError(null)

    try {
      const result = await uploadDocument(file)
      setMessage(`${result.title} 업로드 완료 (${result.chunk_count} chunks)`)
      onUploaded()
    } catch (uploadError) {
      setError(getErrorMessage(uploadError, '업로드에 실패했습니다.'))
    } finally {
      setUploading(false)
      if (inputRef.current) {
        inputRef.current.value = ''
      }
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900">공문 업로드</h3>
      <p className="mt-1 text-base text-slate-500">PDF / HWPX</p>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.hwpx"
        className="mt-3 block w-full text-base text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:text-lg file:font-medium file:text-blue-700 hover:file:bg-blue-100"
        disabled={uploading}
        onChange={(event) => void handleUpload(event.target.files?.[0])}
      />
      {uploading ? <p className="mt-2 text-base text-slate-500">업로드 및 인덱싱 중...</p> : null}
      {message ? <p className="mt-2 text-base text-green-700">{message}</p> : null}
      {error ? <p className="mt-2 text-base text-red-600">{error}</p> : null}
    </div>
  )
}
