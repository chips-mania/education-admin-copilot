# STEP 9 — LLM 연결

> 상태: **완료**  
> 완료일: 2026-06-08  
> 테스트: `tests/test_step9_llm.py` — **5/5 PASSED**

---

## 1. 목표

- 검색된 Chunk를 근거로 GPT 답변 생성
- 답변 + 출처 반환
- STEP 10 FastAPI `/chat` 연결 준비

---

## 2. 구현 내용

### 2.1 파일

| 파일 | 역할 |
|------|------|
| `app/services/llm_service.py` | OpenAI Chat Completions 호출 |
| `app/services/rag_service.py` | Retrieval + LLM 오케스트레이션 |
| `scripts/chat.py` | RAG CLI |
| `tests/test_step9_llm.py` | STEP 9 테스트 |

### 2.2 모델 설정

| 항목 | 기본값 |
|------|--------|
| 모델 | `gpt-4.1-mini` |
| 환경변수 | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| temperature | 0.2 |

### 2.3 RAG 흐름

```text
사용자 질문
  ↓
RetrievalService.search() — Supabase Top-K
  ↓
LLMService.generate_answer() — 참고 자료 기반 답변
  ↓
답변 + sources 반환
```

### 2.4 반환 필드 (`RagResponse`)

| 필드 | 설명 |
|------|------|
| `query` | 사용자 질문 |
| `answer` | LLM 생성 답변 |
| `sources` | 출처 목록 (file_name, chunk_no, similarity, chapter 등) |

---

## 3. 사용 예시

### CLI

```powershell
.\venv\Scripts\python.exe scripts/chat.py "민원 종류 알려줘"
.\venv\Scripts\python.exe scripts/chat.py "민원 종류 알려줘" --threshold 0.3
```

### Python

```python
from app.services.rag_service import RagService

service = RagService(match_count=5, match_threshold=0.3)
response = service.ask("민원 종류 알려줘")

print(response.answer)
for source in response.sources:
    print(source.file_name, source.similarity)
```

### 출력 예시

```json
{
  "query": "민원 종류 알려줘",
  "answer": "민원은 일반민원과 고충민원으로 구분됩니다...",
  "sources": [
    {
      "file_name": "01-01-01 민원의 종류.hwpx",
      "document_title": "민원의 종류",
      "chunk_no": 1,
      "similarity": 0.619,
      "chapter": "제1편 민원정보공개",
      "section": "민원의 처리"
    }
  ]
}
```

---

## 4. 환경 설정

`.env` 예시:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
```

---

## 5. 파이프라인 위치

```text
STEP 8 Dense Retrieval
      ↓
STEP 9 LLM 연결  ← 현재
      ↓
STEP 10 FastAPI /chat (완료)
```

---

## 6. 성공 조건 체크리스트

- [x] 검색 결과를 LLM 컨텍스트로 전달
- [x] 근거 기반 답변 생성
- [x] 출처(sources) 반환
- [x] 검색 결과 없을 때 fallback 처리
- [x] 테스트 5건 통과

---

## 7. 참고

- 검색 결과가 없으면 OpenAI API를 호출하지 않음
- CLI 첫 실행 시 BGE-M3 로딩으로 20~30초 소요 가능 (STEP 8과 동일)
- STEP 10에서 FastAPI 서버 상주 시 두 번째 요청부터 빨라짐

---

## 8. 다음 단계

→ **STEP 11**: 평가셋 구축
