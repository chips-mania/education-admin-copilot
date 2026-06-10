import axios from 'axios'

import type { ChatResponse } from '../types/chat'
import type { DocumentListResponse, DocumentUploadResponse, SourceType } from '../types/document'

const baseURL = import.meta.env.VITE_API_URL ?? ''

export const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export async function fetchDocuments(): Promise<DocumentListResponse> {
  const response = await api.get<DocumentListResponse>('/documents')
  return response.data
}

export async function sendChat(question: string): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>('/chat', { question })
  return response.data
}

export async function uploadDocument(
  file: File,
  sourceType: SourceType = 'manual',
): Promise<DocumentUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('source_type', sourceType)

  const response = await api.post<DocumentUploadResponse>('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 0,
  })
  return response.data
}
