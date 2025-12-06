# Hallucination Detection with Small Language Models

## 출처
- **ArXiv**: https://arxiv.org/abs/2506.22486
- **저자**: Ming Cheung (dBeta Labs, The Lane Crawford Joyce Group, Hong Kong)
- **제출일**: 2025년 6월 24일 (v1)
- **카테고리**: cs.CL (Computation and Language)

## AI 요약

### 1. 연구 배경 및 동기

LLM은 RAG(Retrieval-Augmented Generation)를 통해 벡터 데이터베이스에서 컨텍스트를 검색하여 질문에 답변할 수 있지만, **환각(hallucination) 문제가 실무 적용의 신뢰성을 저해**한다. 특히 Ground truth가 없는 QA 시나리오에서 환각 탐지가 어렵다.

#### 환각의 3가지 유형 (Table I 예시)
1. **Logical Contradiction**: "매디슨 시는 50만 명의 인구를 가지고 있으며, 작은 마을의 매력으로 알려져 있다" (논리 모순)
2. **Prompt Contradiction**: 건강한 아침 식사를 묘사하라는 프롬프트에 "설탕 시리얼과 베이컨이 좋은 선택"이라고 답변 (지시 모순)
3. **Factual Contradiction**: 전통 마르게리타 피자 재료에 "초콜릿"이 포함되어 있다고 잘못된 사실 제시

#### 기존 접근법의 한계
- **ROUGE 같은 전통 메트릭**: Reference 답변이 필요하여 실시간 평가 불가능
- **LLM의 Yes/No 질문 활용**: 지식이 LLM 내부에 있어야 하며, 여러 번 호출 필요 (시간 소요)
- **대형 LLM 로컬 배포**: ChatGPT는 클로즈드 소스, 대형 모델은 계산 리소스 과다 필요

### 2. 핵심 아이디어: Small Language Models (SLMs) 활용

#### SLM의 정의와 장점
- **정의**: 100M~5B 파라미터 범위의 언어 모델
- **장점**:
  - 자유 텍스트 생성 성능은 대형 모델보다 낮지만, **특정 태스크(검증)에는 효율적**
  - 로컬 배포 가능 → "Yes" 확률 직접 추출 (여러 번 API 호출 불필요)
  - 비용 효율적, 리소스 제약 환경에 적합

### 3. 제안 프레임워크 구조

#### (1) LLM 응답 생성 (RAG 기반)
- 사용자 질문 → 벡터 데이터베이스에서 관련 컨텍스트 검색
- LLM이 컨텍스트 기반 응답 생성
- 예: "근무 시간은 오전 9시부터 오후 5시이며, 매장은 일요일부터 토요일까지 영업합니다."

#### (2) Splitter (응답 분할)
- **목적**: 응답을 문장 단위로 분할
- **이유**: 부분적으로 올바른 응답 처리
  - 전체 응답: "근무 시간은 9 AM to 5 PM, **월요일부터 금요일**까지 영업" (부분 맞음)
  - 문장 1: "근무 시간은 9 AM to 5 PM" ✓
  - 문장 2: "월요일부터 금요일까지 영업" ✗ (실제는 일요일~토요일)

- **구현**: SpaCy 라이브러리 사용
- **수식**: $r_i \rightarrow S(r_i) = \{r_{i,1}, r_{i,2}, ..., r_{i,j}\}$

#### (3) Small Language Models (SLMs) - 검증
- **프롬프트**: "질문, 컨텍스트, 답변이 주어졌을 때, YES 또는 NO로 시작하는 답변 생성"
- **사용 모델**:
  - **Qwen2**: 고급 자연어 이해/생성, 다양한 태스크에서 우수한 성능
  - **MiniCPM**: 엣지 최적화 LLM (2.4B 파라미터), Llama2-13B/MPT-30B보다 우수

- **점수 계산** (분할된 문장 $r_{i,j}$에 대해):
  $$s_{i,j}(m) = P(\text{token}_1 = \text{yes} | q_i, c_i, r_{i,j})$$
  - $q_i$: 질문
  - $c_i$: 컨텍스트
  - $r_{i,j}$: 분할된 응답
  - $m$: m번째 SLM

#### (4) Checker (점수 통합)
- **문제**: 서로 다른 SLM은 다른 스케일(평균, 분산)을 가짐
- **정규화**:
  $$\tilde{s}_{i,j}(m) = \frac{s_{i,j}(m) - \mu_m}{\sigma_m}$$
  - $\mu_m$, $\sigma_m$: SLM $m$의 평균과 표준편차 (과거 응답 기반)

- **여러 SLM 점수 평균**:
  $$s_{i,j} = \frac{1}{M} \sum_{m=1}^M \tilde{s}_{i,j}(m)$$

- **최종 응답 점수 (조화평균 사용)**:
  $$s_i = \frac{|S(r_i)|}{\sum_{j=1}^{|S(r_i)|} \frac{1}{s_{i,j}}}, \quad s_{i,j} > 0$$
  - 조화평균을 선택한 이유: 실험 결과 최고 성능 (F1 기준)

### 4. 실험 설정

#### 데이터셋
- **출처**: Lane Crawford 직원 핸드북
- **주제**: 고용 정책 (근무시간, 급여, 휴가, 복리후생 등)
- **구성**: 100개 이상의 (질문, 컨텍스트, 답변) 세트
- **답변 라벨 3가지**:
  1. **Correct**: 모든 정보가 정확
  2. **Partial**: 일부 정보만 정확 (예: 근무 시간은 맞지만 요일이 틀림)
  3. **Wrong**: 완전히 틀린 정보

#### 평가 대상 접근법
1. **Proposed**: Qwen2 + MiniCPM 사용 (제안 프레임워크)
2. **ChatGPT**: ChatGPT에 "Yes/No" 답변 요청 ($P(\text{True})$ 방식)
3. **P(yes)**: Qwen2만 사용, 전체 응답에 대해 "YES" 확률 계산 (Splitter 없음)
4. **Qwen2**: Qwen2만 사용 (제안 프레임워크)
5. **MiniCPM**: MiniCPM만 사용 (제안 프레임워크)

### 5. 실험 결과

#### (1) F1 Score 비교

**Correct vs. Wrong 탐지 (Figure 3a)**:
- 모든 접근법이 높은 F1 달성 (완전히 모순된 응답은 탐지 용이)
- 최저: P(yes) = 0.89
- 제안 방법 포함 대부분 > 0.90

**Correct vs. Partial 탐지 (Figure 3b)** - 더 어려운 문제:
- **Proposed: F1 = 0.81** (최고)
- ChatGPT: 0.70
- P(yes): 0.743
- Qwen2: ~0.77
- MiniCPM: ~0.76

**주요 발견**:
- SLM 사용이 ChatGPT보다 **11% 향상**
- SLM 사용이 P(yes)보다 **6.6% 향상**
- **여러 SLM 사용이 단일 모델보다 우수**

#### (2) Precision & Recall (Figure 4)

QA 시스템에서는 **높은 Precision + 적정 Recall**이 중요 (확신 있는 답변만 제공, 잘못된 정보 방지)

**Correct vs. Wrong (Figure 4a)**:
- Qwen2: Precision 0.89, Recall 0.56 (낮은 Recall)
- MiniCPM: Precision 0.92, Recall 0.53 (낮은 Recall)
- **Proposed: 비슷한 Precision, 훨씬 높은 Recall** → 여러 SLM이 성능 향상

**Correct vs. Partial (Figure 4b)**:
- 모든 접근법에서 Precision/Recall 하락 (더 어려운 태스크)
- 동일 결론: **여러 SLM 사용이 P(yes), ChatGPT보다 우수**

#### (3) 평균 계산 방법 비교 (Figure 5)

문장 점수들을 통합하는 4가지 방법 실험:

1. **Arithmetic Mean**: $s_i = \frac{1}{|S(r_i)|} \sum_{j=1}^{|S(r_i)|} s_{i,j}$
2. **Geometric Mean**: $s_i = \exp(\frac{1}{|S(r_i)|} \sum_{j=1}^{|S(r_i)|} \log(s_{i,j}))$
3. **Max**: $s_i = \max(S(r_i))$
4. **Min**: $s_i = \min(S(r_i))$
5. **Harmonic Mean**: 논문 제안 (Eq. 6)

**Correct vs. Wrong (Figure 5a)**:
- Max: F1 = 0.99 (최고) - 하나라도 올바른 문장이 있으면 높은 점수

**Correct vs. Partial (Figure 5b)**:
- **Harmonic: F1 = 0.81** (최고)
- Min: F1 = 0.66 (최저)
- Max: 성능 저하 (부분 정답에서 올바른 문장과 틀린 문장 혼재 시 구분 어려움)

**결론**: **Harmonic Mean이 부분 정답 탐지에 최적**

#### (4) 분포 분석 (Figure 6, 7)

**Proposed vs. P(yes) 비교 (Figure 6)**:
- 두 방법 모두:
  - Wrong 응답 → 낮은 $s_i$ 값에 집중
  - Correct 응답 → 높은 $s_i$ 값에 집중
  - Partial 응답 → 중간에 분산
  
- **Proposed (Figure 6a)**:
  - Wrong 응답이 더 뚜렷한 peak (낮은 값)
  - Partial과 Correct 응답이 더 잘 분리됨

- **P(yes) (Figure 6b)**:
  - Correct와 Partial이 겹쳐서 구분 어려움
  - 제안 방법보다 성능 낮음

**Geometric vs. Harmonic Mean (Figure 7)**:
- 두 방법 모두 Correct가 높은 $s$ 값, Wrong이 낮은 $s$ 값
- Harmonic이 더 나은 분리 성능 (Figure 5 결과와 일치)

### 6. 핵심 성능 요약

| 비교 | Proposed | ChatGPT | P(yes) | 개선폭 |
|------|----------|---------|--------|--------|
| F1 (Correct vs. Partial) | 0.81 | 0.70 | 0.743 | +11% vs ChatGPT, +6.6% vs P(yes) |
| 여러 SLM vs 단일 SLM | 더 높은 Recall | - | - | Precision 유지하면서 Recall 향상 |

### 7. 방법론 특징 정리

#### 장점
1. **효율성**: 대형 LLM보다 리소스 효율적 (로컬 배포 가능)
2. **확장성**: 리소스 제약 환경에서도 사용 가능
3. **정확성**: 여러 SLM 앙상블로 단일 모델 대비 성능 향상
4. **실용성**: RAG 파이프라인과 쉽게 통합

#### 한계 및 향후 연구
- **게이팅 메커니즘 추가**: Mixture-of-Experts 같은 동적 모델 선택
- **온라인 검증 프레임워크 통합**: 추가 정보를 온라인으로 추출하여 일반 컨텍스트 검증
- **다양한 데이터 타입 최적화**: 현재는 HR 정책 중심, 다른 도메인 확장 필요

## 내가 얻은 인사이트

### 1. "작은 것이 아름답다" - SLM의 특화된 역할
대형 LLM(GPT-4, Claude)은 범용 생성 태스크에 강력하지만, **검증 태스크에서는 SLM이 더 효율적**이다. 이 논문은:
- Qwen2, MiniCPM (2.4B 파라미터)을 사용
- ChatGPT보다 11% 높은 F1
- 로컬 배포로 비용 절감, 레이턴시 감소

이는 "LLM 파이프라인에서 모든 단계에 대형 모델을 쓸 필요 없다"는 중요한 인사이트를 준다. **생성은 대형 LLM, 검증은 SLM**이라는 역할 분담이 최적일 수 있다.

### 2. Splitter는 "Partial Correctness"를 다루는 핵심이다
응답을 문장 단위로 분할하지 않으면:
- "근무 시간은 9 AM to 5 PM (✓), 월요일부터 금요일까지 영업 (✗)"
- 전체 응답을 평가하면 → 혼란 발생

Splitter를 사용한 결과:
- P(yes): F1 = 0.743 (Splitter 없음)
- Proposed: F1 = 0.81 (Splitter 있음, +6.6%)

실무에서 **부분적으로 맞는 답변은 흔하다**. 예를 들어:
- "파리는 프랑스의 수도이며, 인구는 500만 명이다" → 첫 문장은 맞지만, 인구는 약 210만 명 (틀림)

Splitter는 문장 레벨 세분화로 **fine-grained hallucination detection**을 가능케 한다.

### 3. Harmonic Mean은 "하나라도 틀리면 페널티" 전략이다
4가지 평균 방법 중 Harmonic Mean이 Partial 탐지에서 F1 0.81로 최고였다:
- **Max**: Correct vs. Wrong에서 0.99 (최고), Correct vs. Partial에서 성능 저하
  - 이유: 하나라도 올바른 문장이 있으면 높은 점수 → 부분 정답 구분 불가
- **Harmonic**: Correct vs. Partial에서 0.81 (최고)
  - 이유: 하나라도 낮은 점수가 있으면 전체 점수 하락 (보수적 평가)

조화평균의 특성:
- $\frac{n}{\sum_{i=1}^n \frac{1}{x_i}}$ → 작은 값에 민감
- 예: [0.9, 0.9, 0.2] → 산술평균 = 0.67, 조화평균 = 0.36

**실무 의미**: 안전성이 중요한 도메인(의료, 금융)에서는 "하나라도 의심스러우면 전체를 의심"하는 조화평균이 적합하다.

### 4. 정규화는 "다른 스케일의 SLM 통합"의 열쇠다
Qwen2와 MiniCPM은 서로 다른 확률 분포를 가진다:
- Qwen2: P(yes) = [0.3, 0.7, 0.85, ...]
- MiniCPM: P(yes) = [0.1, 0.5, 0.9, ...]

정규화 없이 평균하면:
- MiniCPM의 0.9가 Qwen2의 0.85보다 항상 높게 평가되지만, 실제로는 두 모델의 스케일 차이일 수 있음

**Z-score 정규화**로 해결:
$$\tilde{s}_{i,j}(m) = \frac{s_{i,j}(m) - \mu_m}{\sigma_m}$$

이후 평균하면 **각 SLM의 상대적 신뢰도**를 공정하게 반영할 수 있다. 이는 앙상블 ML에서 feature scaling과 동일한 원리이다.

### 5. 여러 SLM 사용은 "Ensemble Learning"의 NLP 버전이다
단일 SLM vs. 제안 방법 (Qwen2 + MiniCPM):
- Qwen2만: Precision 0.89, Recall 0.56
- Proposed: 비슷한 Precision, **훨씬 높은 Recall**

이는 ML의 Bagging/Boosting과 유사:
- 여러 약한 분류기(weak learners)를 결합 → 강한 분류기(strong learner)
- 각 SLM이 다른 특성을 포착 → 평균으로 noise 감소, 일반화 향상

**실무 적용**: 프로덕션 환경에서 2-3개의 SLM을 병렬로 실행하고 점수를 앙상블하면, 단일 대형 LLM보다 **비용 대비 성능**이 좋을 수 있다.

### 6. Partial Correctness 탐지는 "AI Safety의 회색지대"다
실험 결과:
- Correct vs. Wrong: F1 > 0.89 (모든 방법)
- Correct vs. Partial: F1 = 0.66~0.81 (훨씬 어려움)

이는 **현실 세계의 환각은 대부분 subtle하다**는 것을 의미한다:
- "완전히 틀린" 답변은 쉽게 탐지
- "대부분 맞지만 일부 틀린" 답변은 탐지 어려움 (사람도 속기 쉬움)

실무 의미:
- 사용자가 부분 정답을 더 신뢰할 가능성 높음 (완전히 틀린 답변보다 위험)
- **Partial correctness 탐지에 집중**하는 것이 실제 AI Safety에 더 중요

### 7. "RAG + Verification" 아키텍처의 실용적 가치
이 논문의 파이프라인:
1. 벡터 DB에서 컨텍스트 검색
2. 대형 LLM이 응답 생성
3. SLM이 검증 (컨텍스트와 응답 비교)

이는 **"Trust but Verify" 원칙**의 구현이다:
- 대형 LLM의 생성 능력 활용
- SLM의 효율적 검증으로 환각 필터링
- 컨텍스트 기반 검증으로 외부 지식 의존성 제거

실무 장점:
- 대형 LLM API 비용 절감 (검증에 작은 모델 사용)
- 로컬 SLM 배포로 레이턴시 감소
- 벡터 DB 컨텍스트로 도메인 특화 지식 제공

### 8. Lane Crawford 사례는 "Enterprise AI의 현실"을 보여준다
데이터셋이 Lane Crawford **직원 핸드북** 기반인 점이 흥미롭다:
- 기업 내부 문서 (공개 데이터 아님)
- HR 정책, 근무 규정 등 **정확성이 중요한 정보**
- 잘못된 답변 → 직원 불만, 법적 리스크

이는 **Enterprise LLM 적용의 핵심 과제**:
- 공개 LLM은 기업 내부 지식 부족
- RAG로 보완 가능하지만 환각 위험 존재
- **검증 레이어 필수**

실무 시사점:
- 기업 내부 챗봇, 고객 서비스 등에서 이 프레임워크 직접 적용 가능
- 특히 **규제 산업**(금융, 의료, 법률)에서 유용
- 100개 샘플로 실험 → 소규모 데이터셋으로도 효과적

### 9. Closed-source vs. Open-source의 trade-off를 명확히 보여준다
ChatGPT (Closed-source):
- 토큰 확률 직접 추출 불가 → 여러 번 API 호출 필요
- 비용, 레이턴시 증가
- F1 = 0.70

SLM (Open-source, Qwen2 + MiniCPM):
- 로컬 배포 → 확률 직접 추출
- 한 번 호출로 P(yes) 계산 가능
- F1 = 0.81

**결론**: 환각 탐지 같은 특정 태스크에서는 **오픈소스 SLM의 로컬 배포가 유리**하다. 클로즈드 소스의 성능 우위가 항상 비용/레이턴시를 정당화하지는 않는다.

### 10. 향후 연구 방향이 "Mixture-of-Experts의 NLP 적용"을 암시한다
논문이 제안한 향후 연구:
- **Gating Mechanism 추가**: 어떤 SLM을 사용할지 동적 결정
- **검증 프레임워크 통합**: 온라인으로 추가 정보 추출

이는 **Mixture-of-Experts (MoE) 아키텍처**와 유사:
- 여러 전문가 모델 (SLMs)
- 게이팅 네트워크 (어떤 전문가를 사용할지 결정)
- 동적 라우팅 (질문 유형에 따라 다른 SLM 활용)

예:
- 수학 질문 → Qwen2 (수학 성능 우수)
- 논리 질문 → MiniCPM (논리 추론 우수)
- 게이트가 질문 유형 분류 → 적절한 SLM 선택

이는 **비용 효율성과 성능의 최적 균형점**을 찾는 연구 방향이며, 프로덕션 LLM 시스템의 미래 모습일 수 있다.
