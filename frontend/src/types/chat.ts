import type { Source } from './source'

export interface ChatResponse {
  answer: string
  sources: Source[]
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
}
