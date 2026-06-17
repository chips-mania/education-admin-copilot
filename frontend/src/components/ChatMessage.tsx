import type { ChatMessage as ChatMessageType } from '../types/chat'
import { SourceCard } from './SourceCard'

interface ChatMessageProps {
  message: ChatMessageType
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-[19px] leading-8 shadow-sm ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-slate-100 text-slate-800'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {!isUser && message.sources && message.sources.length > 0 ? (
          <div className="mt-3 space-y-2 border-t border-slate-200 pt-3">
            <p className="text-[17px] font-semibold uppercase tracking-wide text-slate-500">출처</p>
            {message.sources.map((source) => (
              <SourceCard key={`${source.file_name}-${source.chunk_no}`} source={source} />
            ))}
          </div>
        ) : null}
      </div>
    </div>
  )
}
