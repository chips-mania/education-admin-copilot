# education-admin-copilot
AI Copilot for education administration powered by RAG, helping school staff find procedures, regulations, and operational guidance from manuals and policy documents.

---

# Education Administration Copilot (V1)

## 프로젝트 개요

Education Administration Copilot은 학교 업무매뉴얼, 교육 관련 법령, 행정규칙, 법령해석례를 기반으로 교육행정 업무를 지원하는 RAG(Retrieval-Augmented Generation) 기반 AI Copilot입니다.

신규 행정직원은 업무 수행 시 업무매뉴얼, 법령, 지침 등을 각각 찾아야 하며, 필요한 근거를 확인하기 위해 여러 시스템을 오가야 합니다. 본 프로젝트는 이러한 문제를 해결하기 위해 업무 관련 정보를 통합 검색하고 근거와 함께 제공하는 AI 업무지원 시스템을 구축하는 것을 목표로 합니다.

---

## 문제 정의

교육행정 업무는 다음과 같은 어려움을 가지고 있습니다.

* 업무매뉴얼 분량이 방대함
* 관련 법령과 지침을 별도로 찾아야 함
* 신규 직원은 어떤 규정을 참고해야 하는지 파악하기 어려움
* 업무 수행 시 여러 시스템을 반복적으로 탐색해야 함

예시)

질문

> 출장비 정산 절차와 관련 법령을 알려줘

기존 방식

> 업무매뉴얼 검색 → 관련 규정 확인 → 국가법령정보센터 검색 → 관련 조문 확인

개선 방식

> AI 질의 → 업무 절차 + 관련 법령 + 근거 조문 제공

---

## 목표

### 기능 목표

* 자연어 기반 업무 질의응답
* 업무매뉴얼 검색
* 관련 법령 검색
* 행정규칙 검색
* 법령해석례 검색
* 답변 출처 제공

### 비기능 목표

* 근거 기반 답변 제공
* 환각(Hallucination) 최소화
* 검색 정확도 측정 가능 구조 설계
* 향후 Hybrid Search 및 Reranker 실험 기반 마련

---

## 데이터 범위

### 포함

#### 학교 업무매뉴얼

* 민원 및 정보공개
* 공문서 작성
* 기록물관리
* 휴가
* 출장
* 학교운영위원회
* 계약
* 예산 및 회계
* 물품관리
* 시설관리

#### 교육 관련 법령

* 초중등교육법
* 지방공무원법
* 지방교육자치법
* 학교회계 관련 법령 등

#### 행정규칙

* 교육부 행정규칙
* 시도교육청 업무지침

#### 법령해석례

* 교육부 법령해석
* 법제처 법령해석

---

## 시스템 구조

사용자 질문

↓

Embedding 생성

↓

Vector Search (pgvector)

↓

관련 업무매뉴얼 검색

↓

관련 법령 검색

↓

관련 행정규칙 검색

↓

관련 해석례 검색

↓

LLM 답변 생성

↓

답변 + 출처 제공

---

## 기술 스택

### Backend

* FastAPI

### Database

* PostgreSQL
* pgvector

### Embedding Model

* BGE-M3

### LLM

* GPT-4.1 Mini

### Document Processing

* HWPX Parser
* PDF Parser
* PaddleOCR

---

## 데이터 처리 파이프라인

1. HWPX/PDF 문서 수집
2. 텍스트 추출
3. 이미지 기반 절차도 OCR 수행
4. Chunking
5. Embedding 생성
6. PostgreSQL(pgvector) 저장
7. Vector Search 수행

---

## V1 검색 방식

V1은 가장 단순한 Dense Retrieval 기반 RAG 구조를 사용합니다.

질문

↓

Embedding

↓

Vector Search

↓

Top-K 문서 검색

↓

LLM 답변 생성

본 버전은 Retrieval 성능 비교를 위한 Baseline 역할을 수행하며, 이후 Hybrid Search와 Reranker 적용 시 동일한 데이터셋을 기반으로 성능을 비교합니다. Retrieval 품질과 Reranking은 RAG 성능에 큰 영향을 미치는 핵심 요소로 알려져 있습니다.

---

## 주요 시나리오

### 시나리오 1

질문

> 출장비 정산 절차와 관련 법령을 알려줘

응답

* 출장 신청
* 출장 승인
* 증빙서류 제출
* 정산 처리

관련 법령

* 공무원 여비규정

출처

* 제6편 복무 > 출장

---

### 시나리오 2

질문

> 학교운영위원회 회의 개최 절차를 알려줘

응답

* 회의 준비
* 회의 공고
* 회의 개최
* 의결 및 결과 관리

관련 법령

* 초중등교육법

출처

* 제7편 학교운영위원회

---

## 평가 지표

### Retrieval Accuracy

검색된 문서가 실제로 관련 문서인지 평가

### Task Success Rate

사용자가 실제 업무를 수행할 수 있는 수준의 답변을 제공했는지 평가

### Citation Accuracy

답변에 제시된 출처가 실제 문서와 일치하는지 평가

### Response Time

질문부터 응답 생성까지의 소요 시간

---

## 향후 계획

### V2

Metadata Filtering 적용

### V3

Hybrid Search 적용 (BM25 + Vector Search)

### V4

Reranker 적용

### V5

공문 업로드 기반 업무 분석 Copilot

### V6

법제처 OpenAPI 기반 최신 법령 검증 Agent
