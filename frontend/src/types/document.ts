export type SourceType = 'manual' | 'law' | 'regulation' | 'interpretation'

export interface DocumentSummaryStats {
  total_documents: number
  total_chunks: number
  by_source_type: Record<SourceType, number>
}

export interface DocumentItem {
  title: string
  file_name: string
  source_type: SourceType
  chunk_count: number
  file_path?: string
  created_at?: string
}

export interface DocumentListResponse {
  summary: DocumentSummaryStats
  recent: DocumentItem[]
  documents: DocumentItem[]
}

export interface DocumentUploadResponse {
  title: string
  file_name: string
  source_type: SourceType
  document_id: number
  chunk_count: number
}

export const SOURCE_TYPE_LABELS: Record<SourceType, string> = {
  manual: '업무매뉴얼',
  law: '법령',
  regulation: '행정규칙',
  interpretation: '법령해석례',
}
