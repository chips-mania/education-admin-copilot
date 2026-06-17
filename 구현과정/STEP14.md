# STEP 14 — Golden Dataset + Recall 평가

> 상태: **완료**  
> 완료일: 2026-06-14  
> 평가 실행: `scripts/eval_recall.py` (90문항, 약 6분)  
> 계획서: `contextual_retrieval_성능평가계획.md`

---

## 1. 목표

V1 vs V2 Retrieval 성능을 동일 골든 데이터셋으로 정량 비교.

- 지표: Recall@1, @5, @10, MRR, Mean Rank
- 분해: `by_type` (direct / paraphrase / situation), `by_author` (ai / human)
- 정답 매칭: `document_id` + `chunk_no`

---

## 2. 데이터셋

| 항목 | 값 |
|------|-----|
| 파일 | `data/evaluation/golden_dataset.json` |
| 버전 | 2.0 |
| 샘플 청크 | 45 (유형별 15) |
| 총 문항 | 90 (AI 45 + Human 45) |
| 문항 유형 | direct, paraphrase, situation |
| 코퍼스 | 19편, 1,180청크 (heading-only 152 제외) |
| 정답 키 | `document_id` + `chunk_no` |

### 스크립트

| 스크립트 | 역할 |
|----------|------|
| `scripts/build_golden_dataset.py` | 45청크 샘플링 + AI 문항 생성 (gpt-4.1-mini) |
| `scripts/resample_golden_chunks.py` | Human 슬롯 비어 있던 8개 샘플 재추출 (seed=142) |
| `scripts/eval_recall.py` | V1/V2 Recall 평가 |

### 재샘플링 (2026-06-14)

Human 문항 미작성 8청크 → sample_id `1, 2, 14, 15, 16, 29, 31, 34` 재추출 후 AI 문항 재생성. 이후 Human 90문항 전부 작성 완료.

검증: `validation.ok = true`, `unique_chunks = 45`

---

## 3. 평가 설정

| 파라미터 | 값 | 비고 |
|----------|-----|------|
| `match_count` | 10 | Recall@10 측정 |
| `match_threshold` | 0.0 | 평가 전용 (운영 `/chat`은 0.5 유지) |
| `rank_shift_match_count` | 50 | 순위 변화 사례 추출 |

```powershell
.\venv\Scripts\python.exe scripts/eval_recall.py
```

결과: `data/evaluation/eval_results.json`

---

## 4. 평가 결과 (2026-06-14)

### 4.1 전체 (90문항)

| 지표 | V1 | V2 | Δ |
|------|-----|-----|-----|
| Recall@1 | 38.9% | **57.8%** | +18.9%p |
| Recall@5 | 74.4% | **82.2%** | +7.8%p |
| Recall@10 | 80.0% | **92.2%** | +12.2%p |
| MRR | 0.527 | **0.679** | +0.152 |
| Mean Rank (hit) | 2.39 | **2.29** | -0.10 |
| Miss (@10 밖) | 18건 | **7건** | -11건 |

### 4.2 유형별 Recall@10

| 유형 | V1 | V2 |
|------|-----|-----|
| 직접 질의형 (direct) | 83.3% | **96.7%** |
| 의미 변환형 (paraphrase) | 76.7% | **93.3%** |
| 상황 기반형 (situation) | 80.0% | **86.7%** |

### 4.3 작성자별 Recall@10

| 작성자 | V1 | V2 |
|--------|-----|-----|
| AI | 88.9% | **97.8%** |
| Human | 71.1% | **86.7%** |

Human 질문에서 V2 개선 폭이 더 큼 (Recall@1: 24.4% → 51.1%).

### 4.4 Rank Shift 사례 (top-50 검색)

| QID | 유형 | V1 rank | V2 rank | 개선 |
|-----|------|---------|---------|------|
| 9 | paraphrase | 40 | **1** | +39 |
| 84 | situation | 44 | **6** | +38 |
| 6 | situation | 32 | **8** | +24 |

---

## 5. 결론

- V2(Contextual Retrieval)가 V1 대비 **전 지표에서 우수**
- 특히 **Recall@1·MRR·상황/의미변환형**에서 차이 뚜렷
- Contextual Retrieval이 교육행정 매뉴얼 RAG 검색 성능 향상에 기여함을 확인

---

## 6. 파이프라인 위치

```text
STEP 13 Contextual Retrieval (V1/V2)
      ↓
STEP 14 Golden Dataset + Recall 평가  ← 현재
      ↓
(예정) Reranking 보조 실험
```

---

## 7. 성공 조건 체크리스트

- [x] 45청크 × 90문항 골든 데이터셋 구축
- [x] 3유형 × AI/Human 분해
- [x] `eval_recall.py` 구현 및 실행
- [x] `eval_results.json` 저장
- [x] 평가 계획서 산출물 표 갱신

---

## 8. 다음 단계 (예정)

→ **Reranking 보조 실험** (V2 vs V2+Cross-Encoder) — 메인 결론(V1 vs V2)과 분리하여 진행
