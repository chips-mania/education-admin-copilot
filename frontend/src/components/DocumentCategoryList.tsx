import { useState } from 'react'

import type { DocumentItem, SourceType } from '../types/document'
import { SOURCE_TYPE_LABELS } from '../types/document'

interface DocumentCategoryListProps {
  documents: DocumentItem[]
}

const SOURCE_TYPES: SourceType[] = ['manual', 'law', 'regulation', 'interpretation']

export function DocumentCategoryList({ documents }: DocumentCategoryListProps) {
  const [openType, setOpenType] = useState<SourceType | null>(null)

  return (
    <div className="space-y-2">
      {SOURCE_TYPES.map((sourceType) => {
        const items = documents.filter((document) => document.source_type === sourceType)
        const isOpen = openType === sourceType

        return (
          <div key={sourceType} className="rounded-lg border border-slate-200 bg-white">
            <button
              type="button"
              onClick={() => setOpenType(isOpen ? null : sourceType)}
              className="flex w-full items-center justify-between px-3 py-2 text-left text-lg font-medium text-slate-800 hover:bg-slate-50"
            >
              <span>{SOURCE_TYPE_LABELS[sourceType]}</span>
              <span className="text-slate-500">
                {items.length}건 {isOpen ? '▲' : '▼'}
              </span>
            </button>
            {isOpen ? (
              <ul className="border-t border-slate-100 px-3 py-2 text-base text-slate-600">
                {items.length === 0 ? (
                  <li className="py-1 text-slate-400">등록된 문서 없음</li>
                ) : (
                  items.map((item) => (
                    <li key={item.file_name} className="truncate py-1">
                      {item.file_name}
                    </li>
                  ))
                )}
              </ul>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
