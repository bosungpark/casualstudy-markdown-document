# Why LLM Safety Guardrails Collapse After Fine-tuning: A Similarity Analysis Between Alignment and Fine-tuning Datasets

## 출처
- **링크**: https://arxiv.org/abs/2506.05346
- **저자**: Lei Hsiung, Tianyu Pang, Yung-Chen Tang, Linyue Song, Tsung-Yi Ho, Pin-Yu Chen, Yaoqing Yang (Dartmouth College, EPFL, UC Berkeley, CUHK, IBM Research)
- **제출일**: 2025년 6월 5일

---

## AI 요약

### 배경 및 문제 정의

대형 언어 모델(LLM)은 특정 작업에 맞춰 다운스트림 파인튜닝을 거치는 것이 일반적이다. Google, Meta, Mistral AI, Alibaba 등은 안전성과 공정성을 우선시하여 **안전 정렬(safety alignment)**된 오픈 소스 모델을 공개하고 있다. 그러나 이러한 모델들이 제3자에 의해 추가 파인튜닝될 경우, 내장된 안전 가드레일(safety guardrails)이 손상되는 **재일브레이킹(jailbreaking)** 현상이 발생한다.

**핵심 문제점**:
- 기존 방어 전략은 주로 가드레일이 이미 손상된 후 사후 대응에 집중
- 파인튜닝 중 유해 그래디언트 제거나 안전 정렬 지속적 강화에만 초점
- **근본 원인인 업스트림 안전 정렬 데이터의 역할은 간과됨**

놀랍게도, **완전히 무해한(benign) 데이터로 파인튜닝해도** 안전 가드레일이 무너질 수 있다는 것이 실험적으로 확인되었다.

### 핵심 가설: 표현 유사도(Representation Similarity)

본 논문은 안전 가드레일의 취약성을 **업스트림 정렬 데이터셋(최초 학습)과 다운스트림 파인튜닝(추가 학습) 태스크 간의 표현 유사도** 관점에서 조사한다.

**가설**:
1. **높은 유사도**: 업스트림 정렬 데이터와 다운스트림 파인튜닝 데이터가 매우 유사하면, 가드레일이 좁은 분포에 형성되어 과적합(overfitting)되고 재일브레이크에 취약
2. **낮은 유사도**: 두 데이터셋 간 유사도가 낮으면, 가드레일이 과적합에 덜 취약하고 파인튜닝에 더 견고함

### 연구 방법론

#### 1. 예비 실험: 클러스터링을 통한 유해 서브셋 발견

기존 연구(He et al., 2024)는 100개의 유해 데이터를 앵커로 사용해 표현 매칭으로 유해 서브셋을 식별했다. 본 연구는 **앵커 없이** k-means 클러스터링을 적용하여:
- Alpaca 데이터셋을 20개 클러스터로 그룹화
- 높은 내부 유사도를 가진 리스트 형식 질문 클러스터 선택
- 결과: 기존 Top-100 Harmful 대비 **15.7% 더 높은 유해성** 달성

**RQ1 답변**: 클러스터링 기법으로 높은 내부 유사도를 가진 유해 서브셋을 앵커 없이 식별 가능

#### 2. 업스트림-다운스트림 유사도 분석

**데이터셋 선택 방법**:
- 각 다운스트림 태스크 샘플에 대해, 업스트림 안전 정렬 데이터에서 코사인 유사도 계산
- Top-K (가장 유사한) → **High-Sim 서브셋**
- Bottom-K (가장 비유사한) → **Low-Sim 서브셋**
- Random → **Random 서브셋** (베이스라인)

**실험 설계**:
1. Llama-2-7B-Base를 UltraChat 데이터로 instruction fine-tuning
2. BeaverTails 데이터셋에서 선택한 서브셋(High/Low/Random, 1K 또는 5K)으로 안전 정렬
3. 유해/무해 다운스트림 태스크로 파인튜닝
4. HEx-PHI 벤치마크로 Harmfulness Score(HS) 측정

**다운스트림 태스크**:
- **유해 태스크**: 
  - List Examples (Alpaca에서 100개 리스트 형식 예제)
  - Pure Bad Examples (Qi et al.의 100개 명시적 유해 샘플)
- **무해 태스크**:
  - Alpaca (52K 서브셋)
  - SAMSum (16K 대화 요약)

**다운스트림 방어 기법 평가**:
- SafeInstr: 안전 샘플을 파인튜닝 데이터에 추가 (10% 유해, 3% 무해 태스크)
- BEA (Backdoor Enhanced Alignment): 트리거-안전 응답 쌍을 백도어로 삽입

#### 3. 평가 지표

- **안전성**: Harmfulness Score (HS) - 유해 출력 비율
- **유용성**: 
  - MT-Bench (1-10 점수, GPT-3.5로 평가)
  - Rouge-1 F1 score (SAMSum)

### 주요 실험 결과

#### 핵심 발견 1: 높은 유사도는 안전성을 심각하게 훼손

**Llama-2-7B 결과** (Table 1):
- Low-Sim은 High-Sim 대비 **최대 10.33% 낮은 HS** 달성
- 모든 다운스트림 태스크(유해/무해)에서 일관된 패턴
- 안전 정렬 데이터 크기가 클수록 더 안전 (None < 1K < 5K < Full 7.7K)

**Llama-2-13B 결과** (Table 2):
- 7B 모델과 동일한 패턴 확인
- 모델 스케일에 관계없이 유사도 효과는 일관됨

**Gemma-2-2B/9B 결과** (Appendix):
- 다양한 모델 아키텍처에서도 동일한 현상 재현
- 일반화 가능성 입증

**구체적 비교**:
- List 태스크 (Llama-2-7B, 5K):
  - High-Sim: HS 78.33%
  - Low-Sim: HS 76.67%
  - 차이: 1.66%p
  
- Alpaca 태스크 (Llama-2-7B, 5K):
  - High-Sim: HS 62.00%
  - Low-Sim: HS 51.67%
  - 차이: 10.33%p ← **최대 차이**

#### 핵심 발견 2: 업스트림 + 다운스트림 방어의 상승 효과 -> 쉽게 풀면 업스트림, 다운스트림은 상호 독립적이다!

SafeInstr, BEA 같은 다운스트림 방어를 적용해도:
- Low-Sim이 High-Sim보다 **여전히 더 안전**
- 즉, 업스트림 정렬 데이터 선택과 다운스트림 방어는 **독립적이고 상호 보완적**

**SafeInstr 결과** (Llama-2-7B, List 태스크):
- High-Sim + SafeInstr: HS 74.33%
- Low-Sim + SafeInstr: HS 72.67%
- 다운스트림 방어가 있어도 유사도 효과는 유지

#### 핵심 발견 3: 유용성(Utility) 유지

Low-Sim 사용이 안전성을 향상시키면서도:
- MT-Bench 점수는 High-Sim과 유사하거나 더 높음
- 즉, **안전성-유용성 트레이드오프 없음**

### 시사점

#### 1. 데이터 프라이버시의 중요성

공개된 안전 정렬 데이터셋은 악의적 행위자가 다음을 가능하게 함:
- 정렬 데이터와 높은 유사도를 가진 파인튜닝 데이터 의도적 구성
- 가드레일 체계적으로 무력화

**해결책**: 업스트림 안전 정렬 데이터의 **기밀성 유지**

#### 2. 표현 유사도 기반 모델 선택 파이프라인

파인튜닝 서비스 제공자(OpenAI, Anthropic 등)를 위한 실용적 가이드라인:

**제안 파이프라인** (Figure 4b):
1. 사용자가 제공한 파인튜닝 데이터셋 수신
2. 여러 안전 정렬된 후보 모델에 대해 표현 유사도 계산
3. **낮은 유사도**를 가진 모델 선택 (위험 감소)
4. 선택된 모델로 파인튜닝 수행
5. 결과: 태스크 성능 향상 + 안전 가드레일 보존

#### 3. 기존 방어 기법과의 통합

본 접근법은 다음과 같은 기존 방어와 **계층적으로 결합 가능**:
- Post-hoc pruning (Huang et al., 2025a)
- Constraint-based fine-tuning (Hsu et al., 2024)
- Residual output filters (Ji et al., 2024a)

→ 전체 배포 파이프라인에서 다층 방어 전략 구축

### 핵심 개념

**Catastrophic Forgetting vs Representation Similarity**:
- 기존: 파인튜닝 시 이전 지식이 손실되는 재앙적 망각(catastrophic forgetting) 관점
- 본 연구: 업스트림-다운스트림 데이터 표현 공간의 기하학적 관계로 재해석

**Representation Space**:
- 모델의 마지막 은닉 상태(final hidden state)를 특징 벡터로 사용
- 코사인 유사도로 데이터 간 관계 측정
- 높은 유사도 = 표현 공간에서 가까이 위치 = 과적합 위험

**Bounded vs Unbounded Distribution**:
- High-Sim: 정렬 데이터가 특정 분포에 집중 (bounded) → 취약
- Low-Sim: 정렬 데이터가 넓은 분포 커버 (unbounded) → 견고

### 한계점

1. **완전한 방지는 불가능**: Low-Sim도 유해 파인튜닝에는 여전히 취약 (단지 High-Sim보다 나을 뿐)
2. **표현 추출 비용**: 대규모 데이터셋에서 모든 샘플의 표현 계산은 계산 비용 발생
3. **동적 환경**: 공격자가 Low-Sim 전략을 알고 있다면 우회 가능성
4. **평가 벤치마크 한계**: HEx-PHI와 Beaver-Dam-7B의 유해성 판단이 완벽하지 않을 수 있음

---

## 내가 얻은 인사이트

왜 어떤 안전 정렬은 더 쉽게 깨지는가에 대한 내용임. 파인 튜닝시에는 안전 정렬이 너무 한 쪽으로 과적합되지 않게 아래와 같이 하기.

- 안전 정렬 데이터 수집 시 **다양성**을 의도적으로 확보
- 특정 도메인/형식에 편중되지 않도록 데이터 분포 설계
- 정렬 데이터셋 구축 시 표현 공간에서의 커버리지를 정량적으로 측정