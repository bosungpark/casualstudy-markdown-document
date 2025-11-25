# INSIDE - LLM 내부 상태로 환각 검출하기 (EigenScore + Feature Clipping)

## 출처

- **논문**: INSIDE: LLMs' Internal States Retain the Power of Hallucination Detection
- **저자**: Chao Chen, Kai Liu (Zhejiang Univ.), Ze Chen, Yi Gu, Yue Wu, Mingyuan Tao, Zhihang Fu, Jieping Ye (Alibaba Cloud)
- **발표**: ICLR 2024, arXiv:2402.03744v2 (2024년 10월)
- **링크**: https://arxiv.org/abs/2402.03744

## AI 요약

### 핵심 아이디어

**기존 방법의 한계**:
- **Logit-level uncertainty** (Perplexity, Entropy): 토큰별 불확실성을 문장 수준으로 집계하는 과정에서 **의미 정보 손실**
- **Language-level consistency** (Lexical Similarity): 디코딩된 텍스트로만 평가하여 **논리적 일관성/다양성 정밀 모델링 실패**

**INSIDE 프레임워크**: LLM의 **내부 상태(hidden states)**는 문장 전체의 **고도로 압축된 의미 정보**를 보존하므로, 이를 직접 활용하여 환각 검출 수행

**두 가지 핵심 기법**:
1. **EigenScore**: 문장 임베딩 공분산 행렬의 **고유값(eigenvalues)**으로 의미론적 일관성 측정
2. **Feature Clipping**: Penultimate layer의 **극단 활성화를 절단**하여 과도한 확신(overconfident) 생성 억제 → 자기 확신적 환각(self-consistent hallucination) 검출 가능

### 방법론

#### 1. EigenScore - 고유값 기반 의미 다양성 측정

**문장 임베딩 추출**:
- 각 응답 $\mathbf{y}^{(i)}$에 대해, 중간 레이어(layer $l = \text{int}(L/2)$)의 **마지막 토큰 임베딩**을 문장 임베딩 $\mathbf{z}^{(i)} \in \mathbb{R}^d$로 사용
  - 예: LLaMA-7B → layer 17/32, $d=4096$
  - 대안: 전체 토큰 평균 $\mathbf{z} = \frac{1}{T}\sum_{t=1}^T \mathbf{h}_t$ (ablation에서 마지막 토큰이 더 우수)

**공분산 행렬 계산**:

$$
\mathbf{\Sigma} = \mathbf{Z}^\top \cdot \mathbf{J}_d \cdot \mathbf{Z} \in \mathbb{R}^{K \times K}
$$

- $\mathbf{Z} = [\mathbf{z}_1, \mathbf{z}_2, \ldots, \mathbf{z}_K] \in \mathbb{R}^{d \times K}$: $K$개 샘플의 임베딩 행렬
- $\mathbf{J}_d = \mathbf{I}_d - \frac{1}{d}\mathbf{1}_d\mathbf{1}_d^\top$: Centering matrix (평균 제거)

**EigenScore 정의** (LogDet):

$$
E(\mathcal{Y}|\mathbf{x}, \theta) = \frac{1}{K} \log \det(\mathbf{\Sigma} + \alpha \cdot \mathbf{I}_K) = \frac{1}{K} \sum_{i=1}^K \log(\lambda_i)
$$

- $\lambda_i$: 정규화된 공분산 행렬 $\mathbf{\Sigma} + \alpha \mathbf{I}_K$의 고유값 (SVD로 계산)
- $\alpha = 0.001$: Regularization (full rank 보장)
- **낮은 EigenScore (작은 고유값) = 높은 의미 일관성 = 낮은 환각 가능성**
- **높은 EigenScore (큰 고유값) = 의미 다양성 높음 = 높은 환각 가능성**

**이론적 정당성 (Remark 1)**:

LogDet은 **Differential Entropy**와 동치:

$$
H_{\text{de}}(\mathbf{X}) = \frac{1}{2} \log \det(\mathbf{\Sigma}) + \frac{d}{2}(\log 2\pi + 1) = \frac{1}{2} \sum_{i=1}^d \log \lambda_i + C
$$

- 다변량 가aussian 분포 $\mathbf{X} \sim \mathcal{N}(\mathbf{\mu}, \mathbf{\Sigma})$의 differential entropy는 고유값으로 결정
- EigenScore는 **임베딩 공간에서의 엔트로피**를 직접 측정

**장점**:
1. **밀집된 의미 공간**: Logit/언어보다 임베딩이 의미 정보 더 많이 보존
2. **의미 등가성 해결**: "New York" vs "NYC" 같은 linguistic invariance 문제 해결
3. **세밀한 관계 포착**: 고유값으로 응답 간 correlation/divergence 정확히 측정

#### 2. Feature Clipping - 극단 활성화 절단으로 과확신 억제

**동기**:
- **Self-consistent hallucination**: LLM이 틀린 답을 여러 번 똑같이 반복 (일관성 기반 방법 실패)
- **관찰** (Figure 2): Penultimate layer에서 **극단적 활성화(extreme features)** 빈번 → 과확신 생성 유발

**Feature Clipping 함수**:

$$
FC(h) = \begin{cases}
h_{\min} & \text{if } h < h_{\min} \\
h & \text{if } h_{\min} \leq h \leq h_{\max} \\
h_{\max} & \text{if } h > h_{\max}
\end{cases}
$$

- $h$: Penultimate layer의 hidden embedding feature
- $h_{\min}, h_{\max}$: 절단 임계값 (동적 결정)

**임계값 결정 (Memory Bank 기반)**:
1. **Memory Bank**: 추론 시 $N=3000$개 토큰 임베딩 저장 (FIFO queue)
2. **Percentile 기반 임계값**: 각 뉴런에 대해 상위/하위 $p=0.2\%$ (three-sigma rule)
   - $h_{\min}$ = 0.2% percentile
   - $h_{\max}$ = 99.8% percentile
3. **Test-time adaptation**: 추론 중 동적으로 임계값 갱신

**효과**:
- 극단 활성화 절단 → **과확신 생성 감소** → Self-consistent hallucination 검출 가능
- OOD detection의 React (Sun et al., 2021) 기법과 유사

### 실험 결과

#### 주요 성능 (AUROC 기준)

**Table 1: 전체 데이터셋 비교**

| 모델 | 데이터셋 | Perplexity | LN-Entropy | Lexical Similarity | **EigenScore** |
|------|---------|------------|------------|-------------------|----------------|
| **LLaMA-7B** | CoQA | 64.1% | 68.7% | 74.8% | **80.4%** (+5.6%) |
| | SQuAD | 57.5% | 70.1% | 74.9% | **81.5%** (+6.6%) |
| | TriviaQA | 74.0% | 72.8% | 73.8% | **76.5%** (+2.7%) |
| | NQ | 83.6% | 83.4% | 82.6% | **82.7%** (-0.7%) |
| **LLaMA-13B** | CoQA | 63.2% | 68.8% | 74.8% | **79.5%** (+4.7%) |
| | SQuAD | 59.1% | 72.4% | 77.4% | **83.8%** (+6.4%) |
| | NQ | 84.7% | 83.4% | 82.9% | **83.0%** (-1.7%) |
| **OPT-6.7B** | CoQA | 60.9% | 61.4% | 71.2% | **76.5%** (+5.3%) |
| | SQuAD | 58.4% | 65.5% | 72.8% | **81.7%** (+8.9%) |

- **CoQA, SQuAD**: 긴 답변 → EigenScore 크게 우수 (최대 +8.9%)
- **TriviaQA**: 짧은 답변 (1~2단어) → 모든 방법 성능 비슷, Perplexity도 충분
- **NQ**: Perplexity/LN-Entropy가 최고 (EigenScore 약간 낮음)

**Table 2: Feature Clipping 효과**

| 방법 | CoQA (LLaMA-7B) | NQ (LLaMA-7B) |
|------|-----------------|---------------|
| LN-Entropy | 68.7% | 72.8% |
| LN-Entropy + FC | **70.0%** (+1.3%) | **73.4%** (+0.6%) |
| Lexical Similarity | 74.8% | 73.8% |
| Lexical Similarity + FC | **76.6%** (+1.8%) | **74.8%** (+1.0%) |
| EigenScore (w/o FC) | 79.3% | 75.9% |
| **EigenScore** | **80.4%** (+1.1%) | **76.5%** (+0.6%) |

- Feature Clipping은 **모든 방법에 일관되게 향상** 제공
- 최대 개선: Lexical Similarity + FC → +1.8% AUROC

**Appendix B: State-of-the-art 비교**

| 모델 | Semantic Entropy | SentSAR | SelfCheckGPT | **EigenScore** |
|------|-----------------|---------|--------------|----------------|
| OPT-6.7B (CoQA) | 63.1% / 71.7% | 69.8% / 72.2% | 70.2% / 74.1% | **71.9% / 77.5%** |
| LLaMA-7B (CoQA) | 64.9% / 68.2% | 70.4% / 65.8% | 68.7% / 72.9% | **71.2% / 75.7%** |
| LLaMA-13B (CoQA) | 65.3% / 66.7% | 71.4% / 64.7% | 68.1% / 77.0% | **72.8% / 79.8%** |

- **SelfCheckGPT**: 외부 BERT 모델 필요, EigenScore보다 낮음
- **Semantic Entropy**: 의미 클러스터링 + 엔트로피 (Kuhn et al., 2022), EigenScore가 최대 +7.1% 우수

#### Ablation Studies

**생성 개수 $K$의 영향** (Figure 3a, NQ dataset):
- $K < 15$: 성능 향상 (더 많은 샘플 = 더 정확한 공분산)
- $K \geq 15$: 성능 포화 (최적 trade-off: $K=20$)
- **EigenScore > Lexical Similarity > LN-Entropy**: 다중 생성 정보 활용 효율성

**레이어 선택** (Figure 3b, CoQA dataset):
- **중간 레이어 최고**: Layer 15~20 (총 32 layers 중)
- **Shallow/Final layers 열등**: 의미 정보 불충분
- **마지막 토큰 > 평균**: Last token이 문장 의미 더 잘 포착

**Correctness Threshold 민감도** (Table 3):
- ROUGE-L threshold 0.3 → 0.5 → 0.7: EigenScore 일관되게 우수
- **엄격한 기준일수록 성능 향상**: 76.4% → 80.8% → 83.5%

**하이퍼파라미터 민감도** (Figure 4):
- **Temperature**: 최적 범위 [0.1, 1.0], > 1.0에서 급격히 하락
- **Top-k**: 거의 영향 없음

### 기술적 세부사항

**Differential Entropy 연결**:
- Multivariate Gaussian $\mathbf{X} \sim \mathcal{N}(\mathbf{\mu}, \mathbf{\Sigma})$의 differential entropy:
  $$H_{\text{de}}(\mathbf{X}) = \frac{1}{2} \log \det(\mathbf{\Sigma}) + \text{const}$$
- EigenScore는 임베딩 공간에서의 **연속 엔트로피**를 근사

**Eigenvalue 해석**:
- **모든 고유값이 작음** ($\lambda_i \approx 0$): 임베딩들이 highly correlated → 의미 일관성 높음 → 낮은 환각
- **큰 고유값 존재**: 특정 방향으로 큰 분산 → 의미 다양성 높음 → 높은 환각
- **예시** (Case Study):
  - Correct answer: `electors` 10번 반복 → Eigenvalues = [4.87, 0.001, ..., 0.001] → EigenScore = -2.63 (신뢰)
  - Hallucination: `douglas macarthur`, `elvis presley`, `robin williams` 등 다양 → Eigenvalues = [3.32, 0.59, 0.37, ...] → EigenScore = -1.61 (불신)

**Feature Clipping의 메커니즘**:
- **Observation**: Overconfident hallucination은 penultimate layer에서 **극단 활성화 많음**
- **Clipping 효과**: 극단값 절단 → 모델이 다양한 답변 생성 → 일관성 깨짐 → 환각 검출 가능
- **예시** (Appendix H.3):
  - Before FC: `California` 10번 반복 → EigenScore = -2.42 (검출 실패)
  - After FC: `california`, `Washington`, `new york`, `michigan` 등 → EigenScore = -1.32 (검출 성공)

**계산 효율성** (Appendix D, Figure 5):
- **LLaMA-7B**: BaseLLM (0.9s) → EigenScore (9.0s, 10배)
- **SelfCheckGPT**: 90s (100배) - 외부 LLM 호출 필요
- **LN-Entropy/Lexical Similarity**: 9.0s (EigenScore와 동일)
- **Feature Clipping 오버헤드**: 0.06s (무시 가능)

### 한계 및 향후 연구

**Black-box 모델 적용 불가**:
- OpenAI GPT-4 같은 API 전용 모델에서는 **internal states 접근 불가**
- 해결책: Prompt-based uncertainty elicitation (Kadavath et al., 2022)

**샘플링 비용**:
- $K=10$ 생성 필요 → 추론 시간 10배 증가
- 완화 방안: Speculative sampling, continuous batching (vLLM)

**Mitigation 아닌 Detection만**:
- INSIDE는 환각 검출만 수행, 제거는 하지 않음
- 향후 연구: EigenScore를 loss function에 통합하여 훈련 시 환각 억제

**TruthfulQA 성능** (Appendix A):
- Zero-shot: 낮은 성능
- 50 in-distribution prompts: 81.3% (ITI 83.3%보다 낮음)
- ITI는 1024개 binary classifier 훈련 필요, generalization 제한

## 나의 생각

### 1. EigenScore의 이론적 우아함과 실용적 가치

**Differential Entropy 연결의 의미**: EigenScore가 단순 휴리스틱이 아니라 **정보 이론적으로 정당화된 지표**라는 점이 강점입니다. Multivariate Gaussian의 differential entropy가 $\frac{1}{2}\log\det(\mathbf{\Sigma})$로 표현되므로, EigenScore는 **임베딩 공간에서의 연속 엔트로피**를 직접 측정합니다. 이는 Semantic Entropy (Kuhn et al., 2022)가 **이산 확률 분포의 Shannon entropy**를 사용하는 것과 대비되며, **고차원 연속 공간의 불확실성**을 더 정확히 포착할 수 있습니다.

**Semantic Entropy 대비 장점**:
- **Semantic Entropy**: 응답을 의미 클러스터로 그룹화 후 $H = -\sum p_k \log p_k$ 계산 → 클러스터 간 확률 분포만 반영
- **EigenScore**: 임베딩의 **공분산 구조 전체**를 고유값으로 분해 → 클러스터 내/간 관계를 모두 포착
- 예: 두 클러스터 {A1, A2, A3}, {B1, B2}가 있을 때
  - Semantic Entropy: $p(C_1)=0.6, p(C_2)=0.4$ → $H \approx 0.97$
  - EigenScore: A 클러스터 내부 다양성, A-B 간 거리도 반영 → 더 세밀한 불확실성

**PCA/DPP와의 연결**: 논문이 인용한 대로, 고유값은 PCA (Wold et al., 1987)와 Determinantal Point Processes (Kulesza & Taskar, 2011)에서 **다양성 측정**의 핵심입니다. EigenScore는 이 전통을 환각 검출에 적용한 것으로, **데이터 다양성 = 불확실성**이라는 직관을 수학적으로 구현했습니다.

### 2. Feature Clipping - Self-Consistent Hallucination 해결의 실용성

**Semantic Entropy의 치명적 약점 극복**: 이 논문의 가장 큰 기여는 **"LLM이 틀린 답을 10번 똑같이 반복하면 어떻게 하나?"** 문제를 정면으로 다룬 것입니다. Case Study (Appendix H.1)에서:
- Q: "Who won the most Stanley Cups in history?"
- GT: Montreal Canadiens
- LLM: `the detroit red wings` 10번 반복
- **모든 기존 방법 실패**: Perplexity (0.366), LN-Entropy (0.025), Lexical Similarity (1.0), SelfCheckGPT (0.0), EigenScore (w/o FC) (-2.63)

Feature Clipping 적용 후: **EigenScore는 -2.63이지만 여전히 실패**합니다. 그러나 다른 예시에서는 성공:
- Before FC: `California` 10번 → EigenScore -2.42 (실패)
- After FC: `california`, `Washington`, `new york`, `michigan` → EigenScore -1.32 (성공)

**한계**: Feature Clipping이 **항상** self-consistent hallucination을 깨뜨리지는 못합니다. "detroit red wings" 예시처럼 일부는 여전히 검출 실패합니다. 이는 **극단 활성화가 환각의 충분조건이 아닌 필요조건**일 수 있음을 시사합니다.

**Semantic Energy와의 비교**: Semantic Energy (Ma et al., 2025) 논문도 동일한 문제를 다루지만 접근법이 다릅니다:
- **Semantic Energy**: Logits의 크기(magnitude)로 내재적 불확실성 측정 → K=1일 때도 logit 낮으면 불확실
- **INSIDE Feature Clipping**: Hidden states의 극단값 절단으로 생성 다양화 유도 → K=1을 K>1로 변환

두 방법은 **상호 보완적**입니다. 이상적으로는:
1. **1차 검증**: EigenScore (빠름, internal states만)
2. **2차 검증**: Semantic Energy (logits 추가 확인)
3. **3차 검증**: Lynx 70B Judge (느림, 정밀)

### 3. Middle Layer Last Token의 의미론적 중요성

**Ablation 결과의 통찰** (Figure 3b):
- **Shallow layers (1~10)**: 토큰 수준 정보, 문장 의미 불충분
- **Middle layers (15~20)**: 의미론적 추상화 최적, 환각 검출 최고
- **Final layers (25~32)**: Task-specific tuning으로 오염, 일반화 저하

이는 **Probing tasks** 연구 (Azaria & Mitchell, 2023)와 일치합니다: LLM의 중간 레이어가 **사실성(truthfulness)** 정보를 가장 잘 보존합니다.

**마지막 토큰 vs 평균 토큰**:
- **평균**: $\mathbf{z} = \frac{1}{T}\sum_{t=1}^T \mathbf{h}_t$ → 모든 토큰 정보 균등 반영
- **마지막 토큰**: $\mathbf{z} = \mathbf{h}_T$ → 문장 전체 context 누적

Ablation에서 **마지막 토큰이 우수**한 이유:
1. **Causal attention**: 마지막 토큰은 이전 모든 토큰을 attend → 전체 문맥 압축
2. **EOS 토큰 특성**: 문장 완성 판단 → 의미 완결성 포함
3. **평균의 노이즈**: 중간 토큰들은 local context에 과적합될 수 있음

### 4. 환각 탐지 기법 생태계 내 위치

**Reference-Free Detection 계보**:
- **1세대**: Token-level Perplexity → 의미 무시
- **2세대**: Semantic Entropy (Kuhn et al., 2022) → 언어 수준 의미 클러스터링
- **3세대 A**: **INSIDE EigenScore** → 내부 임베딩 공간 entropy
- **3세대 B**: **Semantic Energy** (Ma et al., 2025) → Logits 기반 epistemic uncertainty
- **4세대?**: Formal Verification (PCFG uncertainty) + 내부 상태 통합

**다른 기법과의 비교**:

| 방법 | 공간 | 샘플링 | 외부 모델 | White-box 필요 | AUROC (CoQA, LLaMA-7B) |
|------|------|--------|----------|----------------|------------------------|
| Perplexity | Logit | 단일 | ✗ | ✗ | 64.1% |
| Semantic Entropy | Language | 다중 | NLI/GPT-4 | ✗ | 64.9% |
| SelfCheckGPT | Language | 다중 | BERT | ✗ | 68.7% |
| Lexical Similarity | Language | 다중 | ✗ | ✗ | 74.8% |
| **INSIDE** | **Embedding** | **다중** | ✗ | **✓** | **80.4%** |
| Semantic Energy | Logit | 다중 | ✗ | ✓ | ~76% (추정) |
| Lynx | Language | 다중 | LLM Judge | ✗ | 87.4% |

**장점**:
- **외부 모델 불필요**: SelfCheckGPT처럼 BERT 호출 없음 (계산 10배 빠름)
- **의미 공간 직접 접근**: 언어 디코딩 우회 → linguistic invariance 해결
- **Feature Clipping 독창성**: Overconfident hallucination 대응

**단점**:
- **White-box 한정**: GPT-4 API에 적용 불가
- **샘플링 비용**: K=10~20 필요 (Lynx도 동일)
- **Detection only**: Mitigation 기능 없음

### 5. 실무 적용 시 고려사항

**Memory Bank 동적 관리**:
- $N=3000$ 토큰 저장 → 메모리 사용량: $3000 \times d \times 4 \text{ bytes}$
  - LLaMA-7B: $3000 \times 4096 \times 4 = 49.2 \text{ MB}$ (무시 가능)
- **FIFO queue**: 오래된 토큰 제거 → 최신 분포 반영
- **도메인 shift**: 의료 → 금융 전환 시 memory bank 초기화 필요

**Threshold 결정의 민감도**:
- Ablation (Table 8): Memory Bank (80.4%) > Pre-computed (79.9%) > Current sample (78.1%)
- **도메인별 프로파일링**: 각 도메인에서 optimal percentile 탐색 (0.2%가 항상 최적은 아님)

**Feature Clipping의 Trade-off**:
- **장점**: +1.1~1.8% AUROC 향상
- **단점**: 생성 품질 저하 가능성 (정상 응답도 다양화될 수 있음)
- **선택적 적용**: EigenScore 임계값 근처(애매한 경우)에만 FC 활성화

**다중 레이어 앙상블**:
- 논문: 중간 레이어 1개 사용
- **개선 아이디어**: Layer 15, 17, 20의 EigenScore 평균 → 더 robust할 수 있음

**Lynx와의 2단계 파이프라인**:
```python
# Pseudo-code
samples = [llm.generate(q) for _ in range(10)]

# Stage 1: INSIDE (fast)
eigen_score = compute_eigenscore(samples, middle_layer_embeddings)
if eigen_score > high_threshold:
    return "CERTAIN_HALLUCINATION"
elif eigen_score < low_threshold:
    return "CERTAIN_CORRECT"

# Stage 2: Lynx Judge (slow, precise)
lynx_score = lynx_judge(q, samples)
return "HALLUCINATION" if lynx_score > 0.5 else "CORRECT"
```

### 6. 향후 연구 방향 및 미해결 과제

**EigenScore를 훈련에 통합**:
- 현재: Post-hoc detection
- **제안**: Loss function에 추가
  $$\mathcal{L} = \mathcal{L}_{\text{CE}} + \lambda \cdot \text{EigenScore}(\text{embeddings})$$
- **목표**: 훈련 중 의미 일관성 높은 응답 생성 유도 (환각 mitigation)

**Covariance Matrix의 구조 활용**:
- 현재: 고유값 평균만 사용
- **확장**: 고유벡터 분석으로 **환각의 방향** 식별
  - 예: 첫 번째 고유벡터 = 주요 의미 축 (사실적 내용)
  - 나머지 고유벡터 = 노이즈/환각 방향
- **Projection**: 입력을 주요 고유벡터에 투영하여 환각 제거

**Multi-Modal Extension**:
- Vision-Language Models (GPT-4V, LLaVA): 이미지 + 텍스트 임베딩
- **통합 EigenScore**: $\mathbf{Z}_{\text{total}} = [\mathbf{Z}_{\text{vision}}, \mathbf{Z}_{\text{text}}]$ → 통합 공분산

**Semantic Energy와의 이론적 통합**:
- **가설**: EigenScore (임베딩 엔트로피) + Semantic Energy (logit 에너지) = 전체 불확실성
- **정보 이론적 분해**:
  $$\text{Total Uncertainty} = \underbrace{H(\text{embedding})}_{\text{EigenScore}} + \underbrace{I(\text{embedding}; \text{logit})}_{\text{Mutual Info}} + \underbrace{H(\text{logit}|\text{embedding})}_{\text{Semantic Energy}}$$

**Real-Time Streaming**:
- 현재: 전체 응답 생성 후 계산
- **온라인 버전**: 토큰 생성마다 incremental covariance update
  $$\mathbf{\Sigma}_{t+1} = \mathbf{\Sigma}_t + \Delta\mathbf{\Sigma}(\mathbf{h}_{t+1})$$
- **조기 중단**: EigenScore > threshold 시 생성 즉시 중단

**Black-box 근사**:
- API 모델에서 internal states 접근 불가 문제
- **대안**: Probing outputs으로 임베딩 근사
  - Multiple paraphrases 생성 → Sentence-BERT embedding → EigenScore 계산
  - 정확도는 낮지만 trade-off 가능

이 논문은 **임베딩 공간의 기하학적 구조**를 활용하여 환각을 검출하는 혁신적 접근법을 제시했습니다. EigenScore의 **이론적 정당성(differential entropy)**과 **실용적 효과(SOTA 성능)**, 그리고 Feature Clipping의 **overconfident hallucination 대응**은 환각 검출 연구의 중요한 진전입니다. 특히 **Semantic Energy와 상호 보완적**이므로, 두 방법을 결합하면 aleatoric + epistemic uncertainty를 모두 포착할 수 있을 것입니다.
