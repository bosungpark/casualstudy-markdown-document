# Living Specs - AI 에이전트 개발을 위한 살아있는 명세 작성법

## 출처
- **아티클/논문**: How to Write Living Specs for AI Agent Development
- **저자/출처**: Molisha Shah (Augment Code)
- **링크**: https://www.augmentcode.com/guides/living-specs-for-ai-agent-development

---

## AI 요약

### 1. Living Spec이란?

Living Spec(살아있는 명세)은 AI 에이전트의 **드리프트(drift)를 방지**하기 위해, 구현 결정이 명세로 역류(flow back)하는 양방향 피드백 루프를 갖춘 명세이다. 정적 명세가 한 방향으로만 정보를 전달하는 것과 달리, Living Spec은 코드 변경이 요구사항 업데이트에 반영된다.

> "명세는 한 가지 말을 하고, 구현은 다른 것을 하고, 다음 패스에서 불일치가 더 벌어진다."

| 항목 | 내용 |
|------|------|
| 핵심 정의 | 구현 → 명세 역방향 업데이트가 내장된 양방향 명세 |
| 해결 문제 | 반복 개발 사이클에서의 AI 에이전트 드리프트 |
| 차별점 | Phase 3(양방향 업데이트) 없으면 명세는 "정교한 프롬프트"에 불과 |
| 적용 대상 | 다중 에이전트 병렬 작업, 크로스-서비스 조정 |

### 2. 양방향 업데이트의 4단계 사이클

Living Spec의 핵심은 **단방향이 아닌 양방향 피드백 루프**에 있다. Phase 3이 없으면 명세는 그저 정교한 프롬프트일 뿐이다.

```
Phase 1                Phase 2                Phase 3                Phase 4
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Initial  │     │Implementation│     │ Bidirectional│     │  Continuous  │
│  Intent   │────▶│              │────▶│   Update     │────▶│  Refinement  │
│           │     │              │     │              │     │              │
│ Dev → Spec│     │Spec → Agent  │     │ Impl → Spec  │     │ Prod → Spec  │
│           │     │     → Code   │     │              │     │              │
└──────────┘     └──────────────┘     └──────────────┘     └──────────────┘
      │                                       │                     │
      │         ◀─────────────────────────────┘                     │
      │         ◀───────────────────────────────────────────────────┘
      │                    피드백 루프 (역방향 흐름)
```

| Phase | 방향 | 활동 |
|-------|------|------|
| **Phase 1: Initial Intent** | Developer → Spec | 고수준 요구사항을 구조화된 명세로 확장 |
| **Phase 2: Implementation** | Spec → Agent → Code | 에이전트가 코드, 테스트, 문서 생성 |
| **Phase 3: Bidirectional Update** | Implementation → Spec | 실제 구축된 솔루션을 명세에 반영 (**핵심**) |
| **Phase 4: Continuous Refinement** | Production → Spec | 메트릭, 인시던트가 명세에 반영 |

### 3. Living Spec의 7가지 필수 섹션

효과적인 Living Spec은 다음 7개 섹션으로 구성된다.

```
┌─────────────────────────────────────────────────────────┐
│                   Living Spec 구조                        │
├─────────────────────────────────────────────────────────┤
│  1. Agent Role & Project Overview                        │
│     └─ 우선순위: correctness > security > performance     │
│                  > elegance                               │
│  2. Key Commands                                         │
│     └─ build, test, lint, migration 정확한 구문           │
│  3. Architecture & Critical Files                        │
│     └─ file:line 참조로 제어 포인트 지시                    │
│  4. Code Style via Examples                              │
│     └─ 에러 핸들링, 로깅 패턴의 실제 코드 스니펫            │
│  5. Three-Tier Boundaries                                │
│     └─ ✅ Always / ⚠️ Ask First / 🚫 Never              │
│  6. Implementation Status                                │
│     └─ completed / in progress / blocked 상태 추적        │
│  7. Decision Log                                         │
│     └─ 아키텍처 결정과 근거 기록                            │
└─────────────────────────────────────────────────────────┘
```

#### Three-Tier Boundaries 상세

| 티어 | 예시 |
|------|------|
| ✅ **Always** | 테스트 작성, strict TypeScript 사용, 구조화된 로그 출력 |
| ⚠️ **Ask First** | 새 의존성 추가, 스키마 변경, 인증 수정 |
| 🚫 **Never** | 크레덴셜 커밋, 프로덕션 env 파일 수정, main 브랜치 직접 push |

### 4. 명세 작성의 적정 수준: 선언적(Declarative) > 명령적(Imperative)

연구에 따르면 "작은 버그 수정에 16개의 인수 테스트 기준을 생성하는 것은 과도했다." 효과적인 명세는 에이전트를 **지향(orient)**시키되, 모든 단계를 **처방(prescribe)**하지 않는다.

```
┌─────────────────────────────────────────────────────────┐
│  ❌ 명령적 (Imperative) - 나쁜 예                         │
│  "Import numpy. Define a function called                 │
│   cosine_distance. Convert inputs..."                    │
│                                                          │
│  ✅ 선언적 (Declarative) - 좋은 예                        │
│  "Write a short and fast function to compute             │
│   cosine distance between vectors."                      │
└─────────────────────────────────────────────────────────┘
```

| 기준 | 설명 |
|------|------|
| 적정 수준 | "무엇(What)"을 명확히, "어떻게(How)"는 에이전트에게 위임 |
| 핵심 원칙 | 구조를 제공하되 반복(iteration)을 허용 |
| 경고 신호 | 단계별 구현 지시 → 에이전트가 지시를 너무 문자 그대로 따름 |

### 5. Living Spec을 방해하는 8가지 안티패턴

| # | 안티패턴 | 증상 |
|---|---------|------|
| 1 | **Under-specification** | 에이전트가 근거 없는 가정으로 빈틈을 채움 |
| 2 | **Over-specification** | 지시를 너무 문자 그대로 따라 중복 코드 생성 |
| 3 | **Mixed concerns** | 기능/기술 요구사항 간 우선순위 불명확 |
| 4 | **Missing continuity** | 이전 교정사항이 컨텍스트에 보존되지 않음 |
| 5 | **Vague success criteria** | 명확한 종료 규칙 부재 |
| 6 | **Jumping to solutions** | 실제 문제 해결 대신 기술된 답안을 구현 |
| 7 | **Environmental blindness** | 배포 컨텍스트, 시크릿 경계 무시 |
| 8 | **Token insensitivity** | 초점 없는 컨텍스트가 성능 저하 유발 |

### 6. 다중 에이전트 조정(Multi-Agent Coordination)

병렬 에이전트 작업 시, Living Spec은 **운영 조정 인프라(operational coordination infrastructure)**가 된다. 공유 스키마에 대한 레이스 컨디션을 방지하기 위해 태스크 분해 시 의존성을 고려해야 한다.

```
┌──────────────────────────────────────────────────────┐
│              전문 에이전트 역할 분류                     │
│                                                      │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐        │
│  │Investigate│  │ Implement │  │  Verify   │        │
│  │  (조사)    │  │  (구현)   │  │  (검증)   │        │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘        │
│        │              │              │               │
│  ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐       │
│  │ Critique  │  │   Debug   │  │Code Review│        │
│  │  (비평)   │  │  (디버그) │  │ (코드리뷰) │        │
│  └───────────┘  └───────────┘  └───────────┘        │
│                                                      │
│  Living Spec = 에이전트 간 조정의 Single Source of Truth │
└──────────────────────────────────────────────────────┘
```

### 7. 명세 리뷰 트리거와 버전 관리

#### 리뷰를 수행해야 하는 시점

| 트리거 | 초점 |
|--------|------|
| 에이전트 구현 사이클 완료 후 | 아키텍처 일관성 |
| 명세 → 코딩 전환 전 | 보안 크리티컬 섹션 |
| 에이전트가 모호성을 표면화할 때 | Decision Log 정확성 |
| 데이터 모델 변경 시 | 전체 구조 영향도 |

#### 버전 관리 통합

명세를 **코드처럼** 취급한다: 버전 관리, diff, 코드 리뷰. 명세가 구현 코드와 함께 리포지토리에 존재할 때, 에이전트는 세션 간 컨텍스트를 유지하며 **제도적 기억(institutional memory)**을 형성한다.

### 8. 실전 도입 권장 사항

> **크로스-서비스 조정이 필요한 실질적 태스크 하나를 선택하라.**

1. 명세를 작성한다
2. 3~5개의 측정 가능한 성공 기준을 정의한다
3. 머지 전에 Decision Log 업데이트를 필수로 요구한다
4. 이 프로세스가 드러내는 것: 명세 구조 문제인지, 리뷰 규율 문제인지, 조정 실패인지

---

## 내가 얻은 인사이트

### SDD 시리즈와의 연결 관점

1. **정적 명세 → 살아있는 명세로의 진화**
   - 이전에 정리한 SDD 가이드에서 Spec-First → Spec-Anchored → Spec-as-Source 성숙도 모델을 다뤘다면, 이 아티클은 그 모든 패턴의 **공통 전제 조건**을 다룬다: "명세가 살아있지 않으면 어떤 패턴도 지속 불가능하다."
   - Phase 3(구현 → 명세 역류)가 없는 SDD는 결국 Waterfall의 문서와 동일한 운명을 맞는다는 점이 핵심이다.

2. **"정교한 프롬프트"와 "Living Spec"의 경계선**
   - 아티클이 제시하는 가장 날카로운 구분: Phase 3이 없으면 명세는 "elaborate prompt"에 불과하다. 이는 많은 팀이 CLAUDE.md나 AGENTS.md를 "명세"라고 부르면서도 실제로는 일회성 프롬프트로 운영하는 현실을 정확히 지적한다.

### 실무 적용 관점

3. **Three-Tier Boundaries의 실용성**
   - Always / Ask First / Never 3단 경계는 단순하지만 강력하다. 특히 "Ask First" 티어의 존재가 중요한데, 이것이 에이전트에게 **판단의 여지**를 주면서도 **위험한 결정은 인간에게 위임**하는 실질적 가드레일이 된다.
   - 이 패턴은 Claude Code의 permission mode(auto/default/plan)와도 구조적으로 일치한다.

4. **8가지 안티패턴은 곧 "명세 코드 스멜"**
   - Under-specification과 Over-specification이 동시에 안티패턴인 점이 흥미롭다. 코드에 "God Object"와 "Anemic Model"이 양극의 스멜인 것처럼, 명세에도 적정 수준이 있다.
   - 특히 **Token insensitivity**(초점 없는 컨텍스트)를 안티패턴으로 명시한 것은, LLM의 컨텍스트 윈도우가 유한한 자원이라는 점을 명세 설계에 반영한 것으로 실무적으로 매우 중요하다.

### 설계 원칙 관점

5. **Living Spec = 분산 시스템의 공유 상태**
   - 다중 에이전트가 하나의 명세를 공유하는 구조는 본질적으로 분산 시스템의 공유 상태 관리 문제와 동일하다. 레이스 컨디션, 일관성, 버전 충돌 등 동일한 문제가 발생하며, 명세의 버전 관리와 리뷰 트리거는 곧 분산 시스템의 일관성 프로토콜에 해당한다.
   - 이 관점에서 Living Spec은 "에이전트 간 합의 프로토콜"이라고 볼 수 있다.
