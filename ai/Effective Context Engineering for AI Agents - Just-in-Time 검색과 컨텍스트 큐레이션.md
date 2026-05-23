# Effective Context Engineering for AI Agents - Just-in-Time 검색과 컨텍스트 큐레이션

## 출처
- **아티클**: Effective context engineering for AI agents
- **저자/출처**: Anthropic Engineering
- **링크**: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

---

## AI 요약

### 1. Context Engineering이란?

> "Finding the smallest possible set of high-signal tokens that maximize the likelihood of your desired outcome."
> — Anthropic

Anthropic은 context engineering을 **prompt engineering의 자연스러운 진화**로 정의한다. 한 번의 프롬프트로 끝나는 분류·생성 작업에서, 다중 턴·장시간 동작 에이전트로 패러다임이 옮겨가면서 "**무엇을 어떻게 말할까**"보다 "**어떤 정보를 어떤 순간에 컨텍스트에 둘까**"가 핵심이 되었다.

| 구분 | Prompt Engineering | Context Engineering |
|------|-------------------|---------------------|
| **단위** | 정적 문자열 | 동적 상태 큐레이션 |
| **빈도** | 일회성 작성 | 매 추론 루프마다 정제 |
| **대상** | User/System 메시지 | + 도구, MCP, 메모리, 외부 데이터, 메시지 히스토리 전체 |
| **목표** | 좋은 지시문 | 신호 대 잡음비(SNR) 극대화 |

---

### 2. Context Rot — 왜 "다 넣기"가 답이 아닌가

> "As context length grows, a model's ability to accurately recall information from that context decreases."

핵심은 **attention budget이 유한**하다는 것. Transformer는 n개 토큰에 대해 n² 쌍별 관계를 계산하는데, 컨텍스트가 길어질수록 각 관계에 배분되는 주의가 희석된다.

```
Context Length: short ─────────────────────── long
                 ▲                              ▼
        Attention/token: high             attention/token: low
              ▲                                 ▼
        Recall accuracy: ★★★★★          Recall accuracy: ★★☆☆☆
```

학습 데이터 자체가 짧은 시퀀스 위주여서, 모델은 장범위 의존성에 본질적으로 덜 최적화돼 있다. 결론: **컨텍스트 윈도우는 귀중하고 유한한 자원**이다.

---

### 3. 컨텍스트 구성요소별 가이드

#### 3.1 시스템 프롬프트 — Goldilocks Zone

두 가지 실패 모드 사이의 균형점을 찾아야 한다.

| 안티패턴 | 문제 |
|---------|------|
| 과도한 구체성 (하드코딩된 if-else) | 부서지기 쉬움, 유지보수 폭증 |
| 과도한 일반성 (모호한 고수준 지침) | 구체적 신호 부족, 잘못된 공유 컨텍스트 가정 |

**권장 구조**:
```xml
<background_information> ... </background_information>
<instructions> ... </instructions>
## Tool guidance
## Output description
```

작업 흐름: 최고 모델 + 최소 프롬프트로 시작 → 실패 모드 관찰 → 명확한 지시문/예제를 점진적으로 추가.

#### 3.2 도구(Tools) 설계

> "도구는 에이전트와 정보/행동 공간 사이의 **계약**이다."

| 좋은 도구의 특성 | 안티패턴 |
|----------------|---------|
| 자체 포함적 | 책임 범위 모호 |
| 명확한 의도 | 도구 간 기능 중복 |
| 토큰 효율적 반환 | 원시 덤프 |
| 에러에 강건 | 실패 시 침묵 |

> "An AI agent cannot be expected to do better than a human engineer being confronted with the same ambiguity."

#### 3.3 Few-shot 예제

> "Examples are worth a thousand words to an LLM."

안티패턴: 모든 엣지 케이스를 나열. 권장: **다양하고 정규적(canonical)인** 예제의 큐레이션 세트.

---

### 4. Just-in-Time Retrieval — RAG에 대한 Anthropic의 입장

#### 4.1 전통적 사전 검색 vs Just-in-Time

```
[전통 RAG]                          [Just-in-Time]
                                    
모든 데이터 → 임베딩 → top-k         경량 식별자(파일경로, URL, 쿼리 ID)
   ↓                                   ↓ (런타임에 필요할 때)
한 번의 호출로 컨텍스트에 주입        도구로 동적 로드
   ↓                                   ↓
정적 인덱스 (재인덱싱 비용)           탐색 → 발견 → 정제 (점진적 공개)
```

핵심 인용:
> "Rather than pre-processing all relevant data up front, agents built with the 'just in time' approach maintain lightweight identifiers (file paths, stored queries, web links, etc.) and use these references to dynamically load data into context at runtime using tools."

#### 4.2 메타데이터가 신호다

| 단서 | 함의 |
|------|------|
| `test_utils.py` vs `src/core_logic/utils.py` | 목적의 차이 (테스트 보조 vs 핵심 로직) |
| 폴더 계층 | 모듈 경계 |
| 명명 규칙 | 사용 시점/주체 힌트 |
| 타임스탬프 | 관련성의 대리 지표 |

→ **인간이 파일시스템·메일함·북마크로 외부 메모리를 운영하듯**, 에이전트도 경량 참조를 들고 다니다 필요할 때만 끌어온다.

#### 4.3 Claude Code 예시

- `glob`, `grep` 같은 프리미티브로 환경 탐색
- `head`, `tail` 같은 Bash 명령어로 거대 데이터를 컨텍스트에 전부 로드하지 않고 분석
- `CLAUDE.md`만 사전 컨텍스트에 두고, 나머지는 just-in-time

> "Stale indexes and complex syntax trees become a problem of the past."

#### 4.4 하이브리드가 정답

최고의 에이전트는 두 전략을 결합한다:
- **사전 검색**: 속도가 중요한 핵심 컨텍스트(`CLAUDE.md` 같은)
- **Just-in-time**: 광활한 미지의 영역 자율 탐색

> "Do whatever is simplest and works." — 여전히 최고의 조언.

---

### 5. Long-Horizon 작업 — 컨텍스트가 윈도우보다 클 때

대규모 마이그레이션, 다단계 리서치처럼 토큰이 윈도우를 넘기는 작업에 필요한 세 가지 기법.

```
┌───────────────────────────────────────────────────────┐
│                Long-Horizon Strategies                 │
├───────────────────────────┬───────────────────────────┤
│  A. Compaction            │  광범위한 왕복 대화        │
│  B. Structured Note-Taking│  명확한 마일스톤 반복 작업 │
│  C. Sub-agent             │  병렬 탐색 가능한 리서치   │
└───────────────────────────┴───────────────────────────┘
```

#### 5.1 Compaction — 대화 압축

윈도우 한계 근처에서 메시지 히스토리를 요약하고 그 요약으로 새 윈도우를 시작.

**Claude Code의 구현**:
- 보존: 아키텍처 결정, 미해결 버그, 구현 세부
- 폐기: 중복 도구 출력, 오래된 메시지
- 압축 후: 요약 + 최근 접근 5개 파일로 계속

**튜닝 원칙**: 회상(recall)을 먼저 최대화 → 그 다음 정확도(precision) 개선.

**가벼운 변형**: 오래된 메시지의 도구 호출/결과만 정리(tool-result cleanup). Claude Developer Platform에 최근 출시됨.

#### 5.2 Structured Note-Taking — 외부 메모리

> "에이전트가 컨텍스트 윈도우 외부 메모리에 정기적으로 노트를 작성하고, 나중에 다시 끌어들인다."

**Claude playing Pokémon 사례**:
- "지난 1,234스텝 동안 Route 1에서 Pikachu 8/10 레벨 달성"
- 탐색한 지역 맵
- 어떤 공격이 어떤 상대에게 효과적인지
- 프롬프트 없이 메모리 구조 자동 개발 → 컨텍스트 리셋 후 자기 노트를 읽고 다중시간 진행 재개

**Sonnet 4.5 + Memory Tool (퍼블릭 베타)**:
- 파일 기반 외부 저장
- 프로젝트 상태를 세션 간 유지

#### 5.3 Sub-agent Architecture — 관심사 분리

- 메인 에이전트: 고수준 계획·조율
- 서브에이전트: 깊이 있는 기술 작업, 자체 깨끗한 컨텍스트
  - 내부적으로 수만 토큰 사용
  - **요약(1k-2k 토큰)만 메인에 반환**

> "Clear separation of concerns — detailed search contexts remain isolated within subagents."

→ Anthropic의 multi-agent research system 포스트가 이 패턴의 실증.

---

### 6. 종합 권장사항

| 상황 | 권장 |
|------|------|
| 단순한 1회성 작업 | 잘 짜인 프롬프트 |
| 짧은 멀티턴 | 시스템 프롬프트 + just-in-time |
| 광역 리서치 | Sub-agent + 노트 |
| 끝나지 않는 작업 | Compaction + Memory Tool |

**최종 인용**:
> "Context engineering represents a fundamental shift in how we build with LLMs... As models become more capable, the challenge isn't just crafting the perfect prompt — it's thoughtfully curating what information enters the model's limited attention budget at each step."

---

## 내가 얻은 인사이트
