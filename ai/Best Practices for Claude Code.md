# Best Practices for Claude Code

## 출처
- **아티클**: Best Practices for Claude Code
- **저자/출처**: Anthropic (Claude Code 공식 문서)
- **링크**: https://code.claude.com/docs/en/best-practices

---

## AI 요약

### 1. 핵심 원칙: 컨텍스트 윈도우 관리

Claude Code의 모든 베스트 프랙티스는 하나의 제약에서 출발한다: **컨텍스트 윈도우가 빠르게 채워지고, 채워질수록 성능이 저하된다.**

컨텍스트 윈도우에는 대화 전체, Claude가 읽은 파일, 명령어 출력이 모두 포함된다. 디버깅 세션 하나가 수만 토큰을 소비할 수 있다.

```
┌─────────────────────────────────────────┐
│          Context Window                 │
│                                         │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐  │
│  │ 대화    │ │ 파일     │ │ 명령어  │  │
│  │ 히스토리│ │ 내용     │ │ 출력    │  │
│  └─────────┘ └──────────┘ └─────────┘  │
│                                         │
│  ← 채워질수록 성능 저하 →               │
└─────────────────────────────────────────┘
```

### 2. Claude에게 스스로 검증할 수단을 제공하라

**가장 높은 레버리지를 가진 실천법.** 테스트, 스크린샷, 기대 출력을 제공하면 Claude가 스스로 작업을 검증한다.

| 전략 | Before | After |
|------|--------|-------|
| **검증 기준 제공** | "이메일 검증 함수 만들어줘" | "validateEmail 함수 작성. user@example.com → true, invalid → false. 테스트 실행까지" |
| **UI 변경 시각적 검증** | "대시보드 예쁘게 만들어" | "[스크린샷 첨부] 이 디자인 구현하고, 결과 스크린샷 찍어서 비교해" |
| **근본 원인 해결** | "빌드 실패함" | "이 에러로 빌드 실패: [에러 붙여넣기]. 근본 원인 해결하고 빌드 성공 확인해" |

### 3. 탐색 → 계획 → 코딩 워크플로우

Plan Mode를 활용해 탐색과 실행을 분리한다.

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 1. 탐색  │───▶│ 2. 계획  │───▶│ 3. 구현  │───▶│ 4. 커밋  │
│ Plan Mode│    │ Plan Mode│    │Normal Mode│    │Normal Mode│
│ 파일 읽기│    │ 계획 작성│    │ 코딩+테스트│   │ PR 생성  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

- **탐색**: Plan Mode에서 파일을 읽고 현재 구조를 이해
- **계획**: 구현 계획 수립 (Ctrl+G로 에디터에서 직접 편집 가능)
- **구현**: Normal Mode로 전환하여 코딩, 테스트 검증
- **커밋**: 설명적 메시지로 커밋 및 PR 생성

> 범위가 명확하고 수정이 작은 작업(오타 수정, 로그 추가 등)은 계획을 건너뛰어도 된다.

### 4. 구체적인 컨텍스트를 프롬프트에 제공하라

| 전략 | Before | After |
|------|--------|-------|
| **범위 지정** | "foo.py 테스트 추가해" | "foo.py에서 사용자 로그아웃 엣지 케이스 테스트 작성. mock 사용 금지" |
| **소스 지정** | "ExecutionFactory API가 왜 이상해?" | "ExecutionFactory의 git history를 보고 API가 어떻게 발전했는지 요약해" |
| **기존 패턴 참조** | "캘린더 위젯 추가해" | "홈페이지 위젯 구현 패턴 확인. HotDogWidget.php 참고. 같은 패턴으로 캘린더 위젯 구현" |
| **증상 기술** | "로그인 버그 고쳐" | "세션 타임아웃 후 로그인 실패. src/auth/ 인증 흐름, 특히 토큰 리프레시 확인. 재현 테스트 작성 후 수정" |

**리치 콘텐츠 제공 방법:**
- `@` 로 파일 참조
- 이미지 복사/붙여넣기 또는 드래그 앤 드롭
- URL 제공 (문서, API 레퍼런스)
- `cat error.log | claude` 로 데이터 파이프

### 5. 환경 설정 (Environment Configuration)

#### CLAUDE.md 작성

`/init` 명령으로 프로젝트 기반 CLAUDE.md 생성 후 점진적으로 개선한다.

```markdown
# Code style
- Use ES modules (import/export) syntax, not CommonJS (require)
- Destructure imports when possible

# Workflow
- Be sure to typecheck when you're done making a series of code changes
- Prefer running single tests, and not the whole test suite
```

| 포함해야 할 것 | 제외해야 할 것 |
|---------------|---------------|
| Claude가 추측 불가능한 Bash 명령어 | 코드를 읽으면 알 수 있는 것 |
| 기본값과 다른 코드 스타일 규칙 | Claude가 이미 아는 표준 규약 |
| 테스트 방법과 선호하는 테스트 러너 | 상세 API 문서 (링크로 대체) |
| 브랜치 네이밍, PR 규약 | 자주 변경되는 정보 |
| 프로젝트 특수 아키텍처 결정 | 긴 설명이나 튜토리얼 |

> CLAUDE.md가 너무 길면 Claude가 중요한 규칙을 무시한다. 코드처럼 정기적으로 리뷰하고 가지치기하라.

#### 권한 설정

- **Auto Mode**: 분류기 모델이 명령을 검토, 위험한 것만 차단
- **Permission Allowlist**: 안전한 특정 도구 허용 (`npm run lint`, `git commit`)
- **Sandboxing**: OS 수준 격리로 파일시스템/네트워크 접근 제한

#### CLI 도구 활용

`gh`, `aws`, `gcloud`, `sentry-cli` 등 CLI 도구는 외부 서비스와 **가장 컨텍스트 효율적인** 상호작용 방법이다.

#### MCP 서버 연결

`claude mcp add`로 Notion, Figma, 데이터베이스 등 외부 도구를 연결한다.

#### Hooks 설정

CLAUDE.md는 권고사항이지만, **Hooks는 결정적(deterministic)**이다. 매번 예외 없이 실행되어야 하는 작업에 사용한다.

#### Skills 생성

`.claude/skills/` 에 `SKILL.md` 파일을 만들어 도메인 지식과 재사용 가능한 워크플로우를 제공한다.

```markdown
# .claude/skills/fix-issue/SKILL.md
---
name: fix-issue
description: Fix a GitHub issue
disable-model-invocation: true
---
Analyze and fix the GitHub issue: $ARGUMENTS.
1. Use `gh issue view` to get the issue details
2. Search the codebase for relevant files
3. Implement the fix
4. Write and run tests
5. Create a PR
```

#### 커스텀 서브에이전트 정의

`.claude/agents/` 에 전문화된 어시스턴트를 정의한다. 자체 컨텍스트와 허용 도구 세트로 격리 실행된다.

#### 플러그인 설치

`/plugin`으로 마켓플레이스를 탐색한다. Skills, Hooks, 서브에이전트, MCP 서버를 하나로 번들링한 단위이다.

### 6. 효과적인 커뮤니케이션

#### 코드베이스 질문하기

시니어 엔지니어에게 묻듯이 질문한다:
- "로깅이 어떻게 동작해?"
- "새 API 엔드포인트는 어떻게 만들어?"
- "foo.rs 134번째 줄의 `async move { ... }`가 뭐야?"
- "CustomerOnboardingFlowImpl이 어떤 엣지 케이스를 처리해?"

#### 인터뷰 방식 활용

큰 기능 구현 전, Claude에게 인터뷰를 요청한다:

```
I want to build [brief description]. Interview me in detail using
the AskUserQuestion tool. Ask about technical implementation, UI/UX,
edge cases, concerns, and tradeoffs.
```

스펙이 완성되면 **새 세션**에서 구현을 시작한다 (깨끗한 컨텍스트).

### 7. 세션 관리

```
┌─────────────────────────────────────────────────────┐
│                세션 관리 도구                         │
├──────────────┬──────────────────────────────────────┤
│ Esc          │ 진행 중 작업 중단 (컨텍스트 보존)      │
│ Esc + Esc    │ 리와인드 메뉴 열기                     │
│ /rewind      │ 이전 체크포인트로 복원                  │
│ /clear       │ 관련 없는 작업 간 컨텍스트 초기화       │
│ /compact     │ 컨텍스트 수동 압축                     │
│ /btw         │ 컨텍스트에 남지 않는 사이드 질문        │
│ --continue   │ 가장 최근 대화 재개                    │
│ --resume     │ 최근 세션 목록에서 선택                 │
│ /rename      │ 세션에 설명적 이름 부여                 │
└──────────────┴──────────────────────────────────────┘
```

핵심 원칙:
- **같은 실수를 2번 이상 수정했다면**: `/clear` 후 더 나은 초기 프롬프트로 재시작
- **서브에이전트로 조사 위임**: 별도 컨텍스트에서 실행되어 메인 대화를 깨끗하게 유지
- **체크포인트 활용**: 위험한 시도를 자유롭게 하고, 실패 시 리와인드

### 8. 자동화 및 스케일링

#### 비대화형 모드 (`claude -p`)

```bash
# 일회성 쿼리
claude -p "Explain what this project does"

# 스크립트용 구조화 출력
claude -p "List all API endpoints" --output-format json

# 실시간 처리용 스트리밍
claude -p "Analyze this log file" --output-format stream-json
```

#### 병렬 세션 운영

- **Desktop 앱**: 다중 로컬 세션 시각적 관리 (격리된 worktree)
- **Web**: Anthropic 클라우드 인프라에서 격리된 VM 실행
- **Agent Teams**: 공유 작업, 메시징, 팀 리드를 통한 자동 조율

#### Writer/Reviewer 패턴

```
Session A (Writer)          Session B (Reviewer)
──────────────────          ────────────────────
"Rate limiter 구현해줘"
                            "rateLimiter.ts 리뷰해줘.
                             엣지 케이스, 레이스 컨디션,
                             기존 미들웨어 패턴 일관성 확인"

"리뷰 피드백: [Session B 결과].
 이 이슈들 해결해줘"
```

#### Fan-out 패턴 (대규모 마이그레이션)

```bash
for file in $(cat files.txt); do
  claude -p "Migrate $file from React to Vue. Return OK or FAIL." \
    --allowedTools "Edit,Bash(git commit *)"
done
```

### 9. 흔한 실패 패턴

| 안티패턴 | 증상 | 해결책 |
|---------|------|--------|
| **Kitchen Sink 세션** | 하나의 세션에서 관련 없는 작업을 계속 수행 | `/clear`로 작업 간 컨텍스트 초기화 |
| **반복 수정** | 같은 실수를 계속 수정, 실패한 접근이 컨텍스트를 오염 | 2번 실패 후 `/clear`, 더 나은 초기 프롬프트로 재시작 |
| **과잉 CLAUDE.md** | 너무 긴 CLAUDE.md로 중요한 규칙이 묻힘 | 가차 없이 가지치기. Hook으로 전환 고려 |
| **검증 부재** | 그럴듯해 보이지만 엣지 케이스 미처리 | 항상 검증 수단 제공 (테스트, 스크립트, 스크린샷) |
| **무한 탐색** | 범위 없이 "조사해줘"로 수백 파일 읽기 | 범위를 좁히거나 서브에이전트 사용 |

---

## 내가 얻은 인사이트

### 시스템 설계 관점

1. **컨텍스트 윈도우 = 가장 소중한 리소스**
   - LLM 에이전트 시스템에서 컨텍스트 윈도우는 메모리와 같다. 메모리 관리 원칙(필요한 것만 로드, 불필요한 것 해제, 격리)이 그대로 적용된다.
   - 서브에이전트는 프로세스 격리와 유사한 패턴이다: 별도 컨텍스트에서 실행하고 결과만 반환받아 메인 컨텍스트를 보호한다.

2. **결정적(Deterministic) vs 권고적(Advisory) 제어의 구분**
   - CLAUDE.md는 권고사항(Advisory)이고, Hooks는 결정적(Deterministic)이다. 이 구분은 소프트웨어 시스템의 설정(config) vs 정책(policy) 구분과 동일하다. 절대 빠져서는 안 되는 것은 Hooks로, 유연하게 적용할 것은 CLAUDE.md로 분리해야 한다.

3. **Writer/Reviewer 분리 패턴의 보편성**
   - 코드 작성자와 리뷰어를 별도 세션으로 분리하는 패턴은, 인간 조직의 코드 리뷰 프로세스를 LLM 에이전트 시스템으로 옮긴 것이다. 자기가 쓴 코드에 대한 편향(bias)을 제거하려면 깨끗한 컨텍스트가 필수다.

### 실무 적용 관점

1. **"2번 실패 후 리셋" 규칙**
   - 같은 실수를 2번 수정했다면 컨텍스트가 오염된 것이다. `/clear` 후 학습한 내용을 반영한 더 나은 프롬프트로 재시작하는 것이 실무에서 매우 효과적이다. 이는 디버깅에서 "삽질의 늪"에 빠지는 것을 구조적으로 방지한다.

2. **Fan-out 패턴으로 대규모 마이그레이션 자동화**
   - `claude -p` + `--allowedTools`로 수천 개 파일의 마이그레이션을 병렬 자동화할 수 있다. 먼저 2-3개 파일로 프롬프트를 검증한 후 전체 실행하는 "테스트 후 스케일" 접근이 핵심이다.

3. **검증 가능성(Verifiability)이 최고의 레버리지**
   - Claude에게 테스트, 스크린샷, 기대 출력을 제공하는 것이 가장 높은 ROI를 가진다. 이는 단순히 "프롬프트 엔지니어링"이 아니라, 에이전트에게 피드백 루프를 만들어주는 시스템 설계다.
