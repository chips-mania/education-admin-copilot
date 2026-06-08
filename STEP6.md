# STEP 6 — Embedding 생성

> 상태: **완료**  
> 완료일: 2026-06-08  
> 테스트: `tests/test_step6_embedding.py` — **4/4 PASSED**

---

## 1. 목표

- Chunk 텍스트 → 벡터(Embedding) 변환
- 모델: **BAAI/bge-m3** (1024 dimension)
- STEP 7 Supabase 저장 준비

---

## 2. 구현 내용

### 2.1 파일

| 파일 | 역할 |
|------|------|
| `app/services/embedding_service.py` | BGE-M3 임베딩 생성 |
| `app/services/__init__.py` | public API export |
| `scripts/build_embeddings.py` | Embedding CLI |
| `tests/test_step6_embedding.py` | STEP 6 테스트 |

### 2.2 모델 설정

| 항목 | 값 |
|------|-----|
| 모델 | `BAAI/bge-m3` |
| 차원 | **1024** |
| 디바이스 | **CPU** (V1) |
| 정규화 | `normalize_embeddings=True` |

### 2.3 API

```python
from app.services.embedding_service import embed_text, embed_texts, embed_query

# 문서(chunk) 임베딩
vector = embed_text("민원의 종류")        # len=1024

# 배치 임베딩
vectors = embed_texts([chunk1, chunk2])   # 각 len=1024

# 질의 임베딩 (STEP 8 Retrieval용)
query_vector = embed_query("민원 종류 알려줘")
```

질의 임베딩은 BGE-M3 권장 prefix 적용:

```text
Represent this sentence for searching relevant passages: {query}
```

---

## 3. 출력 형식

### 저장 위치

```text
data/processed/embeddings/{source_type}/{파일명}.embeddings.json
```

예시:

```text
data/processed/embeddings/manual/01-01-01 민원의 종류.embeddings.json
```

### JSON 구조

```json
{
  "title": "민원의 종류",
  "source_type": "manual",
  "file_name": "...",
  "file_path": "...",
  "chunks": [
    {
      "chunk_no": 1,
      "content": "...",
      "metadata": { ... },
      "embedding": [0.012, -0.034, ...]
    }
  ]
}
```

---

## 4. 파이프라인 위치

```text
STEP 5 Chunking
  data/processed/chunks/manual/01-01-01 민원의 종류.chunks.json
      ↓
STEP 6 Embedding
  data/processed/embeddings/manual/01-01-01 민원의 종류.embeddings.json
      ↓
STEP 7 Supabase 저장 (예정)
```

---

## 5. 설치 패키지

```bash
pip install sentence-transformers
```

| 패키지 | 용도 |
|--------|------|
| `sentence-transformers` | BGE-M3 모델 로드·추론 |
| `torch` | sentence-transformers 의존성 (CPU) |

첫 실행 시 HuggingFace에서 `BAAI/bge-m3` 모델 자동 다운로드 (~2GB).

---

## 6. 테스트

### 실행 명령

```bash
.\venv\Scripts\pytest.exe tests/test_step6_embedding.py -v -s
```

### 테스트 목록

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_embedding_model_constants` | 모델명, 차원 상수 |
| `test_embed_text_returns_1024_dimension` | 단일 텍스트 → 1024차원 |
| `test_embed_texts_for_sample_chunks` | 샘플 2 chunk 모두 임베딩 |
| `test_embed_query_returns_1024_dimension` | 질의 임베딩 1024차원 |

### 결과

```
4 passed (약 83초, 첫 모델 로드 포함)
```

### Embedding CLI

```bash
# 단일 chunks 파일
.\venv\Scripts\python.exe scripts/build_embeddings.py "data/processed/chunks/manual/01-01-01 민원의 종류.chunks.json"

# data/processed/chunks 전체
.\venv\Scripts\python.exe scripts/build_embeddings.py
```

---

## 7. 성공 조건 체크리스트

- [x] BGE-M3 모델 로드
- [x] Chunk → 1024차원 벡터 변환
- [x] 모든 Chunk 임베딩 생성
- [x] embeddings JSON 저장
- [x] 테스트 4건 통과

---

## 8. 다음 단계

→ **STEP 7**: Supabase 저장 (`documents`, `chunks` + `embedding vector(1024)`)
