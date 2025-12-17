# A Survey of Large Language Models

## 출처
- **링크**: https://arxiv.org/abs/2303.18223
- **저자**: Wayne Xin Zhao, Kun Zhou, Junyi Li 외 18명 (Renmin University of China)
- **발표**: 2023년 3월 (최신 버전 v16: 2025년 3월)
- **GitHub**: https://github.com/RUCAIBox/LLMSurvey

---

## AI 요약

### 논문 개요
이 Survey는 LLM의 발전 과정을 **Statistical LM → Neural LM → PLM → LLM**의 4세대로 구분하고, LLM의 핵심 기술을 **Pre-training, Adaptation Tuning, Utilization, Capacity Evaluation**의 4가지 관점에서 체계적으로 정리한다.

### 핵심 구조
```
┌─────────────────────────────────────────────────────────────┐
│                    논문의 4대 축                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [1] Pre-training         [2] Adaptation Tuning             │
│  ├─ 데이터 수집/처리       ├─ Instruction Tuning (IT)        │
│  ├─ 아키텍처 설계          ├─ RLHF (Alignment)               │
│  └─ 학습 전략/Scaling Law  └─ Parameter-Efficient FT        │
│                                                              │
│  [3] Utilization          [4] Capacity Evaluation           │
│  ├─ In-Context Learning    ├─ Emergent Abilities            │
│  ├─ Chain-of-Thought       ├─ Benchmark (MMLU 등)           │
│  └─ Planning/Tool Use      └─ Human Evaluation              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1. PLM vs LLM: 3가지 핵심 차이

| 구분 | PLM (BERT 등) | LLM (GPT-3 이상) |
|------|--------------|------------------|
| **Emergent Abilities** | 없음 | In-Context Learning, CoT 등 창발 |
| **사용 방식** | Fine-tuning 필수 | Prompting으로 바로 사용 |
| **개발 방식** | 연구와 엔지니어링 분리 | 연구+엔지니어링 통합 필요 |

### 2. GPT 시리즈 진화 경로
```
GPT-1 (2018)     GPT-2 (2019)     GPT-3 (2020)     ChatGPT (2022)    GPT-4 (2023)
   │                │                │                  │                │
   ▼                ▼                ▼                  ▼                ▼
117M params     1.5B params      175B params      RLHF 적용         Multimodal
Decoder-only    Zero-shot 시도   ICL 공식화        대화 최적화        Safety 강화
```

- **GPT-3가 핵심 전환점**: Scaling을 통해 In-Context Learning이 "창발"
- **InstructGPT/ChatGPT**: RLHF 3단계 알고리즘 정립 (SFT → Reward Model → PPO)

### 3. Scaling Law와 Emergent Abilities

**Scaling Law** (Kaplan et al., Hoffmann et al.):
- 모델 크기(N), 데이터 크기(D), 연산량(C)에 따라 성능이 power-law로 향상
- Chinchilla 최적: 파라미터 수와 토큰 수를 1:20 비율로 균형

**Emergent Abilities**:
- 특정 스케일(~10B+ params) 이상에서 갑자기 나타나는 능력
- 예: ICL, CoT, Instruction Following
- 논쟁: 연속적 향상의 불연속적 측정 결과일 수 있음

### 4. 아키텍처 비교

| 유형 | Attention 패턴 | 대표 모델 | 특징 |
|------|---------------|----------|------|
| **Encoder-Only** | Bidirectional (입력 전체를 한 번에 보고 문맥을 양방향으로 이해) | BERT, RoBERTa | 이해 태스크, 현재 LLM에서 미사용 |
| **Decoder-Only** | Causal (Unidirectional, 이전 토큰까지만 보고, 다음 토큰을 예측) | GPT, LLaMA, Mistral | 생성 태스크, **현재 주류** |
| **Encoder-Decoder** | 둘 다 (“인코더”가 전체적으로 이해한 뒤, “디코더”가 그 정보를 바탕으로 새로운 출력을 생성하는 방식) | T5, BART | Seq2Seq 태스크 |

### 5. Adaptation Tuning 핵심

**Instruction Tuning**:
- 자연어 지시문 + 입력 + 출력 형식의 데이터로 Fine-tuning
- 다양한 태스크 일반화 능력 향상

**RLHF 3단계**:
```
1. SFT (Supervised Fine-Tuning)
   └─ 인간 시연 데이터로 기본 행동 학습
   
2. Reward Model 학습
   └─ 인간 선호도 비교 데이터로 보상 함수 학습
   
3. PPO (Proximal Policy Optimization)
   └─ Reward Model을 사용해 정책 최적화
```

**Alignment 목표**: Helpful, Honest, Harmless (3H)

### 6. Utilization (활용 방법)

**In-Context Learning (ICL)**:
- Few-shot: 프롬프트에 예시 포함
- Zero-shot: 지시문만으로 태스크 수행
- 예시 선택과 순서가 성능에 큰 영향

**Chain-of-Thought (CoT)**:
- 중간 추론 단계를 명시적으로 생성
- "Let's think step by step" 같은 트리거로 유도

**Planning & Tool Use**:
- 복잡한 태스크를 하위 태스크로 분해
- 외부 도구 (검색, 계산기 등) 활용

### 7. Capacity Evaluation

**주요 벤치마크**:
| 벤치마크 | 평가 대상 |
|---------|----------|
| MMLU | 다양한 학문 분야 지식 |
| HumanEval | 코드 생성 |
| GSM8K | 수학적 추론 |
| TruthfulQA | 사실성/환각 |
| HellaSwag | 상식 추론 |

**평가 방법**:
- 자동 평가: 정확도, BLEU, Pass@k
- 인간 평가: 유용성, 안전성, 선호도
- LLM-as-Judge: GPT-4 등을 평가자로 활용

---

## 내가 얻은 인사이트
