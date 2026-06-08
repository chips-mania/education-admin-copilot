import { useState } from 'react'
import type { FormEvent } from 'react'

import { getErrorMessage } from '../lib/errors'
import { sendChat } from '../services/api'
import type { ChatMessage } from '../types/chat'
import { ChatMessage as ChatMessageItem } from './ChatMessage'
import { LoadingSpinner } from './LoadingSpinner'

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
      const response = await sendChat(question)
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
