# Towards Long Context Hallucination Detection

## 링크
- **링크**: https://aclanthology.org/2025.findings-naacl.436

---

## AI 요약

### 핵심 문제
- LLM은 다양한 작업에서 뛰어난 성능을 보이지만, contextual hallucination(컨텍스트와 무관하거나 모순되는 정보 생성) 문제 존재
- 긴 컨텍스트 입력에서의 hallucination 탐지는 여전히 미해결 과제
- 기존 연구들은 짧은 컨텍스트에 초점을 맞춰왔음

### 제안 방법

**문제 정의**
- BERT의 최대 시퀀스 길이 제약 (일반적으로 512 토큰)
- 긴 컨텍스트(수천~수만 토큰)를 그대로 처리할 수 없음
- 단순 truncation은 중요한 정보 손실 초래

### 아키텍처: Decomposition & Aggregation 메커니즘

**1. Decomposition (분해) 단계**

*목적: 긴 컨텍스트를 BERT가 처리 가능한 단위로 분할*

- 입력: 긴 컨텍스트 C + LLM 응답 R
- 컨텍스트 C를 겹치는 청크들로 분할 (sliding window 방식 가능)
- 각 청크와 응답 R을 쌍으로 구성
- BERT 입력 형식: `[CLS] chunk_i [SEP] response [SEP]`

**청크 분할 전략 (추정)**
- 고정 길이 윈도우 (예: 512 토큰)
- 겹침(overlap) 존재 가능 - 경계에서 정보 손실 방지
- 각 청크는 독립적으로 BERT에 입력

**2. BERT 인코딩**

*목적: 각 청크-응답 쌍의 관계 파악*

- 사전 학습된 BERT 인코더 활용
- 각 청크에 대해 독립적으로 인코딩 수행
- `[CLS]` 토큰의 임베딩 또는 전체 시퀀스 표현 추출
- 출력: 각 청크에 대한 hallucination 확률 또는 support score

**분류 헤드**
- BERT 위에 간단한 분류 레이어 추가
- Binary classification: hallucination vs non-hallucination
- 또는 score 형태로 출력 (0~1 사이 확률)

**3. Aggregation (집계) 단계**

*목적: 여러 청크의 판단을 하나의 최종 판단으로 통합*

**집계 전략 (가능한 방법들)**

a) **Max Pooling**
   - 가장 높은 hallucination 확률 선택
   - 보수적 접근: 하나라도 의심되면 hallucination으로 판단

b) **Average Pooling**
   - 모든 청크의 평균 확률
   - 균형잡힌 판단

c) **Attention-based Aggregation**
   - 각 청크에 가중치 부여
   - 중요한 청크에 더 높은 가중치
   - 학습 가능한 어텐션 메커니�m

d) **Majority Voting**
   - 각 청크의 이진 판단을 투표
   - 과반수의 의견 채택

**Luna와의 차이점 (추정)**
- Luna: 토큰 레벨 예측 → 윈도우 간 max → 토큰 간 min
- 본 논문: 청크 레벨 예측 → 청크 간 집계 (방식은 논문 확인 필요)
- Luna: RAG context + question + response 구조
- 본 논문: 일반적인 context + response 구조

### 학습 방식 (추정)

**데이터 준비**
- 긴 컨텍스트 hallucination 전용 데이터셋 구축
- Positive: context와 일치하는 응답
- Negative: context와 모순되거나 무관한 응답

**학습 프로세스**
1. 사전 학습된 BERT 가중치로 초기화
2. 각 청크-응답 쌍에 대해 분류 학습
3. End-to-end 방식으로 BERT + 분류 헤드 + 집계 레이어 동시 학습
4. Cross-entropy loss 또는 유사 손실 함수 사용

**특징**
- BERT 기반으로 DeBERTA보다 경량 (110M 파라미터)
- 더 빠른 추론 속도 기대
- 사전 학습된 언어 이해 능력 활용

### 성능

**정확도**
- 비슷한 크기의 이전 모델들 대비 모든 메트릭에서 크게 우수
- LLM 기반 모델들(GPT-3.5, GPT-4 등)보다 뛰어난 성능
- 긴 컨텍스트에서 특히 강점

**효율성**
- 추론 속도가 LLM 대비 훨씬 빠름
- BERT 크기(110M)로 경량 배포 가능
- 비용 효율적

### Luna와의 비교

**공통점**
- 작은 인코더 모델 활용 (BERT vs DeBERTA)
- 긴 컨텍스트 처리를 위한 분해-집계 전략
- 빠른 추론 속도와 높은 정확도 목표

**차이점 (예상)**
- Luna: RAG 환경에 특화, NLI 기반 접근
- 본 논문: 일반적인 긴 컨텍스트 hallucination에 초점
- Luna: 토큰 레벨 span 예측 → 윈도우 집계
- 본 논문: 구체적인 분해-집계 메커니즘은 논문 본문 확인 필요

**시사점**
- "작게 쪼개서 집계" 전략이 긴 컨텍스트 처리의 정석 패턴으로 확립
- BERT/DeBERTA 같은 경량 인코더로도 LLM 수준 또는 그 이상의 성능 달성 가능
- 실용성(속도, 비용) + 정확도 균형이 핵심

---

## 내가 얻은 인사이트

- Luna 논문을 본 직후 이 논문을 발견했는데, "분할 단위가 토큰이냐 단순 길이 기반 청크냐?" + "컨텍스트와 유저 질문을 분리하여 고려하느냐?" 정도의 차이를 제외하면 큰 차이는 없다고 느낌
- 긴 컨텍스트 할루시네이션 감지의 정석 패턴인 거 같음 (사실 물리적으로 다른 방법이 없을 것 같기는 함)
- BERT 기반이라는 점에서 Luna의 DeBERTA보다 4배 더 가볍다고 함 (실제로 구현해서 돌려봤을 때 2배 정도 속도 차이가 나기도 했던거 같음, 가벼운건 맞음)
- Luna는 좀 더 구현이 꼼꼼한 대신 RAG에 적합하고, Liu는 굳이 그렇게까지 고려할 필요없는 경량 검증에 유리하다고 생각함
