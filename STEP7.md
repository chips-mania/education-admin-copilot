# STEP 7 — Supabase 저장

> 상태: **완료**  
> 완료일: 2026-06-08  
> 테스트: `tests/test_step7_supabase_ingest.py` — **2/2 PASSED**

---

## 1. 목표

- `documents` 테이블에 문서 메타데이터 저장
- `chunks` 테이블에 chunk + embedding + metadata 저장
- 파싱된 Chunk 수와 Supabase 저장 수 일치 검증

---

## 2. 구현 내용

### 2.1 파일

| 파일 | 역할 |
|------|------|
| `app/db/repositories.py` | `DocumentRepository` — Repository Pattern |
| `app/db/__init__.py` | public API export |
| `scripts/ingest_documents.py` | Supabase 적재 CLI |
| `tests/test_step7_supabase_ingest.py` | STEP 7 테스트 |

### 2.2 Repository API

| 메서드 | 설명 |
|--------|------|
| `find_document_id_by_file_path()` | `file_path`로 기존 문서 조회 |
| `delete_document()` | 문서 삭제 (chunks cascade) |
| `insert_document()` | documents 테이블 insert |
| `insert_chunks()` | chunks + embedding insert |
| `ingest_embedding_document()` | 전체 적재 (replace 지원) |

### 2.3 적재 흐름

```text
embeddings JSON 읽기
  ↓
file_path로 기존 document 조회
  ↓
있으면 삭제 (replace=true, chunks cascade delete)
  ↓
documents insert → document_id
  ↓
chunks insert (content + metadata + embedding)
  ↓
stored count 검증
```

### 2.4 저장 데이터

**documents**

| 필드 | 예시 |
|------|------|
| `title` | 민원의 종류 |
| `source_type` | manual |
| `file_name` | 01-01-01 민원의 종류.hwpx |
| `file_path` | data/raw/manuals/01-01-01 민원의 종류.hwpx |

**chunks**

| 필드 | 예시 |
|------|------|
| `document_id` | FK |
| `chunk_no` | 1, 2 |
| `content` | chunk 텍스트 |
| `source_type` | manual |
| `metadata` | chapter, section, title 등 |
| `embedding` | vector(1024) |

---

## 3. 입력 / 출력

### 입력

```text
data/processed/embeddings/{source_type}/{파일명}.embeddings.json
```

### Supabase 테이블

- `documents`
- `chunks`

---

## 4. 파이프라인 위치

```text
STEP 6 Embedding
  data/processed/embeddings/manual/01-01-01 민원의 종류.embeddings.json
      ↓
STEP 7 Supabase 저장
  documents + chunks (Supabase)
      ↓
STEP 8 Dense Retrieval (예정)
```

---

## 5. 테스트

### 실행 명령

```bash
.\venv\Scripts\pytest.exe tests/test_step7_supabase_ingest.py -v -s
```

### 테스트 목록

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_ingest_embedding_document_to_supabase` | expected == inserted == stored |
| `test_chunks_exist_in_supabase_after_ingest` | metadata 포함 chunk 저장 확인 |

### 결과

```
2 passed
```

### Ingest CLI

```bash
# 단일 embeddings 파일
.\venv\Scripts\python.exe scripts/ingest_documents.py "data/processed/embeddings/manual/01-01-01 민원의 종류.embeddings.json"

# embeddings 전체
.\venv\Scripts\python.exe scripts/ingest_documents.py
```

### Supabase에서 확인

```sql
select * from documents;
select id, document_id, chunk_no, source_type, metadata from chunks;
select count(*) from chunks;
```

---

## 6. 샘플 적재 결과

| 항목 | 값 |
|------|-----|
| 문서 | 01-01-01 민원의 종류.hwpx |
| expected_chunks | 2 |
| inserted_chunks | 2 |
| stored_chunks | 2 |

---

## 7. 성공 조건 체크리스트

- [x] documents 저장
- [x] chunks + embeddings 저장
- [x] metadata jsonb 저장
- [x] Chunk 수 일치 검증
- [x] Repository Pattern 적용
- [x] 테스트 2건 통과

---

## 8. 다음 단계

→ **STEP 8**: Dense Retrieval (`match_documents` RPC, Top-K=5)
