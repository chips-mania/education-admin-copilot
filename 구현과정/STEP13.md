# STEP 13 — Contextual Retrieval (V1/V2 Dual Embedding)

> 상태: **완료**  
> 완료일: 2026-06-14  
> 테스트: `tests/test_embed_versions.py` — **3/3 PASSED**  
> 코퍼스: `manuals_exp` 19편, 1,180청크 (평가셋 기준)

---

## 1. 목표

Anthropic Contextual Retrieval 개념 적용:

- **V1**: 본문(Content)만 임베딩 → `embedding_v1`
- **V2**: breadcrumb + Content 임베딩 → `embedding_v2`

동일 코퍼스·모델·검색 알고리즘에서 임베딩 텍스트만 변경해 비교.

---

## 2. 구현 내용

### 2.1 임베딩 텍스트 빌더

| 파일 | 역할 |
|------|------|
| `app/chunking/embed_versions.py` | `build_embed_text_v1`, `build_embed_text_v2` |
| `app/services/embedding_service.py` | `attach_dual_embeddings()` — V1/V2 동시 생성 |

V2 breadcrumb 예시:

```text
교육청행정업무매뉴얼 > 제1편 민원정보공개 > 민원 개요 > 민원의 정의

{본문}
```

### 2.2 DB 스키마

`scripts/setup_schema.sql`:

- `chunks.embedding_v1`, `chunks.embedding_v2` (vector 1024)
- HNSW 인덱스 각각 (`chunks_embedding_v1_idx`, `chunks_embedding_v2_idx`)
- RPC: `match_documents_v1`, `match_documents_v2`
- `match_documents` wrapper — 기본값 V2

### 2.3 검색·RAG

| 파일 | 변경 |
|------|------|
| `app/services/retrieval_service.py` | `embed_version` 파라미터 (`v1` / `v2`) |
| `app/services/rag_service.py` | `ask(..., embed_version=...)` |
| `app/schemas/chat.py` | `ChatRequest.embed_version` (기본 `v2`) |
| `app/api/chat.py` | 요청의 `embed_version` 전달 |

운영 `/chat` 기본값: **V2**, threshold **0.5**, match_count **5**.

### 2.4 코퍼스 적재

| 스크립트 | 역할 |
|----------|------|
| `scripts/ingest_manuals_exp.py` | `manuals_exp` 19편 outline 청킹 + dual embedding 적재 |
| `scripts/chunk_hwpx_outline.py` | 개요2 기준 HWPX 청킹 |
| `scripts/export_embed_versions.py` | V1/V2 임베딩 텍스트보내기 (검수용) |

```powershell
.\venv\Scripts\python.exe scripts/ingest_manuals_exp.py
```

---

## 3. 테스트 결과

| 테스트 | 내용 | 결과 |
|--------|------|------|
| `test_build_embed_text_v1_is_plain_content` | V1 = 본문만 | PASSED |
| `test_build_embed_text_v2_adds_breadcrumb` | V2 breadcrumb prefix | PASSED |
| `test_build_embed_text_v2_from_chunk_uses_structured_fields` | chunk 필드 → V2 텍스트 | PASSED |
| `test_chat_with_embed_version_v1` (STEP10) | API `embed_version=v1` | PASSED |
| `test_step8_retrieval` | V2 기본 검색 (integration) | 2/2 PASSED |

```powershell
.\venv\Scripts\pytest.exe tests/test_embed_versions.py tests/test_step8_retrieval.py -v -s
```

---

## 4. 파이프라인 위치

```text
STEP 12 Frontend MVP
      ↓
STEP 13 Contextual Retrieval (V1/V2)  ← 현재
      ↓
STEP 14 Golden Dataset + Recall 평가
```

---

## 5. 성공 조건 체크리스트

- [x] V1/V2 임베딩 텍스트 분리
- [x] DB dual column + dual RPC
- [x] RetrievalService / RagService embed_version 지원
- [x] `manuals_exp` 19편 dual embedding 적재
- [x] 단위·통합 테스트 통과

---

## 6. 다음 단계

→ **STEP 14**: Golden Dataset + Recall 평가
