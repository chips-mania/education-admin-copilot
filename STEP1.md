# STEP 1 — Supabase 환경 구성

> 상태: **완료**  
> 완료일: 2026-06-08  
> 테스트: `tests/test_step1_supabase_connection.py` — **PASSED**

---

## 1. 목표

- Supabase 프로젝트 연결
- pgvector Extension 활성화 (Supabase 대시보드)
- API Key 환경변수 설정
- Supabase Python Client 연결 확인

---

## 2. 사전 작업 (사용자)

| 항목 | 내용 |
|------|------|
| Supabase 프로젝트 | 생성 완료 |
| pgvector Extension | SQL Editor에서 `create extension if not exists vector;` 실행 |
| API Key | `.env`에 `SUPABASE_URL`, `SUPABASE_KEY` 입력 |
| Python 가상환경 | `venv/` 생성 (Python 3.13.2) |
| 프로젝트 구조 | `app/`, `scripts/`, `tests/`, `data/` 디렉터리 생성 |

---

## 3. 구현 내용

### 3.1 환경변수 (`.env`)

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=
OPENAI_API_KEY=
```

- `SUPABASE_URL`은 **`/rest/v1` 없이** 프로젝트 루트 URL만 사용
- `OPENAI_API_KEY`는 STEP 9 이전까지 비워둬도 됨

### 3.2 설정 모듈 — `app/config/settings.py`

- `.env` 파일 로드 (`python-dotenv`)
- `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_API_KEY` 관리
- URL 정규화: trailing `/` 및 `/rest/v1` 자동 제거
- `validate_supabase()` — URL/Key 미설정 시 `ValueError` 발생

### 3.3 Supabase 클라이언트 — `app/db/supabase_client.py`

- `supabase-py`의 `create_client()` 사용
- 싱글톤 패턴 (`get_supabase_client()`)
- SQLAlchemy 미사용 (구현 계획서 규칙 준수)

### 3.4 테스트 설정 — `tests/conftest.py`

- 프로젝트 루트를 `sys.path`에 추가하여 `app` 모듈 import 가능

---

## 4. 생성·수정 파일

| 파일 | 설명 |
|------|------|
| `app/config/settings.py` | 환경변수 로드 및 검증 |
| `app/db/supabase_client.py` | Supabase Client 싱글톤 |
| `tests/conftest.py` | pytest 경로 설정 |
| `tests/test_step1_supabase_connection.py` | STEP 1 연결 테스트 |
| `.env` | 실제 키 (git 제외) |
| `.env.example` | 환경변수 템플릿 |
| `.gitignore` | `.env`, `venv/` 등 제외 |
| `requirements.txt` | `supabase`, `python-dotenv`, `pytest` |
| `venv/` | Python 가상환경 |

---

## 5. 설치 패키지

```bash
pip install supabase python-dotenv pytest
```

| 패키지 | 용도 |
|--------|------|
| `supabase` | Supabase Python Client |
| `python-dotenv` | `.env` 로드 |
| `pytest` | 단계별 테스트 |

---

## 6. 이슈 및 해결

### 이슈 1: `SUPABASE_URL` 형식 오류

- **증상**: 연결 실패 또는 API 오동작
- **원인**: URL에 `/rest/v1/` 경로가 포함됨
- **해결**: 프로젝트 루트 URL만 사용 (`https://xxx.supabase.co`)
- **코드 대응**: `settings.py`에서 URL 자동 정규화

### 이슈 2: STEP 1 시점에 `documents` 테이블 없음

- **증상**: `PGRST205` — table not found
- **원인**: STEP 2 스키마 미생성 상태에서 테이블 조회 시도
- **해결**: 연결 테스트를 "API 도달 가능 여부"로 판단하도록 테스트 로직 조정
- **비고**: STEP 2 완료 후 동일 테스트는 정상 count 반환

---

## 7. 테스트

### 실행 명령

```bash
.\venv\Scripts\pytest.exe tests/test_step1_supabase_connection.py -v -s
```

### 테스트 내용

1. `get_supabase_client()` 호출 → Client 객체 생성 확인
2. `documents` 테이블 조회 시도 → API 응답 확인
   - 테이블 없으면 `PGRST205` 허용 (STEP 1 단독 검증)
   - 테이블 있으면 count 로그 출력

### 결과

```
tests/test_step1_supabase_connection.py::test_supabase_connection PASSED
```

---

## 8. 성공 조건 체크리스트

- [x] Supabase 연결 성공
- [x] API 정상 응답 반환
- [x] 환경변수 `.env` 설정 완료
- [x] Supabase Python Client 동작 확인
- [x] 테스트 코드 작성 및 통과

---

## 9. 아키텍처 메모 (FastAPI와의 관계)

| 구분 | Supabase (STEP 1) | FastAPI (STEP 10) |
|------|-------------------|-------------------|
| 역할 | DB 저장·벡터 검색 | HTTP API, RAG 파이프라인 조율 |
| 접근 | `supabase-py` Client | Supabase Client를 내부에서 호출 |

STEP 1은 DB 인프라 연결만 담당. FastAPI API는 STEP 10에서 구현 예정.

---

## 10. 다음 단계

→ **STEP 2**: Supabase DB 스키마 생성 (`documents`, `chunks`, `match_documents` RPC)
