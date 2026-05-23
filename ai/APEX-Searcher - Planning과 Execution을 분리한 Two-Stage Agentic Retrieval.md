# APEX-Searcher - Planning과 Execution을 분리한 Two-Stage Agentic Retrieval

## 출처
- **논문**: APEX-Searcher: Augmenting LLMs' Search Capabilities through Agentic Planning and Execution
- **저자**: Kun Chen, Qingchao Kong, Zhao Feifei, Wenji Mao
- **링크**: https://arxiv.org/abs/2603.13853
- **분야**: cs.CL / cs.AI
- **발행**: 2026년 3월 14일 (v1), 3월 17일 (v2)

---

## AI 요약

### 1. 무엇을 해결하려는가

복잡한 multi-hop 질문(예: "A가 만든 회사를 인수한 기업의 CEO가 다닌 학교는?")은 단일 round 검색으로 풀리지 않는다. 그렇다고 단순히 검색을 여러 번 돌리면 두 가지 함정에 빠진다.

| 문제 | 설명 |
|------|------|
| **모호한 검색 경로** | 어떤 방향으로 검색을 진전시킬지 모델이 갈피를 못 잡음 |
| **희소 보상(sparse reward)** | RL로 학습하려 해도 정답까지 도달해야만 신호가 나옴 → 학습 어려움 |

> "단일 라운드 검색은 정확한 추론과 문제 해결에 불충분하다... 기존 다중 라운드 반복 검색 방식은 모호한 검색 경로와 희소 보상 문제로 검색 정확도가 저하된다."

---

### 2. 핵심 아이디어 — Planning과 Execution의 분리

APEX-Searcher는 검색을 두 개의 독립된 모델로 분리한다.

```
                  Query (Multi-hop)
                       │
                       ▼
        ┌──────────────────────────────┐
        │   Stage 1: Planner            │
        │   (RL로 학습)                  │
        │                                │
        │   질문을 sub-task로 분해      │
        │   sub-task 1 → sub-task 2 → ..│
        │                                │
        │   ※ Decomposition-specific    │
        │     reward로 RL                 │
        └──────────────┬───────────────┘
                       │ 분해된 plan
                       ▼
        ┌──────────────────────────────┐
        │   Stage 2: Executor           │
        │   (SFT로 학습)                 │
        │                                │
        │   각 sub-task에 대해          │
        │   - 검색 쿼리 생성             │
        │   - 결과 관찰                  │
        │   - 다음 hop 진행              │
        │                                │
        │   ※ 고품질 multi-hop           │
        │     trajectory로 SFT           │
        └──────────────┬───────────────┘
                       │
                       ▼
                  Final Answer
```

이전 방식 (단일 모델이 다 함):
```
Model: 검색 → 보고 → 또 검색 → 보고 → ... → 답
                    ↑
            중간에 길을 잃기 쉬움, 보상은 마지막에만
```

APEX-Searcher:
```
Planner: "이 질문은 sub-task A → B → C로 풀린다"
Executor: A 수행, B 수행, C 수행 (각자 명확한 mini-goal)
```

---

### 3. 학습 전략

#### 3.1 Planner — Reinforcement Learning with Decomposition Rewards

기존 RL의 문제: **희소 보상**. 다단계 multi-hop에서 정답까지 가야만 +1, 중간 단계 잘못해도 0. 학습 신호가 너무 듬성듬성.

APEX-Searcher 해법: **decomposition-specific rewards**. 분해 자체의 품질에 보상을 주어 중간 신호 밀도를 높임.
- sub-task가 명확한가?
- sub-task 간 의존성이 올바른가?
- 분해가 답 도달에 기여할 가능성이 있는가?

→ Planner는 좋은 분해를 만드는 데 특화.

#### 3.2 Executor — Supervised Fine-Tuning on Curated Trajectories

Planner가 학습되면, 그 plan을 따라 실제로 검색을 수행한 **고품질 multi-hop trajectory**들을 수집. Executor는 이 데이터로 SFT.

> "High-quality multi-hop trajectories... fine-tuned for robust iterative execution capability."

→ Executor는 sub-task를 받아서 실제 검색 쿼리를 만들고 결과를 처리하는 데 특화.

---

### 4. 왜 분리가 효과적인가

| 단일 모델 접근 | APEX-Searcher (분리) |
|---------------|----------------------|
| 계획 능력과 실행 능력이 한 모델에 섞임 | 각각 특화된 모델 |
| 학습 신호가 한 곳(최종 정답)에 몰림 | 분해 보상 + 실행 SFT로 신호 분산 |
| 실수 누적 시 회복 어려움 | 분해 단계에서 큰 그림이 잡혀 있음 |
| 한 hop 실패 시 전체 실패 | 분해된 sub-task 단위로 디버깅 가능 |

---

### 5. 실험 결과 (Abstract 기준)

논문은 *"다양한 벤치마크에서 multi-hop RAG와 task planning 양쪽에서 상당한 개선"*을 보고. 구체적 수치는 본문에 있으며 abstract엔 정량 비교 없음. 다만 강조점:

- **Multi-hop RAG benchmarks**: 단일 단계 RAG와 기존 multi-round 반복 검색 baseline 모두 능가
- **Task planning quality**: 분해 자체의 품질도 베이스라인 대비 향상

---

### 6. 일반화된 패턴 — Two-Stage Agentic Retrieval

APEX-Searcher의 진짜 기여는 모델 자체보다 **"검색은 planning과 execution을 분리해야 한다"**는 설계 원리.

```
┌─────────────────────────────────────────────────────────┐
│         Two-Stage Agentic Retrieval (일반 형태)         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Stage 1 — Strategic Planning                            │
│    · 질문 구조 파악                                       │
│    · 검색 sub-task 분해                                  │
│    · 의존성·순서 결정                                     │
│    · 학습 방식: RL with decomposition rewards            │
│                                                          │
│  Stage 2 — Tactical Execution                            │
│    · 각 sub-task에 대한 쿼리 작성                         │
│    · 도구 호출 (search, grep, code_exec, ...)           │
│    · 결과 통합, 다음 hop 트리거                          │
│    · 학습 방식: SFT on high-quality trajectories         │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

이 패턴은 APEX-Searcher 한 논문의 발견이 아니라, 광범위한 흐름:
- **Anthropic Claude Code**: planning(TodoWrite) + execution(grep/read) 분리
- **Multi-agent research systems**: orchestrator + worker 분리
- **MCP code execution**: agent가 코드로 plan을 만들고 실행

---

### 7. 한계 및 후속 방향

- **계산 비용**: 두 단계 학습 + 추론 시 두 모델 호출
- **분해 품질의 천장**: Planner가 잘못 분해하면 Executor도 못 살림
- **도메인 일반화**: 새 도메인 적용 시 양쪽 모두 재학습 필요
- **단순 질문의 오버헤드**: 1-hop 질문엔 과한 구조

---

## 내가 얻은 인사이트

### 검색 시스템 설계 관점

1. **"검색"과 "검색 전략"은 다른 능력이다**
   - 한 모델이 *"어떻게 풀까"* 고민하면서 동시에 *"무엇을 grep할까"*까지 하면 둘 다 어중간해진다. 인간 개발자도 무의식적으로 분리한다 — 머릿속에서 "먼저 X 알아내고, 그 결과로 Y 찾고" 계획을 세운 다음에 키보드를 친다. APEX-Searcher는 이 인지 분업을 명시화.

2. **희소 보상 문제는 분해 보상으로 푼다는 일반 원리**
   - RL이 multi-step task에서 잘 안 되는 이유는 거의 항상 보상이 너무 멀리 있어서다. 분해 단계 자체에 보상을 주는 발상은 검색뿐 아니라 코드 생성, 계획, 도구 사용 모든 영역에 적용 가능.

3. **Two-stage는 단순 RAG → 대규모 검색의 일반화 경로**
   - 1-hop 작은 코퍼스: 키워드/임베딩 한 방
   - Multi-hop 작은 코퍼스: 에이전트 단일 모델 ReAct
   - Multi-hop 대형 코퍼스: **planner + executor 분리** (← 여기가 APEX)
   - 즉, 문제가 커질수록 자연스럽게 분해 구조가 등장.

### LLM 아키텍처 관점

1. **"분해 능력"이 새로운 평가 축**
   - 지금까지 LLM 평가는 최종 정답 정확도에 집중했지만, multi-step 작업의 진짜 병목은 *분해 품질*이다. APEX-Searcher는 분해 자체를 명시적으로 학습·평가 대상으로 격상.

2. **모델 분리는 능력 분리이자 데이터 분리**
   - Planner와 Executor를 분리하면 학습 데이터도 분리된다: "좋은 분해 예시" vs "좋은 실행 trajectory". 둘은 수집 방식·평가 기준이 완전히 다르다 — 한 모델로 학습할 땐 이 차이가 뭉개진다.

3. **Sub-agent 패턴과의 자연스러운 정합**
   - Anthropic이 권장하는 multi-agent(orchestrator + workers) 구조는 사실상 APEX의 일반화다. Planner = orchestrator, Executor = worker. 학계와 산업이 같은 결론에 수렴 중.

### 실무 적용 관점

1. **multi-hop 검색이 필요한 도메인의 신호**
   - 회사 위키에서 "A 프로젝트의 기술 결정이 B 제품에 미친 영향" 같은 질문은 단일 검색으로 안 풀린다. 이런 도메인은 단순 RAG로는 한계가 명확하니 처음부터 two-stage를 가정하고 설계하는 게 낫다.

2. **Planner-Executor 분리는 작은 시스템에서도 적용 가능**
   - 두 모델을 따로 학습하는 건 비싸지만, **같은 LLM을 두 개의 다른 프롬프트/role로 호출**하는 가벼운 버전은 즉시 적용 가능. "분해" 단계 결과를 명시적 artifact로 저장하면 디버깅성도 크게 향상.

3. **분해 결과는 운영 자산**
   - 같은 종류의 질문이 반복되는 환경(고객 지원, 사내 검색 등)에선 좋은 분해 plan들을 캐시·재사용 가능. 이게 단일 모델 ReAct로는 불가능했던 운영 최적화.

### 일반화된 직관

1. **"전략과 전술의 분리"는 모든 의사결정 시스템의 원리**
   - 군사·경영·스포츠 어디든 strategy(무엇을·왜)와 tactics(어떻게·언제) 분리가 효과적. LLM agent도 같은 패턴으로 수렴.

2. **희소 보상은 "보상을 더 자주 만들어라"로 푼다**
   - RL의 오랜 격언. APEX는 이 격언을 multi-hop retrieval에 적용한 사례. 다른 영역에서도 *"최종 정답"보다 *"중간 산출물"을 평가 대상으로 끌어내리는 방향이 학습을 살린다.

3. **"한 모델이 다 한다"의 시대는 저물어간다**
   - GPT가 처음 등장했을 땐 "하나의 거대 모델이 모든 걸"이 비전이었지만, 실제로 잘 작동하는 시스템들은 모두 어떤 형태든 분리를 도입하고 있다. Sub-agent, MCP, planner-executor — 명칭만 다를 뿐 같은 흐름.
