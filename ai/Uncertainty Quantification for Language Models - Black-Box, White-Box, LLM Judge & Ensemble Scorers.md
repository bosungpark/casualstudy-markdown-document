# Uncertainty Quantification for Language Models: A Suite of Black-Box, White-Box, LLM Judge, and Ensemble Scorers

## 출처
- **ArXiv**: https://arxiv.org/abs/2504.19254
- **저자**: Dylan Bouchard (CVS Health), Mohit Singh Chauhan (CVS Health)
- **게재**: TMLR (Transactions on Machine Learning Research) 2025 accepted
- **최초 제출**: 2025년 4월 27일
- **최종 수정**: 2025년 11월 12일 (v4)
- **Python 툴킷**: [UQLM](https://github.com/cvs-health/uqlm)

## AI 요약

### 1. 연구 배경 및 동기
LLM이 의료, 금융 등 고위험 도메인에 점점 더 많이 사용되면서, 환각(hallucination) 문제가 심각해지고 있다. OpenAI의 GPT-4.5조차 특정 벤치마크에서 37.1%의 환각률을 보이며, 이는 LLM 출력의 정확성과 신뢰성을 실시간으로 모니터링할 필요성을 강조한다.

기존의 환각 탐지 방법들은 주로:
- Ground truth 텍스트와 생성 콘텐츠 비교 (배포 전 평가용)
- 소스 콘텐츠와 생성 콘텐츠 비교
- 불확실성 정량화 (Uncertainty Quantification, UQ)

이 중에서 UQ 기법은 **closed-book 환경**(소스 데이터베이스, ground truth, 인터넷 접근 불필요)에서 **생성 시점에 실시간으로** 응답 레벨 신뢰도 점수를 계산할 수 있어 프로덕션 환경에 적합하다.

### 2. 핵심 기여

#### (1) 표준화된 UQ 프레임워크
다양한 UQ 기법들을 **0에서 1 사이의 신뢰도 점수**로 표준화:
- **Black-Box UQ**: 동일 프롬프트에 대한 여러 응답의 의미적 일관성 측정
- **White-Box UQ**: 토큰 확률을 활용한 불확실성 정량화
- **LLM-as-a-Judge**: LLM을 활용하여 응답의 정확성 평가

#### (2) Tunable Ensemble Scorer
- 개별 스코어러들의 **가중 평균 앙상블**
- 사용자가 제공한 graded LLM 응답 세트로 가중치 튜닝
- **특정 use case에 최적화** 가능한 확장 가능한 구조
- AUROC 또는 F1-score 등 목적 함수 선택 가능

#### (3) UQLM 오픈소스 툴킷
모든 스코어러의 즉시 사용 가능한 Python 구현 제공

### 3. 방법론 상세

#### Black-Box UQ Scorers (5개)
프롬프트당 m개(실험에서 15개)의 후보 응답을 temperature=1.0으로 생성하여 원본 응답과 비교:

1. **Exact Match Rate (EMR)**: 원본과 정확히 일치하는 후보 응답 비율
   - 수식: $EMR(y_i; \tilde{\mathbf{y}}_i, x_i) = \frac{1}{m}\sum_{j=1}^m \mathbb{I}(y_i = \tilde{y}_{ij})$

2. **Non-Contradiction Probability (NCP)**: NLI 모델로 모순 확률 계산
   - BSDetector의 핵심 컴포넌트
   - DeBERTa-large-MNLI 사용
   - 수식: $NCP(y_i) = 1 - \frac{1}{m}\sum_{j=1}^m \frac{\eta(y_i, \tilde{y}_{ij}) + \eta(\tilde{y}_{ij}, y_i)}{2}$

3. **BERTScore Confidence (BSC)**: 컨텍스트화된 단어 임베딩 기반 F1 평균
   - Precision과 Recall의 조화평균

4. **Normalized Cosine Similarity (NCS)**: 문장 임베딩 기반 코사인 유사도
   - Sentence-BERT 같은 문장 변환기 활용
   - [-1, 1] → [0, 1]로 정규화

5. **Normalized Semantic Negentropy (NSN)**: Semantic Entropy의 정규화 버전
   - NLI 기반 상호 함의로 응답 클러스터링
   - $NSN = 1 - \frac{SE}{\log(m+1)}$
   - 더 높은 엔트로피 = 더 낮은 신뢰도

#### White-Box UQ Scorers (2개)
LLM 생성 응답의 토큰 확률 활용:

1. **Length-Normalized Token Probability (LNTP)**: 토큰 확률의 기하평균
   - $LNTP(y_i) = \prod_{t \in y_i} p_t^{1/L_i}$
   - 긴 시퀀스에 불이익을 주지 않음

2. **Minimum Token Probability (MTP)**: 응답 내 최소 토큰 확률
   - $MTP(y_i) = \min_{t \in y_i} p_t$
   - 가장 불확실한 토큰이 전체 신뢰도 결정

#### LLM-as-a-Judge Scorer
- 질문-응답 쌍을 LLM에 제공하여 0-100 점수로 평가
- 0-1 스케일로 정규화
- 프롬프트 템플릿: "How likely is the above answer to be correct? ... ONLY RETURN YOUR NUMERICAL SCORE"

#### Ensemble Scorer
- 가중 평균: $\hat{s}(y_i) = \sum_{k=1}^K w_k \hat{s}_k(y_i)$
- 제약: $\sum_{k=1}^K w_k = 1, w_k \geq 0$

**두 가지 튜닝 전략**:
1. **Threshold-Agnostic**: AUROC 같은 메트릭으로 가중치 최적화 → 이후 F1으로 threshold 튜닝
2. **Threshold-Aware**: F1-score로 가중치와 threshold 동시 최적화

### 4. 실험 설정 및 결과

#### 데이터셋 (6개 벤치마크, 각 1,000 샘플)
- **숫자 답변**: GSM8K (수학), SVAMP (수학)
- **객관식**: CSQA (상식), AI2-ARC (과학)
- **개방형 텍스트**: PopQA (지식), NQ-Open (자연어 질문)

#### 평가 대상 LLM (4개)
- GPT-4o, GPT-4o-mini
- Gemini-2.5-Flash, Gemini-2.5-Flash-Lite

#### 주요 실험 결과

**1) Threshold-Agnostic 평가 (AUROC)**
- 24개 시나리오(4 LLM × 6 데이터셋) 중:
  - **앙상블이 20개 시나리오에서 개별 컴포넌트 능가**
  - 최고 성능: Gemini-2.5-Flash-Lite on GSM8K (AUROC 0.986)
  - 최저 성능: GPT-4o on NQ-Open (AUROC 0.729)
  - 19/24 시나리오에서 AUROC > 0.8 달성

- **개별 스코어러 순위는 시나리오마다 크게 변동**:
  - LLM-as-a-Judge: 11개 시나리오 최고
  - Black-Box: 7개 시나리오 최고
  - White-Box: 6개 시나리오 최고

- **Black-Box 중 NLI 기반(NSN, NCP)이 가장 강력**:
  - 13/24 시나리오에서 최고 AUROC

- **LLM Judge 성능**:
  - GPT-4o: 단답형 벤치마크에서 우수 (6/8)
  - Gemini-2.5-Flash: 수학 벤치마크에서 우수 (6/8)
  - 큰 모델이 작은 모델보다 일관되게 우수

**2) Threshold-Optimized 평가 (F1-score)**
- **앙상블이 17/24 시나리오에서 최고 F1 달성**
- 예시 성능:
  - Gemini-2.5-Flash on AI2-ARC: F1 0.986
  - GPT-4o on AI2-ARC: F1 0.993
  - GPT-4o-mini on GSM8K: F1 0.940

**3) Filtered Accuracy@τ 분석**
- 신뢰도 threshold τ를 올릴수록 LLM 정확도 단조 증가
- 예시:
  - Gemini-2.5-Flash-Lite on PopQA: 기준 정확도 0.35 → τ=0.6에서 0.61
  - GPT-4o on GSM8K: 기준 0.55 → τ=0.6에서 0.93
- **낮은 신뢰도 응답 필터링의 효과 입증**

**4) 후보 응답 수(m)의 영향**
- m = 1, 3, 5, 10, 15로 실험
- **m이 증가할수록 성능 향상, 단 수익 체감**
- 예: GPT-4o on CSQA 
  - m=1: AUROC 0.54-0.57
  - m=15: AUROC 0.75-0.80
- **실무 배포 시 효율성과 효과성의 균형점 제시**

### 5. 실무 가이드라인

#### 스코어러 선택 기준
1. **토큰 확률 접근 가능 여부**
   - 가능하면: White-Box 사용 (레이턴시 증가 없음)
   - 불가능하면: Black-Box 또는 LLM-as-a-Judge

2. **레이턴시 요구사항**
   - 저지연 필요: NLI 기반(NSN, NCP) 피하고 빠른 Black-Box 또는 Judge 사용
   - 레이턴시 여유: NLI 기반 추천 (가장 강력한 성능)

3. **Graded 데이터셋 가용성**
   - 있으면: Ensemble 튜닝으로 최고 성능
   - 없으면: 개별 스코어러 중 선택

4. **LLM Judge 선택**
   - 해당 데이터셋에서 정확도가 높은 LLM을 Judge로 사용
   - 모델 정확도 ∝ Judge 성능

#### 신뢰도 점수 활용 방법
1. **응답 필터링**: 낮은 신뢰도 응답 차단
2. **Targeted Human-in-the-Loop**: 낮은 신뢰도 응답만 수동 리뷰
3. **배포 전 진단**: 어떤 질문 유형에서 LLM이 약한지 파악
4. **프롬프트 엔지니어링 개선**: 약점 발견 후 프롬프트 최적화

#### 윤리적 고려사항
- 신뢰도 점수 ≠ Ground truth 정확성 (모델 불확실성만 반영)
- 고위험 도메인(의료, 법률, 금융)에서는 외부 인간 검토 필수
- 그룹별 오류율 모니터링으로 분포적 공정성 확보

### 6. 한계점 및 향후 연구

#### 현재 한계
1. **질문 유형 일반화**: 6개 QA 벤치마크로 평가, 장문 생성/코드 생성은 미검증
   - 요약 같은 장문 생성: 단일 출력 내 참/거짓 혼재, 클레임 레벨 분해 필요
   - 코드 생성: 구문/실행 기반 정확성, 대안적 일관성 측정 필요

2. **LLM 다양성**: 4개 LLM만 테스트
   - 토큰 확률 분포 차이 → White-Box 동작 변화
   - 응답 변동성 차이 → Black-Box 성능 변화

3. **Out-of-Distribution 일반화**: In-domain 최적화만 평가, 교차 데이터셋 전이 미검증

4. **앙상블 구조**: 선형 앙상블만 고려
   - 향후: Monotonic GAM, Mixture-of-Experts, Tree-based 앙상블 연구 필요
   - Trade-off: 레이턴시, 과적합 위험, 해석 가능성

5. **Graded 데이터셋 요구사항**:
   - 간단한 grading(산술, 객관식): 자동 라벨링으로 해결
   - 복잡한 grading(요약): 초기 수백 개 인간 라벨 + 프로덕션 로그에서 점진적 추가

#### 향후 연구 방향
- 장문 생성 및 코드 생성에 대한 확장
- Cross-dataset weight transfer 연구
- Non-linear 앙상블 기법 탐색
- 소규모 graded 데이터셋으로 시작하는 점진적 학습 전략

## 내가 얻은 인사이트

### 1. 환각 탐지는 "표준화"가 핵심이다
다양한 UQ 기법들이 제각각의 출력 범위와 의미를 가지고 있었다. 이 논문의 가장 큰 기여는 모든 스코어러를 **0~1 사이의 신뢰도 점수**로 표준화한 것이다. 이로 인해:
- 서로 다른 기법들을 직접 비교 가능
- 가중 평균 앙상블 구성 가능
- 실무자가 threshold 기반 의사결정 가능

예를 들어, Semantic Entropy는 원래 unbounded인데 $\log(m+1)$로 나눠 정규화했고, Perplexity나 Average Negative Log Probability 같은 unbounded 메트릭은 의도적으로 제외했다. 이런 설계 선택이 실무 적용 가능성을 높였다.

### 2. "No Silver Bullet" - 시나리오별 최적 기법이 다르다
24개 시나리오에서 최고 성능 스코어러가 시나리오마다 달랐다:
- LLM Judge: 11개
- Black-Box: 7개
- White-Box: 6개

더 흥미로운 점은 **Judge의 도메인 특화성**:
- Gemini-2.5-Flash: 수학 벤치마크 8/8 최고 성능
- GPT-4o: 단답형 벤치마크 6/8 최고 성능

이는 "모델의 강점 도메인 = Judge로서도 강점"이라는 인사이트를 준다. 실무에서는 **타겟 태스크에서 정확한 LLM을 Judge로 선택**해야 한다.

### 3. NLI 기반 Black-Box가 생각보다 강력하다
NSN(Normalized Semantic Negentropy)과 NCP(Non-Contradiction Probability)가:
- 24개 시나리오 중 13개에서 Black-Box 중 최고 AUROC
- 18개 시나리오에서 다른 Black-Box 능가 (F1 기준)

단순 Exact Match나 Cosine Similarity보다 **의미적 함의 관계**를 명시적으로 모델링하는 NLI 접근이 효과적이다. 하지만 NLI 모델 추론 시간이 추가되므로 **저지연 애플리케이션에는 부적합**하다는 trade-off가 있다.

### 4. White-Box는 "공짜 점심"이지만 API 의존적이다
LNTP와 MTP는 토큰 확률만 있으면 추가 비용 없이 사용 가능하다:
- 추가 응답 생성 불필요 (Black-Box는 m=15개 생성)
- 추가 모델 호출 불필요 (LLM Judge는 별도 LLM 호출)
- **레이턴시 증가 없음**

하지만 OpenAI, Anthropic 등 많은 상용 API가 **토큰 확률을 제공하지 않는다**. 이 경우 White-Box는 선택지가 아니다. 논문에서 사용한 4개 LLM은 모두 토큰 확률을 제공했지만, 실무에서는 API 제약이 스코어러 선택의 첫 번째 기준이 될 수 있다.

### 5. Ensemble 튜닝은 "few-shot learning"처럼 작동한다
앙상블 가중치를 튜닝하려면 graded 데이터셋이 필요한데, 논문에서는:
- "수백 개 샘플"로 시작 가능
- 프로덕션 로그에서 점진적 추가

이는 **소량의 도메인 특화 데이터로 성능을 크게 향상**시킬 수 있다는 뜻이다. 실험 결과 앙상블이 20/24 (AUROC) 및 17/24 (F1) 시나리오에서 개별 컴포넌트를 능가했다. 특히 NQ-Open(가장 어려운 태스크)에서 AUROC 0.729를 달성한 것도 앙상블이었다.

### 6. m(후보 응답 수) 증가는 체감 수익이다
Black-Box 스코어러의 성능이 m=1→15로 증가하면서 향상되지만:
- GPT-4o on CSQA: m=1에서 0.54 → m=15에서 0.80
- **대부분 m=10 이후 성능 향상 둔화**

실무 배포 시 중요한 의미:
- m=5~10 정도면 충분한 성능
- m=15 이상은 계산 비용 대비 효과 낮음
- **생성 비용과 성능의 균형점 존재**

예를 들어 GPT-4o API를 사용한다면, m=15개 생성은 원래 비용의 15배이다. m=10에서 충분한 성능을 얻을 수 있다면 33% 비용 절감이 가능하다.

### 7. Filtered Accuracy는 "신뢰도 기반 라우팅"의 정당성을 보여준다
τ를 올릴수록 정확도가 단조 증가했다:
- Gemini-2.5-Flash-Lite on PopQA: 0.35 → 0.61 (75% 향상)
- GPT-4o on GSM8K: 0.55 → 0.93 (69% 향상)

이는 다음 실무 패턴들을 정당화한다:
1. **낮은 신뢰도 응답 차단**: 사용자에게 "죄송합니다, 확실하지 않습니다" 반환
2. **Human-in-the-Loop 라우팅**: 낮은 신뢰도만 인간 검토
3. **계층적 모델 라우팅**: 낮은 신뢰도는 더 강력한 모델로 재시도

특히 의료/금융 도메인에서 **정확도가 중요한 경우 높은 τ 설정**으로 precision을 높이고, 커버리지가 중요한 경우 낮은 τ로 recall을 높일 수 있다.

### 8. UQLM 툴킷은 "프레임워크보다 라이브러리"에 가깝다
논문의 companion 툴킷 UQLM은:
- 모든 스코어러 즉시 사용 가능
- LLM 선택만 하면 프롬프트 입력 → 신뢰도 점수 출력
- 앙상블 튜닝 기능 포함

이는 **"환각 탐지를 서비스로 제공"**하는 접근이다. 실무자가 UQ 논문들을 직접 구현할 필요 없이, 라이브러리 임포트만으로 프로덕션 배포 가능하다. 특히 "지속적으로 새 스코어러 추가" 계획은 연구-실무 갭을 줄이는 좋은 사례이다.

하지만 한계도 있다:
- 질문-답변 형식만 지원 (대화, 요약, 코드는 추가 작업 필요)
- 특정 API 형식 가정 (토큰 확률, 여러 응답 생성 등)

그럼에도 **즉시 적용 가능한 솔루션을 제공**했다는 점에서 실무 영향력이 크다.

### 9. 체급이 떨어져도 특수 목적을 가지는 모델을 생각보다 강하다.