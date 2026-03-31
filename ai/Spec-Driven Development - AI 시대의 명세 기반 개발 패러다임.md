# Spec-Driven Development - AI 시대의 명세 기반 개발 패러다임

## 출처
- **아티클/논문**: Spec-driven development: Unpacking one of 2025's key new AI-assisted engineering practices
- **저자/출처**: Liu Shangqi (Technology Director, APAC Region, Thoughtworks)
- **링크**: https://thoughtworks.medium.com/spec-driven-development-d85995a81387

---

## AI 요약

### 1. Spec-Driven Development(SDD)란?

AI 코딩 에이전트를 활용하여 **잘 작성된 소프트웨어 요구사항 명세(Specification)**를 프롬프트로 사용해 실행 가능한 코드를 생성하는 개발 패러다임이다.

> "A development paradigm that uses well-crafted software requirement specifications as prompts, aided by AI coding agents, to generate executable code."

| 항목 | 내용 |
|------|------|
| 핵심 정의 | 명세를 AI 에이전트의 프롬프트로 사용하여 코드를 생성하는 개발 방식 |
| 등장 배경 | LLM의 확장된 컨텍스트 윈도우 + BDD/분산 컴퓨팅 명세의 발전 |
| 위치 | Vibe Coding과 전통적 Waterfall 사이의 균형점 |
| 시점 | 2025년 말 기준 신흥 실천법(Emerging Practice) |
| 관련 도구 | Amazon Kiro, GitHub Spec-Kit, Cursor, Claude Code, Context7 |

### 2. 두 가지 해석의 충돌

SDD에 대해 업계 내에서 두 가지 상반된 관점이 존재한다.

```
┌────────────────────────────────────────────────────────────────────┐
│              SDD의 두 가지 해석                                      │
│                                                                    │
│   급진적 관점 (Radical)              전통적 관점 (Traditional)       │
│   ┌──────────────────────┐          ┌──────────────────────┐       │
│   │ Spec = 유일한 진실의  │          │ Spec = 코드 생성을    │       │
│   │        원천 (SoT)     │          │        구동하는 입력   │       │
│   │                      │          │                      │       │
│   │ Code = 중간 부산물    │          │ Code = 유지해야 할    │       │
│   │        (Byproduct)    │          │        진실의 원천     │       │
│   └──────────────────────┘          └──────────────────────┘       │
│                                                                    │
│   대표 도구: Tessl Framework         대표 도구: Kiro, Spec-Kit      │
│   "코드를 버리고 명세만 유지"         "명세가 TDD처럼 코드를 구동"    │
└────────────────────────────────────────────────────────────────────┘
```

### 3. 명세(Spec)의 구성 요소

SDD에서의 명세는 일반적인 PRD(Product Requirements Document)와 다르다. 구체적이고 형식화된 구조를 요구한다.

| 구성 요소 | 설명 |
|-----------|------|
| Input/Output 매핑 | 입력에 대한 기대 출력을 명시적으로 정의 |
| 사전/사후 조건 | Preconditions & Postconditions |
| 불변 조건과 제약 | Invariants & Constraints |
| 인터페이스 타입 | 통합 계약(Integration Contracts) |
| 순차 로직 | 상태 머신(State Machines) |

### 4. 좋은 명세의 특성

```
┌────────────────────────────────────────────────────────────────────┐
│              효과적인 SDD 명세의 5가지 원칙                          │
│                                                                    │
│   ① 도메인 지향 유비쿼터스 언어                                     │
│      구현 세부사항이 아닌 도메인 언어로 작성                          │
│                                                                    │
│   ② Given/When/Then 구조 (BDD 차용)                                │
│      시나리오 기반의 구조화된 요구사항 기술                           │
│                                                                    │
│   ③ 완전성과 간결성의 균형                                          │
│      "Critical path를 커버하되, 모든 케이스를 열거하지 않는다"        │
│                                                                    │
│   ④ 명확성과 결정론                                                 │
│      모호함을 줄여 모델 환각(Hallucination)을 최소화                  │
│                                                                    │
│   ⑤ 반구조화된 형식(Semi-structured)                                │
│      기계 가독성을 유지하면서 LLM 추론에 최적화                       │
└────────────────────────────────────────────────────────────────────┘
```

### 5. SDD 실무 워크플로우

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Planning │────▶│ Spec 작성     │────▶│ Human Review │────▶│ 코드 생성     │
│ Phase    │     │ (Markdown)   │     │ (반복 검증)   │     │ (AI Agent)   │
└──────────┘     └──────────────┘     └──────────────┘     └──────────────┘
     │                  │                    │                     │
     ▼                  ▼                    ▼                     ▼
 AI가 요구사항      명세를 .md 파일로    사람이 명세를         AGENTS.md 등
 분석 & 설계 계획   공식화               반복적으로 검토       기술 제약과 함께
 생성                                   & 수정               에이전트에 전달
```

**도구별 접근 방식:**
- **Amazon Kiro**: 요구사항 → 설계 → 태스크 생성의 3단계 워크플로우
- **GitHub Spec-Kit**: Kiro와 유사하나 더 풍부한 오케스트레이션 + "Constitution"(불변 원칙) 정의
- **Tessl Framework**: 더 급진적 — 명세 자체가 유지 관리되는 아티팩트

### 6. Context Engineering과의 관계

SDD는 Context Engineering의 원리를 활용한다.

| 구분 | Prompt Engineering | Context Engineering |
|------|-------------------|-------------------|
| 최적화 대상 | 사람 ↔ LLM 상호작용 | 에이전트 ↔ LLM 상호작용 |
| 핵심 역할 | 단일 프롬프트 최적화 | 정보 큐레이션 시스템 설계 |

SDD에서 Context Engineering이 작동하는 방식:
- BDD의 Given/When/Then → Few-shot 프롬프트 기법
- 명세로 압축된 컨텍스트 정보
- MCP 서버(Context7 등)를 통한 실시간 문서 제공
- 레거시 코드베이스에서 추출한 지식 그래프

### 7. Waterfall과의 차이

SDD가 Waterfall의 부활이 아닌 이유:

```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│  Waterfall          SDD              Vibe Coding                  │
│  ┌─────────┐       ┌─────────┐       ┌─────────┐                 │
│  │ 매우 긴  │       │ 짧고    │       │ 피드백   │                 │
│  │ 피드백   │       │ 효과적인│       │ 루프    │                 │
│  │ 루프     │       │ 피드백  │       │ 없음    │                 │
│  │         │       │ 루프    │       │ (즉흥적) │                 │
│  └─────────┘       └─────────┘       └─────────┘                 │
│                                                                    │
│  문제: Shadow       해결: 거버넌스    문제: "too fast,             │
│  Architecture 발생   + 민첩성 유지    spontaneous and haphazard"   │
│  + 긴 사이클                         → 유지보수 불가능한 코드      │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

> "It's not creating huge feedback loops like waterfall—it's providing a mechanism for shorter and effective ones than would otherwise be possible with pure vibe coding."

### 8. 도전과제와 리스크

| 도전과제 | 설명 |
|---------|------|
| 합의 부재 | 최적의 SDD 워크플로우에 대한 업계 합의 없음. 명세 품질 평가 방법(Eval)도 부재 |
| 비결정론적 생성 | 동일 명세에서도 생성 코드가 매번 달라짐. 명세 업그레이드/유지보수 어려움 |
| Spec Drift & 환각 | 명세와 실제 구현 간의 괴리, LLM 환각이 본질적으로 회피 어려움 |
| CI/CD의 중요성 | 비결정론적 생성에 대응하기 위해 "고도로 결정론적인 CI/CD"가 필수적 |
| 아티팩트 모호성 | 명세와 코드 중 어느 것이 궁극적 개발 산출물인지 미해결 |

---

## 내가 얻은 인사이트

### 소프트웨어 공학 관점

1. **BDD에서 SDD로의 자연스러운 진화**
   - Given/When/Then 구조를 이미 사용하는 팀이라면 SDD 도입의 진입 장벽이 낮다. BDD 명세가 곧 AI 에이전트의 프롬프트가 되는 구조이므로, 기존 BDD 자산을 SDD로 전환하는 경로가 현실적이다.

2. **"명세가 진실의 원천" vs "코드가 진실의 원천" 논쟁의 핵심**
   - 이 논쟁은 단순한 철학적 차이가 아니라 실무적 결과를 좌우한다. Spec이 SoT라면 코드를 언제든 재생성할 수 있어야 하므로, 비결정론적 생성 문제를 해결해야 한다. Code가 SoT라면 Spec Drift를 지속적으로 관리하는 프로세스가 필요하다.

3. **Vibe Coding의 구조적 한계를 명시적으로 인정**
   - Vibe Coding이 "빠르지만 즉흥적이고 산만하다"는 평가는 현장에서 체감되는 문제를 정확히 짚는다. 특히 팀 규모가 커지거나 프로젝트 수명이 길어질수록 SDD의 거버넌스가 의미 있어진다.

### 실무 적용 관점

1. **CI/CD가 SDD의 안전망이다**
   - 비결정론적 코드 생성은 피할 수 없으므로, 결국 테스트 자동화와 CI/CD 파이프라인의 품질이 SDD 성패를 결정한다. AI가 코드를 생성하더라도 검증 체계는 결정론적이어야 한다는 점은 전통적 엔지니어링 원칙이 여전히 유효함을 보여준다.

2. **AGENTS.md와 같은 기술 제약 파일의 중요성**
   - 명세만으로는 부족하고, AI 에이전트가 참조할 아키텍처 제약, 코딩 컨벤션, 기술 스택 정보를 별도로 관리하는 패턴이 실무적으로 핵심이다. 이것이 Context Engineering의 실체다.

3. **2026년은 SDD 도구의 성숙도가 결정되는 해**
   - Kiro, Spec-Kit, Tessl 등 도구가 경쟁하면서 워크플로우 표준이 형성될 가능성이 높다. 어떤 도구/접근법이 살아남는지 지켜보되, 명세 작성 역량 자체를 키우는 것이 도구 독립적으로 유효한 투자다.
