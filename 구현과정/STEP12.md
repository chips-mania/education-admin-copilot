# STEP 12 — Frontend MVP

> 상태: **완료**  
> 완료일: 2026-06-08  
> 빌드: `frontend/` — `npm run build` 성공  
> 상세 계획: `구현과정/프론트엔드_구현계획서.md`

---

## 1. 목표

시연·면접용 최소 UI:

- KB 규모·문서 목록 확인
- 공문 업로드
- 채팅 + AI 답변 + 출처 표시

---

## 2. 기술 스택

- React + TypeScript + Vite
- Tailwind CSS + shadcn/ui
- Vite proxy: `/chat`, `/documents` → `localhost:8000`

---

## 3. 구현 컴포넌트

| 컴포넌트 | 역할 |
|----------|------|
| `KnowledgeBasePanel.tsx` | 문서 수·청크 수·카테고리별 통계 |
| `DocumentCategoryList.tsx` | source_type별 문서 목록 |
| `ChatWindow.tsx` / `ChatMessage.tsx` | 질의·응답 UI |
| `SourceCard.tsx` | 출처 카드 (파일명, 유사도, 장/절) |
| `UploadPanel.tsx` | PDF/HWPX 업로드 |
| `services/api.ts` | `GET /documents`, `POST /chat`, `POST /documents/upload` |

---

## 4. 실행 방법

```powershell
# 백엔드
.\venv\Scripts\uvicorn.exe app.main:app --reload

# 프론트엔드
cd frontend
npm run dev
```

브라우저: `http://localhost:5173`

프로덕션 빌드:

```powershell
cd frontend
npm run build
```

---

## 5. 파이프라인 위치

```text
STEP 11 Documents API
      ↓
STEP 12 Frontend MVP  ← 현재
      ↓
STEP 13 Contextual Retrieval (V1/V2)
```

---

## 6. 성공 조건 체크리스트

- [x] KB 패널 — 문서·청크 통계 표시
- [x] 채팅 — 답변 + 출처
- [x] 업로드 — 파일 선택 후 목록 갱신
- [x] `npm run build` 성공

---

## 7. 다음 단계

→ **STEP 13**: Contextual Retrieval (V1/V2)
