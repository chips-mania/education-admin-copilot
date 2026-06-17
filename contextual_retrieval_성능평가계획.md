# Contextual Retrieval 성능 평가 계획서

## 1. 연구 목적

본 연구의 목적은 교육청 행정업무 매뉴얼 기반 RAG(Retrieval-Augmented Generation) 시스템에서 Contextual Retrieval 기법이 검색 성능 향상에 미치는 영향을 검증하는 것이다.

Anthropic의 Contextual Retrieval 개념을 적용하여,

* V1 (기본 Retrieval)
* V2 (Contextual Retrieval)

를 동일한 환경에서 비교 평가한다.

본 연구에서는 **Retrieval 단계의 성능**을 중심으로 평가하며, LLM 생성 품질은 보조 실험으로 다룬다.

---

# 2. 실험 대상

## V1 (Prototype)

청크 본문(Content)만 임베딩

예시

```text
민원인이 행정기관에 대하여 처분 등 특정한 행위를 요구하는 것

민원의 종류
- 일반민원
- 고충민원
```

---

## V2 (Contextual Retrieval)

청크 본문 앞에 문맥(Context)을 추가하여 임베딩

예시

```text
교육청행정업무매뉴얼 > 제1편 민원정보공개 > 민원 개요 > 민원의 정의

민원인이 행정기관에 대하여 처분 등 특정한 행위를 요구하는 것

민원의 종류
- 일반민원
- 고충민원
```

---

# 3. 실험 통제 조건

## 동일 조건

* 동일 문서 집합 (`manuals_exp`, 19편)
* 동일 청킹 방식 (개요2 기준)
* 동일 임베딩 모델 (BGE-M3)
* 동일 벡터 DB (Supabase pgvector)
* 동일 검색 알고리즘 (cosine similarity, RPC)
* 동일 LLM (GPT-4.1 Mini)
* 동일 Prompt (검색 결과 → LLM 컨텍스트 포맷 통일)
* 동일 Top-K 설정

## 변경 조건

### V1

```text
본문(Content)만 임베딩 → embedding_v1
```

### V2

```text
Context(breadcrumb) + Content 임베딩 → embedding_v2
```

즉, **임베딩 텍스트만** 변경한다.

---

# 4. 데이터셋 구성

## 대상 문서

교육청 행정업무 매뉴얼 (`data/raw/manuals_exp/`)

* 민원정보공개
* 감사
* 인사
* 회계
* 시설관리
* 학교운영위원회
* 계약
* 재산관리

등 19편

---

## 청킹 방식

문서 구조 기반 청킹

```text
대단원(개요1 / chapter)
 └ 소제목(개요2 / heading)
     └ 내용(개요3,4 / content)
```

개요2(heading)를 기준으로 하나의 청크를 생성한다.

**제외 조건:** heading과 content가 동일한 제목만 있는 청크는 평가 풀에서 제외한다.

---

# 5. Golden Dataset 구축

## 청크 선정

전체 청크 중 **무작위 45개** 선정 (seed=42)

* 유형별 15청크씩 균등 배정
* 각 청크에 ai/human 출제자 2문항 (동일 유형)

---

## 문제 생성 방식

선정된 45개 청크에 대해

### AI 생성 문제

* 청크당 1문항 (`author: "ai"`)
* 유형별 프롬프트로 자동 생성

### 사용자 생성 문제

* 청크당 1문항 (`author: "human"`)
* 동일 청크·동일 유형, 실제 사용자 말투로 수기 작성

총

```text
45 × 2 = 90문항
```

---

## 출제자·유형 분포

| 유형 | AI 출제 | 사람 출제 | 합계 |
| --- | --- | --- | --- |
| 직접 질의형 (`direct`) | 15 | 15 | 30 |
| 의미 변환형 (`paraphrase`) | 15 | 15 | 30 |
| 상황 기반형 (`situation`) | 15 | 15 | 30 |
| **합계** | **45** | **45** | **90** |

---

## 출제자 구분

```json
{
  "author": "ai"
}
```

또는

```json
{
  "author": "human"
}
```

으로 저장한다.

---

# 6. 문제 유형

90문항을 아래 **3개 유형**으로 균등하게 구성한다.

---

## 1. 직접 질의형 (`direct`)

**정의:** 청크의 핵심 용어를 그대로 사용하는 질문

**예시**

청크: 민원의 정의

```text
민원이란 무엇인가요?
민원의 종류는 무엇인가요?
```

**목적:** 기본 검색 성능 확인

**기대:** V1 ≈ V2

---

## 2. 의미 변환형 (`paraphrase`)

**정의:** 같은 의미를 다른 표현으로 질문

**예시**

청크: 학교 계좌 관리

```text
학교 통장은 어떻게 관리하나요?
학교 회계용 계좌 운영 기준은 무엇인가요?
```

**목적:** 벡터 검색의 의미 매칭 능력 확인

**기대:** V2 > V1

---

## 3. 상황 기반형 (`situation`)

**정의:** 정답 키워드를 사용하지 않고 상황만 설명하는 질문

**예시**

청크: 국고보조금은 단독 세부항목으로 편성

```text
새로 받은 지원금을 기존 사업 예산에 같이 넣어도 되나요?
학교 자금이 들어가는 통장을 관리할 때 주의할 점은 무엇인가요?
```

**목적:** Contextual Retrieval 효과 검증

**기대:** V2 >> V1

---

## 출제자별 역할

| 출제자 | 역할 |
| --- | --- |
| AI (45문항) | 유형 균형·재현성, 자동 생성 |
| Human (45문항) | 실제 사용자 질문 반영, 구어체·오타·축약 표현 포함 |

Human 예시 (AI와 동일 청크·유형, 다른 표현):

```text
통장 관리 뭐 봐야됨?
보조금 통장 따로 써야 하나?
학교 돈 들어오는 계좌 관리 어떻게 함?
```

---

# 7. 정답 데이터 구성

각 문제마다 Gold Chunk를 지정한다.

매칭 키: `document_id` + `chunk_no` (`gold_chunks`)

예시

```json
{
  "question_id": 1,
  "question": "민원이란 무엇인가요?",
  "type": "direct",
  "author": "ai",
  "gold_chunks": [12],
  "source": {
    "document": "제1편 민원정보공개",
    "chapter": "민원 개요",
    "heading": "민원의 정의"
  }
}
```

---

실무형 질문 등 여러 청크가 필요한 경우

```json
{
  "gold_chunks": [45, 46]
}
```

형태 허용 (본 평가셋에서는 단일 청크가 기본)

---

# 8. Retrieval 평가 지표

90문항 전체에 대해 측정한다.

## Recall@1

검색 결과 1위에 정답 청크가 존재하는 비율

---

## Recall@5

검색 결과 상위 5개 안에 정답 청크가 존재하는 비율

---

## Recall@10

검색 결과 상위 10개 안에 정답 청크가 존재하는 비율

---

## MRR (Mean Reciprocal Rank)

정답 청크의 평균 순위를 측정

수식

```text
MRR = 평균(1 / 정답순위)
```

예시

```text
1위 = 1.0
2위 = 0.5
3위 = 0.333
```

정답을 얼마나 상위에 배치하는지 평가 가능하다.

---

# 9. 평가 절차

## Step 1

질문 입력 (90문항)

---

## Step 2

V1 검색 수행 (`embedding_v1` 기반)

---

## Step 3

V2 검색 수행 (`embedding_v2` 기반)

---

## Step 4

각 버전에 대해

* Recall@1
* Recall@5
* Recall@10
* MRR

계산

---

## Step 5

문제 유형별 성능 비교

예시

| 유형 | V1 Recall@5 | V2 Recall@5 | 기대 |
| --- | --- | --- | --- |
| 직접 질의형 | 85% | 87% | V1 ≈ V2 |
| 의미 변환형 | 60% | 78% | V2 > V1 |
| 상황 기반형 | 35% | 72% | V2 >> V1 |

---

## Step 6

출제자별 성능 비교

예시

| 출제자 | Recall@5 | MRR |
| --- | --- | --- |
| AI | 72% | 0.58 |
| Human | 65% | 0.51 |

AI 생성 문제와 실제 사용자가 생성한 문제의 난이도 차이를 분석한다.

---

# 10. 추가 평가 (선택)

Retrieval 성능 평가 후,

동일 질문에 대해 실제 RAG 응답을 생성하여 다음을 측정할 수 있다.

* Answer Correctness
* Faithfulness
* Answer Relevancy

단, 본 연구의 **핵심 평가는 Retrieval 성능 비교**이며, 생성 품질 평가는 보조 실험으로 수행한다.

---

# 11. 기대 결과

Contextual Retrieval은 다음 유형에서 가장 큰 효과를 보일 것으로 예상된다.

| 유형 | 기대 |
| --- | --- |
| 직접 질의형 | V1 ≈ V2 (키워드가 본문에 그대로 있어 context 이득 적음) |
| 의미 변환형 | V2 > V1 (표현은 달라도 맥락이 있으면 매칭 유리) |
| 상황 기반형 | V2 >> V1 (키워드 없을 때 breadcrumb/heading 효과 큼) |

---

# 12. 최종 판단 기준

Contextual Retrieval이 효과적이라고 판단하는 조건

* Recall@1, Recall@5, Recall@10 전반적 향상
* MRR 향상
* 특히 **의미 변환형·상황 기반형**에서 통계적으로 의미 있는 개선

직접 질의형에서 V1과 큰 차이가 없더라도, 상황 기반형에서 V2가 유의미하게 우수하면 Contextual Retrieval이 검색 성능 향상에 기여한다고 결론 내린다.

---

# 13. 산출물

| 파일 | 설명 |
| --- | --- |
| `data/evaluation/golden_dataset.json` | 45청크, 90문항 평가셋 |
| `scripts/build_golden_dataset.py` | 청크 샘플링 + AI 문항 생성 |
| `scripts/eval_recall.py` | Recall@k / MRR / Mean Rank 평가 (`match_count=10`, `threshold=0`) |
| `data/evaluation/eval_results.json` | V1 vs V2 평가 결과 (90문항) |
