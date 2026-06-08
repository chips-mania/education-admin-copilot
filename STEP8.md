# STEP 8 — Dense Retrieval 구현

> 상태: **완료**  
> 완료일: 2026-06-08  
> 테스트: `tests/test_step8_retrieval.py` — **2/2 PASSED**

---

## 1. 목표

- 사용자 질문 → 관련 chunk 검색
- Supabase `match_documents` RPC (pgvector cosine similarity)
- Top-K 및 similarity threshold 적용

---

## 2. 구현 내용

### 2.1 파일

| 파일 | 역할 |
|------|------|
| `app/services/retrieval_service.py` | Dense Retrieval 서비스 |
| `scripts/search_documents.py` | 검색 CLI |
| `tests/test_step8_retrieval.py` | STEP 8 테스트 |

### 2.2 검색 설정

| 항목 | 기본값 |
|------|--------|
| Top-K | 5 |
| match_threshold | 0.5 |
| 유사도 | cosine similarity |
| RPC | `match_documents` |

### 2.3 검색 흐름

```text
사용자 질문
  ↓
embed_query() — BGE-M3 + query prefix
  ↓
supabase.rpc("match_documents", {...})
  ↓
Top-K chunk + similarity + document 정보 반환
```

### 2.4 BGE-M3 질의 prefix

```text
Represent this sentence for searching relevant passages: {query}
```

문서 임베딩(`embed_text`)과 질의 임베딩(`embed_query`)을 구분하여 검색 품질 향상.

### 2.5 반환 필드 (`RetrievalResult`)

| 필드 | 설명 |
|------|------|
| `id` | chunk id |
| `document_id` | document id |
| `chunk_no` | chunk 순번 |
| `content` | chunk 텍스트 |
| `source_type` | manual / law / ... |
| `metadata` | chapter, section 등 |
| `similarity` | cosine similarity (0~1) |
| `document_title` | 문서 제목 |
| `file_name` | 원본 파일명 |
| `file_path` | 원본 경로 |

---

## 3. 사용 예시

### Python

```python
from app.services.retrieval_service import RetrievalService

service = RetrievalService(match_count=5, match_threshold=0.5)
response = service.search("민원 종류 알려줘")

for result in response.results:
    print(result.similarity, result.file_name, result.chunk_no)
```

### CLI

```bash
.\venv\Scripts\python.exe scripts/search_documents.py "민원 종류 알려줘"

# 옵션
.\venv\Scripts\python.exe scripts/search_documents.py "민원 종류 알려줘" --top-k 5 --threshold 0.3
```

---

## 4. 테스트

### 실행 명령

```bash
.\venv\Scripts\pytest.exe tests/test_step8_retrieval.py -v -s
```

### 테스트 목록

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_search_returns_results_for_relevant_query` | "민원 종류 알려줘" → 관련 chunk 반환 |
| `test_search_top_result_has_metadata` | Top1 metadata·file_path 정상 |

### 샘플 질의 검증

| 질문 | 기대 결과 |
|------|-----------|
| `민원 종류 알려줘` | `01-01-01 민원의 종류.hwpx` chunk 상위 반환 |

### 결과

```
2 passed
```

---

## 5. 파이프라인 위치

```text
STEP 7 Supabase 저장 (documents + chunks + embeddings)
      ↓
STEP 8 Dense Retrieval  ← 현재
      ↓
STEP 9 LLM 연결 (완료)
```

---

## 6. 성공 조건 체크리스트

- [x] 질문 → embedding 변환
- [x] `match_documents` RPC 호출
- [x] Top-K 결과 반환
- [x] similarity·출처 정보 포함
- [x] 관련 문서 상위 반환 확인
- [x] 테스트 2건 통과

---

## 7. 참고

- 현재 DB에 샘플 문서 1건(2 chunks)만 있어 Top-K=5여도 최대 2건만 반환
- `match_threshold=0.5`는 출발점. 문서 수 증가 후 STEP 12 Baseline에서 튜닝
- 테스트에서는 threshold `0.3` 사용 (소량 데이터 검증용)

---

## 8. 다음 단계

→ **STEP 10**: FastAPI `POST /chat` API 구현
