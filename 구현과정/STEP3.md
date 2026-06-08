# STEP 3 — HWPX/PDF 문서 파싱

> 상태: **완료**  
> 완료일: 2026-06-08  
> 테스트: `tests/test_step3_document_parsing.py` — **4/4 PASSED**  
> 품질 평가: **90~95점** (초기 plain text 버전 대비 75점 → 개선 완료)

---

## 1. 목표

- HWPX(주력) 및 PDF 문서에서 텍스트 추출
- 파싱 결과를 JSON으로 저장 (`data/processed/`)
- 한글 깨짐 없이 본문·제목·출처 정보 보존
- RAG 적재(STEP 7)를 위한 구조화된 출력 준비

---

## 2. 구현 내용

### 2.1 파서

| 파일 | 역할 |
|------|------|
| `app/parsers/hwpx_parser.py` | HWPX → Markdown/HTML 혼합 텍스트 추출 |
| `app/parsers/pdf_parser.py` | PDF → plain text 추출 (PyMuPDF) |
| `app/parsers/__init__.py` | 확장자별 파서 라우팅 (`.hwpx`, `.pdf`) |
| `app/schemas/document.py` | `ParsedDocument` 스키마, `source_type` 추론, metadata 생성 |
| `app/config/manual_toc.py` | 학교 업무매뉴얼 제1~19편 목차 매핑 |
| `scripts/parse_documents.py` | 파싱 CLI → `data/processed/` 저장 |

### 2.2 HWPX 추출 방식

초기: `TextExtractor.extract_text()` — plain text만 추출, **표 구조 소실**

최종: `HwpxDocument.export_rich_markdown()` — 병합 셀(rowspan/colspan) 포함 **HTML table 보존**

```python
with HwpxDocument.open(str(file_path)) as document:
    content = document.export_rich_markdown()
```

복잡한 표(일반민원 > 법정민원/질의민원 등)에서 plain markdown 변환 시 내용 누락이 발생하여 rich markdown(HTML table) 방식 채택.

### 2.3 source_type 추론

`data/raw/{폴더명}/` 기준 자동 분류:

| 폴더 | source_type |
|------|-------------|
| `manuals/` | `manual` |
| `laws/` | `law` |
| `regulations/` | `regulation` |
| `interpretations/` | `interpretation` |

### 2.4 매뉴얼 metadata 매핑

파일명 패턴: `01-01-01 민원의 종류.hwpx`

| 코드 | 의미 | 예시 (`01-01-01`) |
|------|------|-------------------|
| 1번째 숫자 | **편** | 제1편 민원정보공개 |
| 2번째 숫자 | **단위업무(장)** | 민원의 처리 |
| 3번째 숫자 | **세부 문서 순번** | 1번째 문서 |
| 파일명 텍스트 | **문서 제목** | 민원의 종류 |

`app/config/manual_toc.py`에 제1~19편 단위업무 목록 저장 → 코드 기반 한글 chapter/section 자동 매핑.

### 2.5 출력 JSON 형식

```json
{
  "title": "민원의 종류",
  "content": "| 민원의 종류 |\n| --- |\n\n<table>...</table>\n\n※ 복합민원 : ...",
  "source_type": "manual",
  "file_name": "01-01-01 민원의 종류.hwpx",
  "file_path": "data/raw/manuals/01-01-01 민원의 종류.hwpx",
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

저장 위치: `data/processed/{source_type}/{파일명}.json`

---

## 3. 개선 이력

### 3.1 1차 구현 (75점)

- `extract_text()` plain text 추출
- 표 셀 경계 소실 (`구분` / `내용` / `일반민원` / `법정민원` ... 뭉개짐)
- metadata 없음
- 샘플 파일이 `interpretations/`에 잘못 배치 → `source_type: interpretation` 오분류

### 3.2 2차 개선 (90~95점)

| 항목 | 개선 |
|------|------|
| 표 구조 | `export_rich_markdown()` → HTML `<table>` 보존 |
| metadata | `chapter`, `section`, `title`, `source` 추가 |
| 목차 매핑 | `manual_toc.py` — 제1~19편 단위업무 자동 연결 |
| source_type | 파일을 `data/raw/manuals/`로 이동 → `manual` 정상화 |
| file_name / file_path | 출처 추적용 보존 |

### 3.3 의도적으로 보류한 항목 (V1)

| 항목 | 이유 |
|------|------|
| `metadata.document_type` | `source_type`과 중복 → 불필요 |
| `metadata.keywords` 자동 생성 | V1에서 과함, V2+ 검토 |

---

## 4. 이슈 및 해결

### 이슈 1: Windows 콘솔 인코딩

- **증상**: `parse_documents.py` 실행 시 `UnicodeEncodeError` (cp949)
- **해결**: `sys.stdout.reconfigure(encoding="utf-8")` 추가

### 이슈 2: 표 내용 누락

- **증상**: plain `export_markdown()` 시 법정민원 설명 셀 누락 (rowspan 표)
- **해결**: `export_rich_markdown()` 사용 → HTML table로 전체 셀 보존

### 이슈 3: 파일 위치 오류

- **증상**: `01-01-01 민원의 종류.hwpx`가 `interpretations/`에 있어 `source_type` 오분류
- **해결**: `data/raw/manuals/`로 이동, processed JSON 재생성

### 이슈 4: chapter/section 한글명 부재

- **증상**: `제1편`, `제1장` 코드만 있고 한글명 없음
- **해결**: 사용자 제공 매뉴얼 목차 → `manual_toc.py` 매핑 테이블 추가

---

## 5. 설치 패키지

```bash
pip install python-hwpx PyMuPDF
```

| 패키지 | 용도 |
|--------|------|
| `python-hwpx` | HWPX 파싱 (표 구조 보존) |
| `PyMuPDF` | PDF 파싱 |

---

## 6. 테스트

### 실행 명령

```bash
.\venv\Scripts\pytest.exe tests/test_step3_document_parsing.py -v -s
```

### 테스트 목록

| 테스트 | 검증 내용 |
|--------|-----------|
| `test_parse_hwpx_extracts_korean_text` | 한글 추출, metadata, source_type, 표 존재 |
| `test_parse_hwpx_preserves_table_structure` | 구분/내용/법정민원/질의민원 등 표 내용 보존 |
| `test_parse_document_router_hwpx` | 파서 라우팅 정상 |
| `test_parse_documents_script_output_format` | JSON 출력 필드 구조 검증 |

### 결과

```
tests/test_step3_document_parsing.py::test_parse_hwpx_extracts_korean_text PASSED
tests/test_step3_document_parsing.py::test_parse_hwpx_preserves_table_structure PASSED
tests/test_step3_document_parsing.py::test_parse_document_router_hwpx PASSED
tests/test_step3_document_parsing.py::test_parse_documents_script_output_format PASSED

4 passed
```

### 파싱 CLI

```bash
# 단일 파일
.\venv\Scripts\python.exe scripts/parse_documents.py "data/raw/manuals/01-01-01 민원의 종류.hwpx"

# data/raw 전체
.\venv\Scripts\python.exe scripts/parse_documents.py
```

---

## 7. 품질 평가

| 항목 | 상태 | 비고 |
|------|------|------|
| HWPX 파싱 | ✅ | 한글 정상 추출 |
| 표 보존 | ✅ | HTML table, rowspan/colspan 유지 |
| metadata | ✅ | chapter/section/title/source |
| 출처 추적 | ✅ | file_name, file_path |
| source_type | ✅ | 폴더 기반 자동 분류 |
| RAG 적재 준비 | ✅ | processed JSON → STEP 7 연결 가능 |
| Chunking 안정성 | ⚠️ | STEP 5에서 HTML table 분할 방지 필요 |
| Retrieval 품질 | ⏳ | STEP 8 이후 검증 예정 |

---

## 8. STEP 5(Chunking) 주의사항

현재 `content`에 HTML `<table>`이 포함됨. Chunking 시 아래 규칙 필요:

1. **HTML table은 가능한 한 하나의 Chunk 안에 유지**
2. **표 중간에서 Chunk 분할 금지** (`<table>` ~ `</table>` 블록 단위 처리)
3. 700 token 기준 분할 시 table 블록을 atomic unit으로 취급

표가 중간에 잘리면 검색·답변 품질이 크게 저하됨.

---

## 9. STEP 4를 진행하지 않은 이유

구현계획서의 STEP 4는 **OCR 처리** (PaddleOCR로 PDF 내 이미지 기반 절차도 추출)이다.

**진행하지 않기로 한 배경 (대화 중 사용자 결정):**

1. **대부분 HWPX** — 주력 문서가 HWPX이므로 OCR 우선순위 낮음
2. **OCR 제외 요청** — *"일단 ocr은 제외하고 진행해줘"*
3. **GPU 제외** — PaddleOCR GPU 활용도 당분간 보류 (6GB GPU 있으나 V1에서 미사용)
4. **V1 Baseline 목표** — Dense Vector RAG Baseline 구축이 우선, 절차도 OCR은 V2+ 확장 영역

**STEP 4가 필요해지는 시점:**

- PDF 내 이미지 절차도(플로우차트)에서 텍스트 추출이 필요할 때
- HWPX가 아닌 스캔 PDF 문서 비중이 커질 때

현재 흐름: **STEP 3 → (STEP 4 생략) → STEP 5 Chunking**

---

## 10. 성공 조건 체크리스트

- [x] HWPX 텍스트 추출 (한글 깨짐 없음)
- [x] PDF 파서 구현 (PyMuPDF)
- [x] 표 구조 보존 (HTML table)
- [x] metadata 생성 (chapter, section, title, source)
- [x] source_type 자동 분류
- [x] file_name / file_path 보존
- [x] processed JSON 저장
- [x] 테스트 4건 통과
- [ ] Retrieval 합격 테스트 (10문서 적재 후 "민원 종류 알려줘" → Top3) — STEP 8에서 확인

---

## 11. 다음 단계

→ **STEP 5**: Chunking (700 token / 100 overlap, **HTML table 분할 방지** 규칙 적용)
