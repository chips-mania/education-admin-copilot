export interface Source {
  file_name: string
  document_title: string
  chunk_no: number
  similarity: number
  file_path: string
  source_type: string
  chapter?: string | null
  section?: string | null
}
