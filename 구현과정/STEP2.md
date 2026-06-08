# STEP 2 — Supabase 데이터베이스 스키마 생성

> 상태: **완료**  
> 완료일: 2026-06-08  
> 테스트: `tests/test_step2_schema.py` — **3/3 PASSED**

---

## 1. 목표

- `documents`, `chunks` 테이블 생성
- pgvector HNSW 인덱스 생성
- `metadata` GIN 인덱스 생성 (V2 Metadata Filtering 대비)
- `match_documents()` RPC Function 생성
- Supabase Table Editor / Client 조회 검증

---

## 2. 사전 작업 (사용자)

1. Supabase SQL Editor에서 기존 테이블·함수 **drop 후 재생성**
2. `scripts/setup_schema.sql` 전체 실행

---

## 3. 스키마 설계 변경 이력

초기 설계 대비 아래 항목을 반영하여 스키마를 개선함.

| 항목 | 초기 설계 | 최종 설계 | 변경 이유 |
|------|-----------|-----------|-----------|
| `documents` | `id, title, source_type, created_at` | + `file_name`, `file_path` | chunk → 원본 파일 추적, Citation Accuracy |
| `chunks.work_category` | `text` 컬럼 | 제거 | 유연한 구조 확보 |
| `chunks.page_no` | `integer` 컬럼 | 제거 → `metadata`로 통합 | V2 Metadata Filtering 대비 |
| `chunks.metadata` | 없음 | `jsonb` 추가 | chapter, section, page 등 확장 메타데이터 |
| `source_type` | `text` (제약 없음) | `CHECK` 제약 | 4종 고정값 강제 |
| `match_documents` | Top-K만 | + `match_threshold` | 관련 문서 없을 때 빈 결과 반환 |
| RPC 반환값 | chunk 필드만 | + `document_title`, `file_name`, `file_path` | 출처 표시·JOIN 없이 citation |

---

## 4. source_type 허용 값

| 값 | 대응 폴더 |
|----|-----------|
| `manual` | `data/raw/manuals/` |
| `law` | `data/raw/laws/` |
| `regulation` | `data/raw/regulations/` |
| `interpretation` | `data/raw/interpretations/` |

`documents`, `chunks` 양쪽 테이블에 동일 CHECK 제약 적용.

---

## 5. 테이블 스키마

### 5.1 `documents`

```sql
create table documents (
    id bigint generated always as identity primary key,
    title text not null,
    source_type text not null,
    file_name text not null,
    file_path text not null,
    created_at timestamptz default now(),

    constraint documents_source_type_check check (
        source_type in ('manual', 'law', 'regulation', 'interpretation')
    )
);
```

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | bigint (identity) | PK |
| `title` | text | 문서 제목 |
| `source_type` | text | manual / law / regulation / interpretation |
| `file_name` | text | 파일명 (예: `01-01-01 민원의 종류.hwpx`) |
| `file_path` | text | 상대경로 (예: `data/raw/interpretations/01-01-01 민원의 종류.hwpx`) |
| `created_at` | timestamptz | 생성 시각 |

### 5.2 `chunks`

```sql
create table chunks (
    id bigint generated always as identity primary key,
    document_id bigint not null references documents(id) on delete cascade,
    chunk_no integer not null,
    content text not null,
    source_type text not null,
    metadata jsonb default '{}'::jsonb,
    embedding vector(1024),

    constraint chunks_source_type_check check (
        source_type in ('manual', 'law', 'regulation', 'interpretation')
    )
);
```

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | bigint (identity) | PK |
| `document_id` | bigint | FK → `documents.id` (cascade delete) |
| `chunk_no` | integer | 문서 내 chunk 순번 |
| `content` | text | chunk 텍스트 |
| `source_type` | text | documents와 동일 4종 |
| `metadata` | jsonb | 확장 메타데이터 |
| `embedding` | vector(1024) | BGE-M3 임베딩 (STEP 6) |

### 5.3 `metadata` 예시

```json
{
  "chapter": "제6편 복무",
  "section": "출장",
  "source": "업무매뉴얼",
  "page": 123
}
```

---

## 6. 인덱스

```sql
-- 벡터 유사도 검색 (cosine)
create index chunks_embedding_idx
    on chunks using hnsw (embedding vector_cosine_ops);

-- V2 Metadata Filtering 대비
create index chunks_metadata_idx
    on chunks using gin (metadata);
```

---

## 7. RPC Function — `match_documents`

```sql
create or replace function match_documents(
    query_embedding vector(1024),
    match_count int default 5,
    match_threshold float default 0.5
)
returns table (
    id bigint,
    document_id bigint,
    chunk_no integer,
    content text,
    source_type text,
    metadata jsonb,
    similarity float,
    document_title text,
    file_name text,
    file_path text
)
```

### 파라미터

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `query_embedding` | — | 질문 벡터 (1024차원) |
| `match_count` | 5 | Top-K |
| `match_threshold` | 0.5 | cosine similarity 하한 (미만 제외) |

### 동작

1. `chunks` ↔ `documents` JOIN
2. `embedding`이 null이 아닌 row만 대상
3. `similarity = 1 - (embedding <=> query_embedding)` 계산
4. `similarity > match_threshold` 인 row만 반환
5. similarity 내림차순 정렬 후 `match_count`개 제한

### Python 호출 예시 (STEP 8)

```python
client.rpc(
    "match_documents",
    {
        "query_embedding": query_vector,
        "match_count": 5,
        "match_threshold": 0.5,
    },
).execute()
```

---

## 8. 생성·수정 파일

| 파일 | 설명 |
|------|------|
| `scripts/setup_schema.sql` | drop + create 전체 SQL |
| `tests/test_step2_schema.py` | STEP 2 스키마·RPC 테스트 |
| `구현계획서.md` | STEP 2 섹션 스키마 반영 |

---

## 9. 데이터 저장 예시 (STEP 7 참고)

```python
client.table("documents").insert({
    "title": "민원의 종류",
    "source_type": "interpretation",
    "file_name": "01-01-01 민원의 종류.hwpx",
    "file_path": "data/raw/interpretations/01-01-01 민원의 종류.hwpx",
}).execute()

client.table("chunks").insert({
    "document_id": 1,
    "chunk_no": 1,
    "content": "...",
    "source_type": "interpretation",
    "metadata": {
        "chapter": "제1편 민원",
        "section": "민원의 종류",
    },
    "embedding": vector,
}).execute()
```

---

## 10. 테스트

### 실행 명령

```bash
.\venv\Scripts\pytest.exe tests/test_step2_schema.py -v -s
```

### 테스트 목록

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_documents_table_exists` | `documents` 테이블 및 `file_name`, `file_path` 컬럼 조회 |
| `test_chunks_table_exists` | `chunks` 테이블 및 `metadata` 컬럼 조회 |
| `test_match_documents_rpc_exists` | RPC 호출 가능 여부 (빈 결과 허용) |

### 결과

```
tests/test_step2_schema.py::test_documents_table_exists PASSED
tests/test_step2_schema.py::test_chunks_table_exists PASSED
tests/test_step2_schema.py::test_match_documents_rpc_exists PASSED

3 passed
```

---

## 11. 성공 조건 체크리스트

- [x] `documents` 테이블 생성 완료
- [x] `chunks` 테이블 생성 완료
- [x] `source_type` CHECK 제약 적용
- [x] `metadata jsonb` 컬럼 적용
- [x] HNSW 벡터 인덱스 생성
- [x] GIN metadata 인덱스 생성
- [x] `match_documents` RPC 생성 (`match_threshold` 포함)
- [x] RPC가 `documents` JOIN 정보 반환
- [x] 테스트 3건 통과

---

## 12. 주의사항

- `match_threshold` 기본값 `0.5`는 출발점. STEP 8/12 Baseline 측정 시 실제 분포에 맞게 조정 필요.
- 스키마 재생성 시 기존 데이터는 삭제됨 (현재 데이터 없음 → 문제 없음).
- `embedding` 차원은 BGE-M3 기준 **1024** 고정.

---

## 13. 다음 단계

→ **STEP 3**: HWPX 문서 파싱 (`hwpx_parser.py`)  
→ 테스트 파일: `data/raw/interpretations/01-01-01 민원의 종류.hwpx`
