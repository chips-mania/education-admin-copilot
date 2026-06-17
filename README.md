# 교육행정업무 AI Copilot

교육청 행정업무 매뉴얼을 기반으로 **근거 있는 질의응답**을 제공하는 RAG(Retrieval-Augmented Generation) Copilot입니다.  
본문만 임베딩하는 **V1(Prototype)** 과 breadcrumb 맥락을 추가한 **V2(Contextual Retrieval)** 를 동일 골든 데이터셋으로 비교·검증했습니다.

---

## 목차

- [배경 및 문제](#배경-및-문제)
- [해결 접근](#해결-접근)
- [시스템 아키텍처](#시스템-아키텍처)
- [기술 스택](#기술-스택)
- [데이터 및 청킹](#데이터-및-청킹)
- [V1 vs V2 임베딩](#v1-vs-v2-임베딩)
- [평가 결과](#평가-결과)
- [프로젝트 구조](#프로젝트-구조)
- [시작하기](#시작하기)
- [API](#api)
- [평가 실행](#평가-실행)
- [구현 문서](#구현-문서)
- [향후 계획](#향후-계획)

---

## 배경 및 문제

교육행정 실무에서는 다음과 같은 어려움이 있습니다.

- 업무매뉴얼 분량이 방대하고 **편·장·절 구조**가 복잡함
- 유사한 행정 용어(계약, 지출, 신청 등)가 **여러 편에 반복**됨
- 신규 직원은 어떤 규정을 참고해야 하는지 파악하기 어려움
- 매뉴얼·법령·지침을 **여러 시스템**에서 따로 검색해야 함

초기 **V1(본문만 임베딩)** 으로 운영 시, 90문항 골든셋 평가에서 다음 한계가 드러났습니다.

| 문제 | V1 증상 |
|------|---------|
| 맥락 부재 | 유사 본문 청크 간 혼동, 정답이 Top-10 밖으로 밀림 (miss 18/90) |
| 상황형 질문 | 키워드 없이 상황만 설명 시 Recall@1 **23.3%** |
| 실사용 질문 | Human 작성 질문 Recall@1 **24.4%** (AI 53.3% 대비 큰 격차) |
| 순위 품질 | Recall@10 80%이나 Recall@1 38.9% → **찾긴 찾지만 1위가 아님** |

---

## 해결 접근

[Anthropic Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval) 개념을 적용해 **V2**를 도입했습니다.

- V1: 청크 **본문(Content)** 만 임베딩 → `embedding_v1`
- V2: **breadcrumb(편 > 장 > 절) + 본문** 임베딩 → `embedding_v2`

임베딩 모델·벡터 DB·청킹·LLM·프롬프트는 동일하게 유지하고, **임베딩 텍스트만** 변경해 검색 성능 차이를 측정했습니다.

---

## 시스템 아키텍처

```text
[Frontend] React + Vite (localhost:5173)
      │  GET /documents, POST /chat, POST /documents/upload
      ▼
[Backend]  FastAPI (localhost:8000)
      │
      ├─ embed_query()        BGE-M3
      ├─ match_documents_v1/v2   Supabase pgvector RPC
      └─ LLMService           GPT-4.1 Mini
      ▼
[Supabase]  documents + chunks (embedding_v1, embedding_v2)
```

### RAG 파이프라인 (`POST /chat`)

```text
질문
  → BGE-M3 임베딩
  → match_documents_v2 RPC (Top-K, cosine similarity)
  → 검색 청크를 LLM 컨텍스트로 전달
  → GPT-4.1 Mini 답변 생성
  → answer + sources 반환
```

운영 기본값: **V2**, `match_count=5`, `match_threshold=0.5`

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Backend | FastAPI, Uvicorn |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS |
| Database | Supabase (PostgreSQL + pgvector) |
| Embedding | BAAI/bge-m3 (1024 dim) |
| LLM | OpenAI GPT-4.1 Mini |
| 문서 파싱 | python-hwpx, PyMuPDF |
| 청킹 | 개요2(Outline) 구조 기반 + tiktoken |
| 평가 | 골든 데이터셋 90문항, Recall@k, MRR |

---

## 데이터 및 청킹

### 코퍼스

| 항목 | 값 |
|------|-----|
| 대상 | 교육청 행정업무 매뉴얼 (`data/raw/manuals_exp/`) |
| 편 수 | 19편 |
| 총 청크 | 1,180 (heading-only 152개는 평가 풀에서 제외) |

### 청킹 방식 (개요2 기준)

```text
대단원(개요1 / chapter)
 └ 소제목(개요2 / heading)  ← 청크 1개
     └ 내용(개요3,4 / content)
```

고정 토큰 슬라이싱(700 token)이 아니라 **문서 구조(소제목) 단위**로 분할합니다.  
문서 업로드 경로(`POST /documents/upload`)는 별도로 700 token / 100 overlap 청킹을 사용합니다.

---

## V1 vs V2 임베딩

**V1 예시** (본문만)

```text
전기·가스·수도 등의 공급계약, 추정가격 200만원 미만 물품의 제조·구매·임차 및 용역계약 …
```

**V2 예시** (prefix + 본문)

```text
교육청행정업무매뉴얼 > 제12편 학교회계 지출 > 견적서 징구 및 계약상대자 결정 > 견적서 제출이 생략 가능한 경우

전기·가스·수도 등의 공급계약, 추정가격 200만원 미만 물품의 제조·구매·임차 및 용역계약 …
```

구현: `app/chunking/embed_versions.py`, DB 컬럼 `embedding_v1` / `embedding_v2`, RPC `match_documents_v1` / `match_documents_v2`

---

## 평가 결과

골든 데이터셋 **45청크 × 90문항**(직접/의미변환/상황형 × AI·Human 각 45)으로 V1 vs V2 Retrieval을 비교했습니다.  
상세: [`contextual_retrieval_성능평가계획.md`](contextual_retrieval_성능평가계획.md), [`구현과정/STEP14.md`](구현과정/STEP14.md)

**평가 설정:** `match_count=10`, `match_threshold=0.0` (평가 전용), 정답 키 `document_id + chunk_no`

### 전체 (90문항)

| 지표 | V1 | V2 | Δ |
|------|-----|-----|-----|
| Recall@1 | 38.9% | **57.8%** | +18.9%p |
| Recall@5 | 74.4% | **82.2%** | +7.8%p |
| Recall@10 | 80.0% | **92.2%** | +12.2%p |
| MRR | 0.527 | **0.679** | +0.152 |
| Miss (Top-10 밖) | 18건 | **7건** | −11건 |

### 유형별 Recall@10

| 유형 | V1 | V2 |
|------|-----|-----|
| 직접 질의형 | 83.3% | **96.7%** |
| 의미 변환형 | 76.7% | **93.3%** |
| 상황 기반형 | 80.0% | **86.7%** |

### 작성자별 Recall@1

| 작성자 | V1 | V2 |
|--------|-----|-----|
| AI | 53.3% | 64.4% |
| Human | 24.4% | **51.1%** |

### Rank Shift 대표 사례 (Top-50 검색 기준)

| 질문 요약 | V1 순위 | V2 순위 |
|-----------|---------|---------|
| 견적서 제출 없이 계약 가능한 경우 | 40위 | **1위** |
| 체전 인솔교사 여비 수령 여부 | 44위 | **6위** |
| 보조금 관리 업무 참고사항 | 32위 | **8위** |

**결론:** V2(Contextual Retrieval)가 전 지표에서 V1 대비 우수하며, 특히 **상황형·Human 질문·Recall@1**에서 개선이 뚜렷했습니다.

---

## 프로젝트 구조

```text
education-admin-copilot/
├── app/
│   ├── api/              # chat, documents, health
│   ├── chunking/         # outline 청킹, embed V1/V2
│   ├── services/         # retrieval, rag, llm, embedding
│   └── main.py
├── frontend/             # React MVP UI
├── scripts/
│   ├── setup_schema.sql
│   ├── ingest_manuals_exp.py
│   ├── build_golden_dataset.py
│   └── eval_recall.py
├── data/
│   ├── raw/manuals_exp/  # 원본 HWPX (19편)
│   └── evaluation/
│       ├── golden_dataset.json
│       └── eval_results.json   # 로컬 생성 (gitignore)
├── tests/
├── 구현과정/             # STEP1~14 구현·테스트 기록
└── contextual_retrieval_성능평가계획.md
```

---

## 시작하기

### 사전 요구사항

- Python 3.10+
- Node.js 18+
- Supabase 프로젝트 (pgvector extension)
- OpenAI API Key

### 1. 환경 설정

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

`.env` 파일 작성 (`.env.example` 참고):

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
RETRIEVAL_EMBED_VERSION=v2
```

### 2. DB 스키마

Supabase SQL Editor에서 `scripts/setup_schema.sql` 전체 실행

### 3. 매뉴얼 적재 (19편, V1/V2 dual embedding)

```powershell
.\venv\Scripts\python.exe scripts/ingest_manuals_exp.py
```

### 4. 백엔드 실행

```powershell
.\venv\Scripts\uvicorn.exe app.main:app --reload
```

- API 문서: http://localhost:8000/docs
- Health: http://localhost:8000/health

### 5. 프론트엔드 실행

```powershell
cd frontend
npm install
npm run dev
```

- UI: http://localhost:5173

---

## API

| Method | Path | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 |
| POST | `/chat` | RAG 질의응답 (`embed_version`: `v1` \| `v2`) |
| GET | `/documents` | KB 문서·청크 통계 |
| POST | `/documents/upload` | PDF/HWPX 업로드 및 적재 |

**`POST /chat` 요청 예시**

```json
{
  "question": "민원 종류 알려줘",
  "embed_version": "v2"
}
```

---

## 평가 실행

```powershell
# 골든 데이터셋 구축 (최초 1회, OpenAI API 필요)
.\venv\Scripts\python.exe scripts/build_golden_dataset.py

# V1 vs V2 Recall 평가 (약 6분)
.\venv\Scripts\python.exe scripts/eval_recall.py
```

결과: `data/evaluation/eval_results.json`

```powershell
# 테스트
.\venv\Scripts\pytest.exe tests/ -v
```

---

## 구현 문서

| STEP | 내용 |
|------|------|
| [STEP1](구현과정/STEP1.md) | Supabase 연결 |
| [STEP2](구현과정/STEP2.md) | DB 스키마 (pgvector, RPC) |
| [STEP3~7](구현과정/) | 파싱 → 청킹 → 임베딩 → 적재 |
| [STEP8~9](구현과정/) | Retrieval → LLM |
| [STEP10~11](구현과정/) | FastAPI, Documents API |
| [STEP12](구현과정/STEP12.md) | Frontend MVP |
| [STEP13](구현과정/STEP13.md) | Contextual Retrieval (V1/V2) |
| [STEP14](구현과정/STEP14.md) | Golden Dataset + Recall 평가 |

---

## 향후 계획

| 단계 | 내용 | 비고 |
|------|------|------|
| Reranking | V2 + Cross-Encoder (`bge-reranker-v2-m3`) | 보조 실험, Recall@1·MRR 추가 개선 |
| Hybrid Search | BM25 + Vector | |
| LLM 답변 품질 평가 | Faithfulness, Answer Correctness | Retrieval 평가 보완 |
| 법령 연동 | 법제처 OpenAPI 기반 최신 법령 검증 | |

---

## 라이선스

본 프로젝트는 포트폴리오·연구 목적으로 작성되었습니다.  
교육청 행정업무 매뉴얼 원문의 저작권은 해당 기관에 있습니다.
