# STEP 5 — Chunking (문서 분할)

> 상태: **완료**  
> 완료일: 2026-06-08  
> 테스트: `tests/test_step5_chunking.py` — **3/3 PASSED**  
> 방식: **커스텀 Structure-Aware Chunker** (표 보존 중심)

---

## 1. 목표

- 파싱된 문서(`data/processed/`)를 검색 가능한 단위로 분할
- 문맥 손실 최소화
- HTML 표 구조 보존 (표 중간 분할 금지)
- chunk별 metadata 유지 → STEP 7 Supabase 적재 준비

---

## 2. Chunking 방식 선택

### 검토한 방식

| 방식 | 채택 | 이유 |
|------|------|------|
| 단순 토큰 슬라이싱 (`text[:1000]`) | ❌ | 표·문단 중간에서 잘림, 품질 낮음 |
| LangChain `RecursiveCharacterTextSplitter` | ❌ | 범용 라이브러리, 표 구조 미보장 |
| Semantic Chunker | ❌ | V1에서 구현·속도 부담 |
| **Structure-Aware (커스텀)** | ✅ | 업무매뉴얼·법령 문서에 적합, 표 보존 가능 |

### V1 적용 규칙

| 규칙 | 반영 | 비고 |
|------|------|------|
| 제목 유지 | ⚠️ 부분 | chunk1에 제목+표 함께 포함, metadata에 `title` |
| 표 절대 분리 금지 | ✅ | `<table>` atomic block |
| 리스트 절대 분리 금지 | ❌ | V2+ 보강 예정 |
| 토큰 한도 초과 시만 분리 | ✅ | 700 token 기준 (구현계획서) |
| metadata 유지 | ✅ | 모든 chunk에 동일 metadata 복사 |

---

## 3. 구현 내용

### 3.1 파일

| 파일 | 역할 |
|------|------|
| `app/chunking/chunk_service.py` | Chunking 핵심 로직 |
| `app/chunking/__init__.py` | public API export |
| `scripts/chunk_documents.py` | Chunking CLI |
| `tests/test_step5_chunking.py` | STEP 5 테스트 |

### 3.2 정책

| 항목 | 값 |
|------|-----|
| Chunk Size | **700 tokens** |
| Overlap | **100 tokens** |
| Tokenizer | `tiktoken` (`cl100k_base`) |

### 3.3 알고리즘

```text
1. content → atomic block 분리
   - <table>...</table>  → 통째로 1 block (분할 금지)
   - 나머지 텍스트       → \n\n 문단 단위 block

2. block들을 순서대로 묶어 chunk 생성
   - 누적 token ≤ 700 이면 같은 chunk에 추가
   - 초과 시 새 chunk 시작

3. overlap 적용 (조건부)
   - 일반 텍스트 chunk 사이: 100 token overlap
   - 표가 포함된 chunk 이후: overlap 미적용 (표 잔여 조각 방지)

4. block 단독이 700 token 초과 시 (대형 표 등)
   - 해당 block을 단독 chunk로 유지 (강제 분할 안 함)
```

### 3.4 사용 라이브러리

```bash
pip install tiktoken
```

- **tiktoken**: 토큰 수 계산 전용
- LangChain 등 별도 Chunker 라이브러리 **미사용**

---

## 4. 출력 형식

### 4.1 Chunk 단위

```json
{
  "chunk_no": 1,
  "content": "...",
  "metadata": {
    "title": "민원의 종류",
    "source": "업무매뉴얼",
    "chapter": "제1편 민원정보공개",
    "section": "민원의 처리",
    "section_no": "1",
    "item_no": "1"
  }
}
```

### 4.2 저장 위치

```text
data/processed/chunks/{source_type}/{파일명}.chunks.json
```

예시:

```text
data/processed/chunks/manual/01-01-01 민원의 종류.chunks.json
```

### 4.3 샘플 결과 (`01-01-01 민원의 종류`)

| Chunk | Tokens | 내용 |
|-------|--------|------|
| chunk 1 | ~578 | 제목(`\| 민원의 종류 \|`) + **HTML 표 전체** (법정민원~고충민원) |
| chunk 2 | ~135 | `※ 복합민원` 주석 |

→ Structure-Aware에 가까운 분리: **표 = chunk1, 후속 설명 = chunk2**

---

## 5. 파이프라인 위치

```text
STEP 3 파싱
  data/processed/manual/01-01-01 민원의 종류.json
      ↓
STEP 5 Chunking
  data/processed/chunks/manual/01-01-01 민원의 종류.chunks.json
      ↓
STEP 6 Embedding (예정)
STEP 7 Supabase 저장 (예정)
```

---

## 6. 이슈 및 해결

### 이슈 1: 표 중간에서 chunk 분할

- **증상**: chunk1에 표 일부, chunk2에 `</td>질의민원...` 잔여 조각
- **원인**: 표 chunk 이후 100 token overlap이 표 내부 텍스트를 다음 chunk에 복사
- **해결**: `_contains_table()` 체크 → 표 chunk 다음 overlap **미적용**

### 이슈 2: chunk CLI 경로 오류

- **증상**: `relative_to(PROCESSED_DIR)` 실패 (상대경로 입력 시)
- **해결**: `parsed_path.resolve()` 후 relative 계산

---

## 7. 테스트

### 실행 명령

```bash
.\venv\Scripts\pytest.exe tests/test_step5_chunking.py -v -s
```

### 테스트 목록

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_split_preserves_html_table_as_single_block` | 표가 1개 atomic block으로 분리 |
| `test_chunk_document_keeps_table_intact` | chunk 내 표 완전 보존, chunk2에 표 없음 |
| `test_chunk_output_format` | `chunk_no`, `content`, `metadata` 필드 구조 |

### 결과

```
tests/test_step5_chunking.py::test_split_preserves_html_table_as_single_block PASSED
tests/test_step5_chunking.py::test_chunk_document_keeps_table_intact PASSED
tests/test_step5_chunking.py::test_chunk_output_format PASSED

3 passed
```

### Chunking CLI

```bash
# 단일 parsed JSON
.\venv\Scripts\python.exe scripts/chunk_documents.py "data/processed/manual/01-01-01 민원의 종류.json"

# data/processed 전체 (chunks/ 제외)
.\venv\Scripts\python.exe scripts/chunk_documents.py
```

---

## 8. 품질 평가

| 항목 | 상태 | 비고 |
|------|------|------|
| Chunking 동작 | ✅ | 2 chunk 생성 확인 |
| 표 보존 | ✅ | chunk1에 표 전체 |
| metadata 유지 | ✅ | chapter/section/title |
| Structure-Aware | ✅ | 구조 단위 분리 (표 / 주석) |
| 리스트 보존 | ⏳ | V2+ |
| Retrieval 품질 | ⏳ | STEP 8 이후 검증 |

---

## 9. V2+ 개선 후보

- 리스트 블록 atomic 처리 (분할 금지)
- 모든 chunk에 `제1편 > 민원의 처리 > 민원의 종류` 제목 prefix
- chunk size 700 → 1000 조정 실험
- 절차도(OCR) 블록 보존 (STEP 4 연계)

---

## 10. 성공 조건 체크리스트

- [x] Chunk Size 700 token 적용
- [x] Overlap 100 token 적용 (조건부)
- [x] HTML table atomic block 처리
- [x] 표 chunk 이후 overlap 방지
- [x] metadata chunk별 유지
- [x] chunks JSON 저장
- [x] 테스트 3건 통과

---

## 11. 다음 단계

→ **STEP 6**: Embedding 생성 (BAAI/bge-m3, vector 1024)
