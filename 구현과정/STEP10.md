# STEP 10 — FastAPI API 구현

> 상태: **완료**  
> 완료일: 2026-06-08  
> 테스트: `tests/test_step10_api.py` — **4/4 PASSED**

---

## 1. 목표

- RAG 파이프라인을 HTTP API로 노출
- `POST /chat` — 답변 + 출처 반환
- Swagger UI 제공

---

## 2. 구현 내용

### 2.1 파일

| 파일 | 역할 |
|------|------|
| `app/main.py` | FastAPI 앱 진입점 |
| `app/api/chat.py` | `POST /chat` |
| `app/api/health.py` | `GET /health` |
| `app/schemas/chat.py` | Request/Response 스키마 |
| `tests/test_step10_api.py` | STEP 10 테스트 |

### 2.2 Endpoint

| Method | Path | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 확인 |
| POST | `/chat` | RAG 질의응답 |

### 2.3 Request / Response

**Request**

```json
{
  "question": "민원 종류 알려줘"
}
```

**Response**

```json
{
  "answer": "민원은 일반민원과 고충민원으로 구분됩니다...",
  "sources": [
    {
      "file_name": "01-01-01 민원의 종류.hwpx",
      "document_title": "민원의 종류",
      "chunk_no": 1,
      "similarity": 0.619,
      "file_path": "data/raw/manuals/01-01-01 민원의 종류.hwpx",
      "source_type": "manual",
      "chapter": "제1편 민원정보공개",
      "section": "민원의 처리"
    }
  ]
}
```

### 2.4 내부 흐름

```text
POST /chat
  ↓
RagService.ask()
  ↓
embed_query() → match_documents RPC → GPT 답변
  ↓
answer + sources 반환
```

`RagService`는 `@lru_cache`로 싱글톤 처리되어 서버 상주 시 BGE-M3 모델이 메모리에 유지됩니다.

---

## 3. 사용 예시

### 서버 실행

```powershell
.\venv\Scripts\uvicorn.exe app.main:app --reload
```

### Swagger UI

브라우저: `http://localhost:8000/docs`

### curl

```powershell
curl -X POST http://localhost:8000/chat `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"민원 종류 알려줘\"}"
```

### Python requests

```python
import requests

response = requests.post(
    "http://localhost:8000/chat",
    json={"question": "민원 종류 알려줘"},
)
print(response.json()["answer"])
```

---

## 4. 파이프라인 위치

```text
STEP 9 LLM 연결
      ↓
STEP 10 FastAPI /chat  ← 현재
      ↓
STEP 11 평가셋 구축 (예정)
```

---

## 5. 성공 조건 체크리스트

- [x] Swagger UI (`/docs`) 정상 표시
- [x] `GET /health` 정상 응답
- [x] `POST /chat` 정상 응답
- [x] answer + sources 반환
- [x] 테스트 4건 통과

---

## 6. 참고

- 첫 `/chat` 요청: BGE-M3 cold start로 20~30초 소요 가능
- 이후 요청: 임베딩 + 검색 + LLM만 수행 (수 초)
- CLI `scripts/chat.py`와 동일한 RAG 파이프라인 사용

---

## 7. 다음 단계

→ **STEP 11**: 평가셋 구축
