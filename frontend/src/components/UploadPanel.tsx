import { useEffect, useReducer, useRef, useState } from 'react'

import { formatDuration } from '../lib/format'
import { getErrorMessage } from '../lib/errors'
import { uploadDocument } from '../services/api'

interface UploadPanelProps {
  onUploaded: () => void
}

type FileUploadStatus = 'pending' | 'processing' | 'done' | 'error'

interface FileUploadItem {
  id: string
  name: string
  status: FileUploadStatus
  elapsedMs?: number
  chunkCount?: number
  title?: string
  error?: string
}

function createUploadItem(file: File): FileUploadItem {
  return {
    id: `${file.name}-${file.size}-${file.lastModified}`,
    name: file.name,
    status: 'pending',
  }
}

export function UploadPanel({ onUploaded }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [items, setItems] = useState<FileUploadItem[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [processingStartedAt, setProcessingStartedAt] = useState<number | null>(null)
  const [, refreshElapsed] = useReducer((count: number) => count + 1, 0)
  const [summary, setSummary] = useState<string | null>(null)

  const totalCount = items.length
  const completedCount = items.filter((item) => item.status === 'done' || item.status === 'error').length
  const successCount = items.filter((item) => item.status === 'done').length
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0

  const currentItem = currentIndex > 0 ? items[currentIndex - 1] : undefined
  const elapsedMs =
    uploading && processingStartedAt && currentItem?.status === 'processing'
      ? Date.now() - processingStartedAt
      : 0

  useEffect(() => {
    if (!uploading || processingStartedAt === null) {
      return
    }

    const timer = window.setInterval(() => {
      refreshElapsed()
    }, 1000)

    return () => window.clearInterval(timer)
  }, [uploading, processingStartedAt])

  const updateItem = (id: string, patch: Partial<FileUploadItem>) => {
    setItems((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)))
  }

  const handleUploadMany = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return

    const files = Array.from(fileList)
    const queue = files.map(createUploadItem)

    setUploading(true)
    setSummary(null)
    setItems(queue)
    setCurrentIndex(0)
    setProcessingStartedAt(null)

    let succeeded = 0

    for (let index = 0; index < files.length; index += 1) {
      const file = files[index]
      const item = queue[index]
      const startedAt = Date.now()

      setCurrentIndex(index + 1)
      setProcessingStartedAt(startedAt)
      updateItem(item.id, { status: 'processing' })

      try {
        const result = await uploadDocument(file)
        const elapsed = Date.now() - startedAt
        updateItem(item.id, {
          status: 'done',
          elapsedMs: elapsed,
          chunkCount: result.chunk_count,
          title: result.title,
        })
        succeeded += 1
      } catch (uploadError) {
        const elapsed = Date.now() - startedAt
        updateItem(item.id, {
          status: 'error',
          elapsedMs: elapsed,
          error: getErrorMessage(uploadError, '업로드에 실패했습니다.'),
        })
      }
    }

    setProcessingStartedAt(null)
    setUploading(false)
    setSummary(`${succeeded} / ${files.length}개 파일 처리 완료`)
    onUploaded()

    if (inputRef.current) {
      inputRef.current.value = ''
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-lg font-semibold text-slate-900">문서 업로드</h3>
      <p className="mt-1 text-base text-slate-500">PDF / HWPX · 여러 파일 선택 가능</p>
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.hwpx"
        className="mt-3 block w-full text-base text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:text-lg file:font-medium file:text-blue-700 hover:file:bg-blue-100"
        disabled={uploading}
        onChange={(event) => void handleUploadMany(event.target.files)}
      />

      {uploading && totalCount > 0 ? (
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between text-base text-slate-700">
            <span>
              {currentIndex} / {totalCount} 처리 중
            </span>
            <span>{progressPercent}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-blue-600 transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          {currentItem?.status === 'processing' ? (
            <p className="text-base text-slate-500">
              {currentItem.name} · 경과 {formatDuration(elapsedMs)}
            </p>
          ) : null}
        </div>
      ) : null}

      {items.length > 0 ? (
        <ul className="mt-4 max-h-48 space-y-2 overflow-y-auto">
          {items.map((item, index) => (
            <li
              key={item.id}
              className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-base text-slate-700"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="truncate">
                  {index + 1}. {item.name}
                </span>
                <span className="shrink-0 font-medium">
                  {item.status === 'pending' ? '대기' : null}
                  {item.status === 'processing' ? '처리 중' : null}
                  {item.status === 'done' ? '완료' : null}
                  {item.status === 'error' ? '실패' : null}
                </span>
              </div>
              {item.status === 'done' && item.elapsedMs !== undefined ? (
                <p className="mt-1 text-base text-green-700">
                  {item.title} · {item.chunkCount} chunks · {formatDuration(item.elapsedMs)}
                </p>
              ) : null}
              {item.status === 'error' ? (
                <p className="mt-1 text-base text-red-600">
                  {item.error}
                  {item.elapsedMs !== undefined ? ` · ${formatDuration(item.elapsedMs)}` : null}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      {summary && !uploading ? (
        <p className="mt-3 text-base text-slate-700">
          {summary}
          {successCount < totalCount ? ' (일부 실패)' : ''}
        </p>
      ) : null}
    </div>
  )
}
