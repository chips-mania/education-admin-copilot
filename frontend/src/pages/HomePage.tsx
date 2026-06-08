import { useCallback, useEffect, useState } from 'react'

import { ChatWindow } from '../components/ChatWindow'
import { KnowledgeBasePanel } from '../components/KnowledgeBasePanel'
import { getErrorMessage } from '../lib/errors'
import { fetchDocuments } from '../services/api'
import type { DocumentListResponse } from '../types/document'

export function HomePage() {
  const [documents, setDocuments] = useState<DocumentListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadDocuments = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchDocuments()
      setDocuments(data)
    } catch (loadError) {
      setError(getErrorMessage(loadError, '문서 목록을 불러오지 못했습니다.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadDocuments()
  }, [loadDocuments])

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <h1 className="text-2xl font-semibold text-slate-900">Education Administration Copilot</h1>
        <p className="mt-1 text-lg text-slate-500">교육행정 RAG 업무지원 시스템</p>
      </header>

      <div className="grid min-h-0 flex-1 lg:grid-cols-[320px_1fr]">
        <KnowledgeBasePanel
          data={documents}
          loading={loading}
          error={error}
          onRefresh={() => void loadDocuments()}
        />
        <ChatWindow />
      </div>
    </div>
  )
}
