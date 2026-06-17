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
    <div className="flex h-screen flex-col overflow-hidden bg-white">
      <header className="flex shrink-0 min-h-[4.5rem] items-center bg-[#1B2B44] px-8 py-6">
        <h1 className="text-2xl font-semibold text-white">교육행정업무 AI Copilot</h1>
      </header>

      <div className="grid min-h-0 flex-1 overflow-hidden lg:grid-cols-[320px_1fr]">
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
