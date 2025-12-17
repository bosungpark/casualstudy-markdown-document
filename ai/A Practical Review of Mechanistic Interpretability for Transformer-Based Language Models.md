# A Practical Review of Mechanistic Interpretability for Transformer-Based Language Models

## 출처
- **링크**: https://arxiv.org/abs/2407.02646
- **저자**: Daking Rai, Yilun Zhou, Shi Feng, Abulhair Saparov, Ziyu Yao (George Mason University 등)
- **발표**: 2024년 7월 (최신 버전 v4: 2025년 10월, ICML 2025 Tutorial)
- **GitHub**: https://github.com/Dakingrai/awesome-mechanistic-interpretability-lm-papers

---

## AI 요약

### 논문 개요
이 Survey는 **Mechanistic Interpretability (MI)**를 체계적으로 정리한 입문자용 로드맵이다. MI는 신경망의 내부 계산을 역공학(reverse-engineering)하여 인간이 이해할 수 있는 메커니즘으로 설명하려는 분야다. 이전 Zhao et al. Survey가 "LLM이 무엇을 하는가"를 다뤘다면, 이 논문은 "LLM이 어떻게 작동하는가"를 다룬다.

### 핵심 구조: MI의 3가지 기본 객체
```
┌─────────────────────────────────────────────────────────────┐
│          Mechanistic Interpretability의 기본 객체            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [1] Residual Stream (잔차 스트림)                           │
│  ├─ Transformer의 "정보 고속도로"                           │
│  ├─ 모든 레이어가 읽고 쓰는 공유 공간                        │
│  └─ 임베딩 → ... → 최종 예측까지 정보 누적                  │
│                                                              │
│  [2] Features (특징)                                         │
│  ├─ 모델이 학습한 개념/패턴의 표현                          │
│  ├─ 활성화 공간의 방향(direction)으로 인코딩                │
│  └─ 문제: Superposition으로 인해 해석 어려움                │
│                                                              │
│  [3] Circuits (회로)                                         │
│  ├─ 특정 태스크를 수행하는 컴포넌트들의 연결                │
│  ├─ Attention Head + MLP + 연결 = 알고리즘                  │
│  └─ 예: Induction Circuit (패턴 반복 감지)                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1. Residual Stream: Transformer의 통신 채널
```
┌─────────────────────────────────────────────────────────────┐
│                    Residual Stream 개념도                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Token "The capital of France is" → [?]                     │
│                                                              │
│  Embedding ──┬──────────────────────────────────────────→   │
│              │                                               │
│              ↓  +Attn₁  +MLP₁  +Attn₂  +MLP₂  ...  Unembed │
│  ──────────────────────────────────────────────────────────→│
│              ↑          ↑       ↑       ↑                   │
│           [읽기]     [쓰기]   [읽기]   [쓰기]                 │
│                                                              │
│  • 각 컴포넌트는 RS를 읽고(linear projection)               │
│  • 결과를 RS에 더함(additive)                               │
│  • 깊이 선형 구조 → Virtual Weights로 분석 가능             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**핵심 인사이트**:
- Attention은 정보를 **이동**(토큰 간 복사)
- MLP/FFN은 정보를 **변환**(지식 검색/추가)
- Residual Stream은 모델의 "현재 추측"을 레이어별로 정제

### 2. Superposition 문제와 해결책

**문제: Polysemantic Neurons**
- 모델은 뉴런 수보다 더 많은 Feature를 표현해야 함
- 결과: 하나의 뉴런이 여러 무관한 개념에 반응 (polysemantic)
- 예: 뉴런 A가 "고양이", "프랑스어", "숫자 7"에 모두 활성화

**해결책: Sparse Autoencoders (SAEs)**
```
┌─────────────────────────────────────────────────────────────┐
│               Sparse Autoencoder 개념도                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  원본 활성화 (d차원, polysemantic)                          │
│       ↓                                                      │
│  ┌─────────┐                                                │
│  │ Encoder │ → s차원 (s >> d, sparse)                      │
│  └─────────┘                                                │
│       ↓                                                      │
│  [0, 0, 0.8, 0, 0, 0, 0.3, 0, 0, 0, ...]  ← Monosemantic!  │
│       ↓                                                      │
│  ┌─────────┐                                                │
│  │ Decoder │ → d차원 (복원)                                 │
│  └─────────┘                                                │
│                                                              │
│  • 각 SAE 특징 = 하나의 해석 가능한 개념                    │
│  • 예: "도시 이름", "프랑스 관련", "대문자"                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3. MI 핵심 기법들

| 기법 | 설명 | 용도 |
|------|------|------|
| **Logit Lens** | 중간 레이어 활성화를 어휘 공간에 투영 | 레이어별 예측 변화 추적 |
| **Activation Patching** | Clean/Corrupted 실행 간 활성화 교체 | 인과적 중요 컴포넌트 식별 |
| **Path Patching** | 특정 경로만 선택적 패칭 | 회로 내 정보 흐름 추적 |
| **Probing** | 활성화로 특정 속성 분류기 학습 | 특징 인코딩 여부 확인 |
| **SAE** | 희소 표현으로 분해 | Superposition 해결 |

### 4. 발견된 주요 회로들

**Induction Circuit (In-Context Learning의 핵심)**
```
입력: "Mr D urs ley was thin. Mr D" → 예측: "urs"

┌─────────────────────────────────────────────────────────────┐
│  Previous Token Head (Layer N)                              │
│  └─ "D" 다음에 "urs"가 왔다는 정보를 RS에 기록             │
│                        ↓                                     │
│  Induction Head (Layer N+1)                                 │
│  └─ 현재 "D" 위치에서 이전 패턴 찾아 "urs" 예측           │
└─────────────────────────────────────────────────────────────┘

- 2개의 Attention Head가 협력
- ICL 능력의 핵심 메커니즘
- 훈련 중 갑자기 출현 (Phase Transition)
```

**Indirect Object Identification (IOI) Circuit**
- 입력: "Mary gave a book to John. She gave it to"
- 예측: "John" (not "Mary")
- 발견: Name Mover Head, S-Inhibition Head 등 여러 헤드가 협력

**Factual Recall Circuit**
- 입력: "The capital of France is"
- 예측: "Paris"
- MLP 레이어가 Key-Value 메모리로 작동
- "France" 패턴 감지 → "Paris" 관련 활성화 증폭

### 5. MI 연구의 태스크 중심 분류
```
┌─────────────────────────────────────────────────────────────┐
│              MI 연구 태스크 분류 체계                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [Feature Study] 특징 연구                                  │
│  ├─ Targeted: 특정 특징 존재 여부 확인                      │
│  └─ Open-ended: SAE로 모든 특징 발견                        │
│                                                              │
│  [Circuit Study] 회로 연구                                  │
│  ├─ 특정 행동의 책임 컴포넌트 식별                          │
│  └─ 컴포넌트 간 정보 흐름 분석                              │
│                                                              │
│  [Universality] 보편성 연구                                 │
│  ├─ 다른 모델에서도 같은 특징/회로 존재?                   │
│  └─ 결과: 혼재 (1-5%만 명확히 공유)                        │
│                                                              │
│  [Capability Study] 능력 연구                               │
│  ├─ ICL, Reasoning, Factual Recall 메커니즘                │
│  └─ Grokking, Phase Transition 현상 분석                   │
│                                                              │
│  [Application] 응용                                          │
│  ├─ Model Editing (사실 수정)                               │
│  ├─ Safety (위험 특징 억제)                                 │
│  └─ Hallucination 감지                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 6. Attention Head vs MLP의 역할 분담

| 컴포넌트 | 역할 | 비유 |
|---------|------|------|
| **Attention Head** | 토큰 간 정보 이동 | "우체부" - 필요한 정보를 복사/이동 |
| **MLP/FFN** | 지식 저장 및 변환 | "도서관" - Key-Value 메모리로 사실 저장 |
| **Residual Stream** | 정보 누적 및 전달 | "고속도로" - 모든 정보가 흐르는 채널 |
| **LayerNorm** | 안정화 | "속도 조절기" - 값 폭발 방지 |

### 7. Open Challenges

1. **Scalability**: 작은 모델(GPT-2)에서 발견한 회로가 대형 모델에도 적용?
2. **Ground Truth 부재**: 해석의 정확성을 어떻게 검증?
3. **Superposition 완전 해결**: SAE도 완벽하지 않음
4. **Universality 한계**: 모델 간 전이 가능성 불확실
5. **Automation**: 수동 분석에서 자동화로 전환 필요

---

## 내가 얻은 인사이트
