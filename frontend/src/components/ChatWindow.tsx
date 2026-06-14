import { useState } from 'react'
import type { FormEvent } from 'react'

import { getErrorMessage } from '../lib/errors'
import { sendChat } from '../services/api'
import type { ChatMessage, EmbedVersion } from '../types/chat'
import { ChatMessage as ChatMessageItem } from './ChatMessage'
import { LoadingSpinner } from './LoadingSpinner'

const EMBED_OPTIONS: { value: EmbedVersion; label: string; description: string }[] = [
  {
    value: 'v1',
    label: 'Prototype',
    description: '본문만 임베딩 (embedding_v1)',
  },
  {
    value: 'v2',
    label: 'Contextual Retrieval',
    description: '맥락+본문 임베딩 (embedding_v2)',
  },
]

function createId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: createId(),
      role: 'assistant',
      content: '교육행정 업무에 대해 질문해 주세요. 등록된 매뉴얼·법령을 기반으로 답변합니다.',
    },
  ])
  const [input, setInput] = useState('')
  const [embedVersion, setEmbedVersion] = useState<EmbedVersion>('v2')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const question = input.trim()
    if (!question || loading) return

    const userMessage: ChatMessage = {
      id: createId(),
      role: 'user',
      content: question,
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const response = await sendChat(question, embedVersion)
      setMessages((prev) => [
        ...prev,
        {
          id: createId(),
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
        },
      ])
    } catch (chatError) {
      setError(getErrorMessage(chatError, '답변 생성에 실패했습니다.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="flex h-full min-h-0 flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
        {messages.map((message) => (
          <ChatMessageItem key={message.id} message={message} />
        ))}
        {loading ? <LoadingSpinner /> : null}
        {error ? <p className="text-lg text-red-600">{error}</p> : null}
      </div>

      <form
        onSubmit={(event) => void handleSubmit(event)}
        className="border-t border-slate-200 bg-white px-6 py-4"
      >
        <div className="mb-3 flex flex-wrap gap-2">
          {EMBED_OPTIONS.map((option) => {
            const selected = embedVersion === option.value
            return (
              <button
                key={option.value}
                type="button"
                disabled={loading}
                onClick={() => setEmbedVersion(option.value)}
                className={`rounded-lg border px-3 py-2 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                  selected
                    ? 'border-blue-600 bg-blue-50 text-blue-900'
                    : 'border-slate-300 bg-white text-slate-700 hover:border-slate-400'
                }`}
              >
                <span className="block text-sm font-semibold">{option.label}</span>
                <span className="block text-xs text-slate-500">{option.description}</span>
              </button>
            )
          })}
        </div>
        <div className="flex gap-3">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="예: 민원 종류 알려줘"
            rows={2}
            disabled={loading}
            className="min-h-[52px] flex-1 resize-none rounded-xl border border-slate-300 px-4 py-3 text-lg outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-xl bg-blue-600 px-5 py-3 text-lg font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            전송
          </button>
        </div>
      </form>
    </section>
  )
}
