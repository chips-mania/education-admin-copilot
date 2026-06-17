# STEP 11 — Documents API (KB 목록·업로드)

> 상태: **완료**  
> 완료일: 2026-06-08  
> 테스트: `tests/test_documents_api.py` — **3/3 PASSED**

---

## 1. 목표

- Knowledge Base 규모·문서 목록을 API로 노출
- 공문(PDF/HWPX) 업로드 → 파싱 → 청킹 → 임베딩 → Supabase 저장
- 프론트엔드 KB 패널·업로드 UI 연동

---

## 2. 구현 내용

### 2.1 파일

| 파일 | 역할 |
|------|------|
| `app/api/documents.py` | `GET /documents`, `POST /documents/upload` |
| `app/schemas/documents.py` | 목록·업로드 Request/Response |
| `app/services/document_list_service.py` | 문서·청크 통계 조회 |
| `app/services/document_ingest_service.py` | 업로드 파일 파싱·적재 |
| `app/main.py` | CORS + documents 라우터 등록 |
| `tests/test_documents_api.py` | Documents API 테스트 |

### 2.2 Endpoint

| Method | Path | 설명 |
|--------|------|------|
| GET | `/documents` | KB 요약 통계 + 문서 목록 |
| POST | `/documents/upload` | PDF/HWPX 업로드 및 적재 |

### 2.3 CORS

프론트엔드 개발 서버(`localhost:5173`)에서 API 호출 가능하도록 `CORSMiddleware` 추가.

### 2.4 내부 흐름 (업로드)

```text
POST /documents/upload
  ↓
DocumentIngestService.ingest_uploaded_file()
  ↓
파일 저장 (data/raw/{source_type}/)
  ↓
parse_document() → chunk_document() → embed_texts()
  ↓
DocumentRepository insert (documents + chunks)
```

---

## 3. 테스트 결과

| 테스트 | 내용 | 결과 |
|--------|------|------|
| `test_list_documents_with_mock_service` | Mock 서비스 목록 응답 | PASSED |
| `test_list_documents_integration` | 실제 Supabase 연동 목록 | PASSED |
| `test_upload_rejects_unsupported_extension` | `.txt` 업로드 400 거부 | PASSED |

```powershell
.\venv\Scripts\pytest.exe tests/test_documents_api.py -v -s
```

---

## 4. 파이프라인 위치

```text
STEP 10 FastAPI /chat
      ↓
STEP 11 Documents API  ← 현재
      ↓
STEP 12 Frontend MVP
```

---

## 5. 성공 조건 체크리스트

- [x] `GET /documents` — summary + documents 반환
- [x] `POST /documents/upload` — PDF/HWPX만 허용
- [x] CORS 설정 (프론트 연동)
- [x] 테스트 3건 통과

---

## 6. 다음 단계

→ **STEP 12**: Frontend MVP
