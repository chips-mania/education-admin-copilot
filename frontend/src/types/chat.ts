import type { Source } from './source'

export type EmbedVersion = 'v1' | 'v2'

export interface ChatRequest {
  question: string
  embed_version: EmbedVersion
}

export interface ChatResponse {
  answer: string
  sources: Source[]
  embed_version: EmbedVersion
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
}
