import type { Source } from '../types/source'

interface SourceCardProps {
  source: Source
}

export function SourceCard({ source }: SourceCardProps) {
  const location = [source.chapter, source.section].filter(Boolean).join(' > ')

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-[17px] text-slate-700">
      <p className="font-medium text-slate-900">
        {source.document_title}
        <span className="ml-2 font-normal text-slate-500">청크 {source.chunk_no}</span>
      </p>
      <p className="mt-1 text-slate-600">{source.file_name}</p>
      {location ? <p className="mt-1 text-slate-500">{location}</p> : null}
      <p className="mt-1 text-blue-700">Similarity {(source.similarity * 100).toFixed(1)}%</p>
    </div>
  )
}
