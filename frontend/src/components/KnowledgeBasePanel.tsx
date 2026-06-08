import type { DocumentListResponse } from '../types/document'
import { SOURCE_TYPE_LABELS } from '../types/document'
import type { SourceType } from '../types/document'
import { DocumentCategoryList } from './DocumentCategoryList'
import { UploadPanel } from './UploadPanel'

interface KnowledgeBasePanelProps {
  data: DocumentListResponse | null
  loading: boolean
  error: string | null
  onRefresh: () => void
}

const SOURCE_TYPES: SourceType[] = ['manual', 'law', 'regulation', 'interpretation']

export function KnowledgeBasePanel({ data, loading, error, onRefresh }: KnowledgeBasePanelProps) {
  return (
    <aside className="flex h-full flex-col gap-4 border-r border-slate-200 bg-slate-50 p-4">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">RAG Knowledge Base</h2>
        <p className="mt-1 text-base text-slate-500">등록된 문서 기반 검색·답변</p>
      </div>

      {loading ? <p className="text-lg text-slate-500">문서 목록 불러오는 중...</p> : null}
      {error ? <p className="text-lg text-red-600">{error}</p> : null}

      {data ? (
        <>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="space-y-2 text-lg">
              {SOURCE_TYPES.map((sourceType) => (
                <div key={sourceType} className="flex items-center justify-between text-slate-700">
                  <span>{SOURCE_TYPE_LABELS[sourceType]}</span>
                  <span className="font-semibold text-slate-900">
                    {data.summary.by_source_type[sourceType].toLocaleString()}건
                  </span>
                </div>
              ))}
            </div>
            <div className="mt-4 border-t border-slate-100 pt-3 text-lg">
              <div className="flex items-center justify-between font-medium text-slate-800">
                <span>총 문서</span>
                <span>{data.summary.total_documents.toLocaleString()}건</span>
              </div>
              <div className="mt-2 flex items-center justify-between font-medium text-slate-800">
                <span>총 Chunk</span>
                <span>{data.summary.total_chunks.toLocaleString()}</span>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">최근 등록 문서</h3>
            <ul className="mt-2 space-y-1 text-base text-slate-600">
              {data.recent.length === 0 ? (
                <li className="text-slate-400">등록된 문서 없음</li>
              ) : (
                data.recent.map((item) => (
                  <li key={item.file_name} className="truncate">
                    · {item.title}
                  </li>
                ))
              )}
            </ul>
          </div>

          <DocumentCategoryList documents={data.documents} />
        </>
      ) : null}

      <div className="mt-auto">
        <UploadPanel onUploaded={onRefresh} />
      </div>
    </aside>
  )
}
