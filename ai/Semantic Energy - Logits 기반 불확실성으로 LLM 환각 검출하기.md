# Semantic Energy - Logits 기반 불확실성으로 LLM 환각 검출하기

## 출처

- **논문**: Semantic Energy: Detecting LLM Hallucination Beyond Entropy
- **저자**: Huan Ma (Tianjin University, Baidu), Jiadong Pan (CAS, Baidu), Joey Tianyi Zhou (A*STAR CFAR), Changqing Zhang (Tianjin University), Hua Wu & Haifeng Wang (Baidu) 외
- **발표**: arXiv:2508.14496v2 (2025년 8월)
- **링크**: https://arxiv.org/abs/2508.14496
- **코드**: https://github.com/MaHuanAAA/SemanticEnergy

## AI 요약

### 핵심 아이디어

**Semantic Entropy의 치명적 결함**: Semantic Entropy는 다중 샘플링 후 의미론적 클러스터의 확률 분포로 불확실성을 측정하지만, **모든 샘플이 동일한 의미(K=1)를 가질 때 엔트로피가 0**이 되어 신뢰도가 높다고 잘못 판단합니다. 그러나 LLM은 **틀린 답을 여러 번 똑같이 반복하는 경향**이 있어, 일부 데이터셋에서는 **의미가 일관된 샘플의 50%가 실제로는 오답**입니다.

**Semantic Energy**: **logits(softmax 이전 값)을 Boltzmann 에너지 분포로 모델링**하여 모델의 **내재적 불확실성(epistemic uncertainty)**을 포착합니다. Semantic Entropy는 **확률 정규화 과정에서 logits의 강도(magnitude) 정보를 소실**하지만, Semantic Energy는 **logits를 직접 사용**하여 모델이 해당 도메인에 충분히 학습되었는지를 반영합니다.

### 방법론

#### 1. Semantic Entropy의 한계 (Failure Case)

**시나리오**:
- 질문 Q₂: 모델이 충분히 학습된 도메인 (confident)
- 질문 Q₃: 모델이 학습이 부족한 도메인 (uncertain)
- 각 질문에 대해 5개 샘플 생성 → 모두 동일 의미로 클러스터링 (K=1)

**Semantic Entropy 결과**:
- H_SE(Q₂) = 0, H_SE(Q₃) = 0 → 둘 다 신뢰도 높다고 판단
- 문제: Q₃는 5개 모두 틀린 답인데도 0 엔트로피

**근본 원인**:
- 확률 기반 엔트로피는 **상대적 가능성(relative likelihood)**만 반영
- LLM 응답은 다중 토큰의 결합 확률이므로 partition function 근사 오차 누적
- 두 가정 실패: (1) 훈련 분포 = 실제 분포, (2) 모델 출력 = 훈련 분포

#### 2. Boltzmann 에너지 기반 불확실성

**Boltzmann 분포**:

$$
p(x_t^{(i)}) = \frac{e^{-E_t^{(i)}/k\tau}}{Z_t}
$$

- $E_t^{(i)}$: 토큰 $x_t^{(i)}$의 에너지 (LLM에서는 $E(x_t^{(i)}, \theta) = -z_\theta(x_t^{(i)})$, 즉 **logit의 음수**)
- $k\tau$: 온도 (LLM 훈련 시 기본값 1)
- $Z_t$: partition function (전체 어휘 $\mathcal{V}$에 대한 정규화)

**시퀀스 수준 에너지**:

$$
\tilde{E}(\mathbf{x}^{(i)}) = \frac{1}{T_i} \sum_{t=1}^{T_i} \tilde{E}_t^{(i)} = \frac{1}{T_i} \sum_{t=1}^{T_i} (-z_\theta(x_t^{(i)}))
$$

**의미론적 클러스터 에너지** (Boltzmann formulation):

$$
\tilde{E}_{\text{Bolt}}(\mathbb{C}_k) = \frac{1}{n} \sum_{\mathbf{x}^{(i)} \in \mathbb{C}_k} \tilde{E}(\mathbf{x}^{(i)})
$$

**최종 불확실성 지표**:

$$
U(\mathbf{x}^{(i)}) = \frac{1}{nT_i} \sum_{\mathbf{x}^{(i)} \in \mathbb{C}_k} \sum_{t=1}^{T_i} (-z_\theta(x_t^{(i)}))
$$

- **낮은 에너지 = 낮은 불확실성 = 높은 신뢰도**
- 열역학 비유: 낮은 에너지 상태는 안정적, 높은 에너지 상태는 불안정

#### 3. Semantic Clustering의 필요성

**LogTokU와의 차이점**:
- LogTokU: 단일 응답의 에너지를 직접 사용
- **문제**: 동일 의미 클러스터 내에서도 개별 응답의 에너지는 다를 수 있음

**Semantic Energy**: 의미론적으로 동일한 응답들의 **평균 에너지**를 사용
- Ablation Study (Fig. 3): 의미론적 클러스터링 사용 시 불확실성 추정 정확도 크게 향상

### 실험 결과

#### 주요 성능 (AUROC 기준)

**전체 데이터셋** (Table 1):

| 모델 | 데이터셋 | Semantic Entropy | Semantic Energy | 개선폭 |
|------|---------|-----------------|-----------------|--------|
| Qwen3-8B | CSQA | 71.6% | **76.1%** | +4.5% |
| Qwen3-8B | TriviaQA | - | - | +5.0%↑ |
| ERNIE-21B-A3B | CSQA | 77.4% | **80.2%** | +2.8% |
| ERNIE-21B-A3B | TriviaQA | - | - | +5.0%↑ |

**단일 클러스터 시나리오** (Table 2, K=1인 경우):

| 모델 | 데이터셋 | Semantic Entropy | Semantic Energy | 개선폭 |
|------|---------|-----------------|-----------------|--------|
| Qwen3-8B | CSQA | ~50% (무작위) | **63%+** | **+13%** |
| Qwen3-8B | TriviaQA | ~50% (무작위) | **63%+** | **+13%** |

- **Semantic Entropy 완전 실패**: H_SE=0 항상, AUPR은 양성 샘플 비율과 동일 (무의미한 지표)
- **Semantic Energy 작동**: 모델 내재적 불확실성으로 오답 구분 가능

#### Think Mode 실험 (Fig. 2)

- Qwen-8B에서 think mode 활성화 (`<think>...</think>` 태그 생성 후 제거)
- Semantic Energy가 일관되게 Semantic Entropy 능가

#### Semantic Clustering 효과 (Fig. 3)

- **Without Semantic**: 단일 응답 에너지 사용 → 낮은 AUROC
- **With Semantic**: 클러스터 평균 에너지 사용 → AUROC 크게 향상

### 기술적 세부사항

**logits vs probabilities**:
- Probabilities: 정규화 과정에서 logits의 **절대적 크기(magnitude)** 정보 소실
- Logits: OOD 검출 연구(Liu et al., 2020)에서 **InD 샘플의 logit이 OOD 샘플보다 유의미하게 높음** 확인
- LogTokU (Ma et al., 2025): 확률 정규화가 강도 정보를 버리므로 내재적 불확실성 표현력 제한

**에너지 vs 엔트로피**:
- **Aleatoric Uncertainty**: 생성 과정의 내재적 랜덤성 (Semantic Entropy 포착)
- **Epistemic Uncertainty**: 모델의 지식 부족 (Semantic Energy 포착)

**Thermodynamic 비유**:
- 물리학: 낮은 에너지 상태 = 안정적, 높은 에너지 상태 = 불안정/무작위
- LLM: 낮은 logit = 모델이 덜 훈련됨 = 높은 불확실성

### 한계 및 향후 연구

**Cross-Entropy Loss의 한계**:
- 현재 LLM 훈련: Cross-Entropy Loss는 **logits의 스케일에 불변(scale-invariant)**
- Logits ≠ 진정한 에너지: 네트워크 초기화와 정규화의 암묵적 제약으로 **에너지 유사 특성**만 가짐
- **향후 방향**: Cross-Entropy Loss의 한계를 훈련 과정에서 해결하여 모델이 자신의 불확실성을 더 정확히 포착하도록 개선

**제한 사항**:
- Semantic Energy는 완벽한 최종 솔루션이 아님
- 더 나은 불확실성 추정을 위해서는 훈련 목표 함수 자체의 개선 필요

## 나의 생각

1. 왜좋음? -> 자기 확신에 찬 오답을 잡을 수 있으므로
2. 여러 답이 얼마나 다양하냐가 아닌 각각의 답이 얼마나 자신감 있게 발화되었는가를 검증
3. 틀린 답을 확신있게 말하는 것이 위험한 의료/금융 도메인 등에 유용할 것으로 보임
