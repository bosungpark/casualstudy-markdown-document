# NeMo Guardrails: Colang 기반 프로그래머블 가드레일 툴킷

## Source
- **논문**: [NeMo Guardrails: A Toolkit for Controllable and Safe LLM Applications with Programmable Rails](https://arxiv.org/abs/2310.10501)
- **저자**: Traian Rebedea, Razvan Dinu, Makesh Sreedhar, Christopher Parisien, Jonathan Cohen
- **출판**: EMNLP 2023 Demo Track
- **GitHub**: [NVIDIA-NeMo/Guardrails](https://github.com/NVIDIA-NeMo/Guardrails) (5.3k stars)
- **공식 문서**: [docs.nvidia.com/nemo/guardrails](https://docs.nvidia.com/nemo/guardrails)

## AI Summary

### 1. 핵심 개념: Programmable Rails

NeMo Guardrails는 **대화 흐름을 프로그래밍 가능하게 제어**하는 오픈소스 툴킷으로, LLM의 학습 단계 정렬(model alignment)이 아닌 **런타임 대화 관리(runtime dialogue management)** 방식을 채택했다.

**Rails의 정의**:
- 특정 주제만 다루도록 제한(topical control)
- 사전 정의된 대화 경로 강제(predefined dialogue paths)
- 언어 스타일 통제(language style)
- 구조화된 데이터 추출(structured data extraction)

**기존 접근법과의 차별점**:
- **Explicit Moderation API**: OpenAI, ActiveFence 등 외부 API 사용
- **Critique Chains**: Constitutional AI의 비평 체인
- **Output Parsing**: guardrails.ai의 스키마 검증
- **Individual Guardrails**: LLM-Guard의 개별 가드레일

→ NeMo Guardrails는 **이 모든 접근법을 통합**하고 **대화 모델링 기능 추가**

### 2. 5가지 가드레일 타입

```yaml
# Guardrails 실행 플로우
Input Rails → Dialog Rails → Retrieval Rails → Execution Rails → Output Rails
```

#### (1) Input Rails
**사용자 입력 전처리**:
- 입력 거부(reject) 또는 변환(alter)
- 민감 데이터 마스킹(PII, email 주소)
- 프롬프트 인젝션 탐지
- Jailbreak 휴리스틱 검사

```yaml
# config.yml 예시
rails:
  input:
    flows:
      - check jailbreak
      - mask sensitive data on input
    config:
      sensitive_data_detection:
        entities:
          - PERSON
          - EMAIL_ADDRESS
```

#### (2) Dialog Rails
**대화 흐름 제어** (Canonical Form 메시지 기반):
- 특정 액션 실행 여부 결정
- LLM 호출 vs 사전 정의 응답 선택
- 대화 경로 강제

```colang
# greeting.co - Colang 1.0 예시
define user express greeting
  "Hello!"
  "Good afternoon!"

define flow
  user express greeting
  bot express greeting
  bot offer to help

define bot express greeting
  "Hello there!"

define bot offer to help
  "How can I help you today?"
```

**Insult 처리 예시**:
```colang
define user express insult
  "You are stupid"

define flow
  user express insult
  bot express calmly willingness to help
```

#### (3) Retrieval Rails
**RAG 시나리오에서 검색된 청크(chunk) 필터링**:
- 검색 결과 거부 또는 변경
- 민감 데이터 마스킹
- 관련성 검증

#### (4) Execution Rails
**커스텀 액션(도구) 입출력 제어**:
- 액션 파라미터 검증
- 실행 결과 필터링

#### (5) Output Rails
**LLM 생성 출력 후처리**:
- 사실 확인(fact-checking)
- 환각 탐지(hallucination detection)
- 독성 필터링(toxicity filtering)
- 민감 정보 제거

```yaml
rails:
  output:
    flows:
      - self check facts
      - self check hallucination
      - activefence moderation on input
```

### 3. Colang: 대화 모델링 DSL

**Colang의 특징**:
- Python 유사 문법
- 유연하면서도 제어 가능한 대화 흐름 설계
- **현재 2개 버전 지원**: Colang 1.0(기본) + Colang 2.0(beta)
- 버전 0.12.0부터 Colang 2.0이 기본값 예정

**Colang vs 기존 DSL**:
- AgentSpec: 제약 조건 기반 DSL (predicates + enforcement actions)
- NeMo Guardrails: 대화 흐름 기반 DSL (user intent → bot response)

**구성 파일 구조**:
```
config/
├── config.yml        # LLM 모델, 활성화할 rails 설정
├── config.py         # 커스텀 초기화 코드
├── actions.py        # 커스텀 Python 액션
├── rails.co          # Colang 정의 파일
```

### 4. 내장 가드레일 라이브러리

**보안/안전**:
- Jailbreak Detection (휴리스틱)
- Self-Check Input/Output Moderation
- LlamaGuard-based Content Moderation
- ActiveFence Input Moderation

**사실성 검증**:
- Self-Check Fact-checking
- Hallucination Detection
- AlignScore-based Fact-checking
- Patronus Lynx RAG Hallucination Detection
- Got It AI TruthChecker API

**프라이버시**:
- Presidio-based Sensitive Data Detection

**새로운 가드레일**:
- AutoAlign-based guardrails

> ⚠️ **주의**: 내장 가드레일은 빠른 시작용이며, **프로덕션 환경에서는 추가 개발 및 테스트 필요**

### 5. 사용 예시 (Python API)

```python
from nemoguardrails import LLMRails, RailsConfig

# 1. 설정 로드
config = RailsConfig.from_path("PATH/TO/CONFIG")
rails = LLMRails(config)

# 2. LLM 호출 (OpenAI Chat Completions API와 유사)
completion = rails.generate(
    messages=[{"role": "user", "content": "Hello world!"}]
)

# 출력: {"role": "assistant", "content": "Hi! How can I help you?"}
```

**비동기 API**:
```python
# NeMo Guardrails는 async-first 설계
completion = await rails.generate_async(
    messages=[{"role": "user", "content": "Hello!"}]
)
```

**LangChain 통합**:
- LangChain `Runnable` 래핑 가능
- 가드레일 내부에서 LangChain 체인 호출 가능

### 6. 지원 LLM 모델

- OpenAI GPT-3.5, GPT-4
- LLaMa-2
- Falcon
- Vicuna
- Mosaic

**LLM 독립성**: 가드레일 설정은 모델에 무관하게 재사용 가능

### 7. Guardrails Server

**CLI 서버 실행**:
```bash
nemoguardrails server --config PATH/TO/CONFIGS --port PORT
```

**HTTP API 예시**:
```bash
POST /v1/chat/completions
{
  "config_id": "sample",
  "messages": [{
    "role": "user",
    "content": "Hello! What can you do for me?"
  }]
}
```

**Docker 지원**:
- 공식 Dockerfile 제공
- [Using Docker 가이드](https://docs.nvidia.com/nemo/guardrails/user-guides/advanced/using-docker.html) 참고

### 8. 평가 도구

**`nemoguardrails evaluate` 명령어**:
- Topical rails 평가
- Fact-checking 성능 측정
- Moderation (jailbreak, output moderation)
- Hallucination 탐지

**LLM Vulnerability Scanning**:
- [ABC Bot 샘플 리포트](https://docs.nvidia.com/nemo/guardrails/evaluation/llm-vulnerability-scanning.html) 제공
- 다양한 가드레일 구성의 보호 효과 비교

### 9. 사용 사례

1. **RAG (Retrieval Augmented Generation)**
   - Fact-checking 적용
   - Output moderation

2. **도메인 특화 어시스턴트(챗봇)**
   - 주제 제한(on-topic)
   - 대화 흐름 설계 강제

3. **LLM 엔드포인트 보호**
   - 커스텀 LLM에 가드레일 추가
   - 안전한 고객 상호작용

4. **LangChain Chains**
   - 기존 체인에 가드레일 레이어 추가

5. **Agents (출시 예정)**
   - LLM 기반 에이전트 보호

## My Insights

### 1. AgentSpec vs NeMo Guardrails 비교

| 측면 | AgentSpec | NeMo Guardrails |
|------|-----------|-----------------|
| **핵심 접근** | 제약 조건 기반 검증 | 대화 흐름 기반 제어 |
| **DSL 목적** | 실행 시점 안전성 검증 | 대화 경로 모델링 |
| **주요 개념** | Trigger → Check → Enforce | Input → Dialog → Output Rails |
| **적용 시점** | 에이전트 액션 실행 전/후 | LLM 입출력 전체 파이프라인 |
| **세밀도** | 함수 호출 단위(micro-level) | 대화 턴 단위(macro-level) |
| **표현력** | 술어 논리 기반 제약 | Python 유사 대화 스크립트 |

**통합 가능성**:
- AgentSpec을 Execution Rails로 활용 가능
- NeMo는 "액션 실행 시 무엇을 검증할까?"를 다루지 못함
- AgentSpec은 "언제 어떤 액션을 실행할까?"를 다루지 못함
- **상호 보완적 관계**

### 2. Colang의 혁신성과 한계

**혁신적인 점**:
- LLM 대화를 **선언적으로 모델링**하는 첫 사례
- "사용자가 인사하면 → 봇이 인사하고 도움 제안"을 코드로 표현
- Constitutional AI의 암묵적 제약을 **명시적 플로우**로 전환

**한계**:
- **유지보수 복잡도**: 대화 시나리오가 많아질수록 `.co` 파일 관리 부담
- **LLM 진화와의 괴리**: 모델이 발전해도 대화 스크립트는 수동 업데이트
- **테스트 어려움**: "어떤 입력이 `express greeting`으로 분류될까?" 검증 필요
- **Colang 2.0 베타**: 아직 안정화되지 않음 (0.12.0에서 기본값 예정)

### 3. 5-Layer Architecture의 실용성

**강점**:
- **체계적 방어선**: Input → Dialog → Retrieval → Execution → Output
- **모듈화**: 각 레이어별 독립적 테스트 가능
- **유연성**: 필요한 레이어만 선택적 활성화

**약점**:
- **성능 오버헤드**: 5단계 필터링 → 레이턴시 증가 우려
- **디버깅 복잡도**: 어느 레이어에서 차단되었는지 추적 어려움
- **설정 복잡도**: `config.yml`, `.co` 파일, `actions.py` 등 관리 포인트 증가

### 4. 내장 가드레일의 신뢰성 문제

**NVIDIA의 경고**:
> "내장 가드레일은 빠른 시작용이며 프로덕션에서는 추가 개발 필요"

**이유 추정**:
- **Self-Check 방식의 한계**: LLM이 자기 출력을 검증 → 순환 논리
- **Jailbreak Detection 휴리스틱**: 키워드 매칭 기반 → 우회 가능
- **False Positive 위험**: 합법적 질문을 차단할 수 있음

**시사점**:
- NeMo는 **프레임워크 제공**에 집중, 가드레일 자체는 커뮤니티 의존
- Guardrails for LLM 논문의 모듈화 접근법과 유사
- **프로덕션 수준 가드레일은 직접 구현 필요**

### 5. Runtime Dialogue Management의 장단점

**장점**:
- **모델 무관성**: GPT-4 → LLaMa-2 전환 시 설정 재사용
- **즉시 적용**: Fine-tuning 없이 가드레일 추가
- **해석 가능성**: Colang 스크립트로 동작 추적

**단점**:
- **프롬프트 엔지니어링 의존**: LLM이 대화 의도를 정확히 분류해야 함
- **Context Window 소비**: 가드레일 지시사항이 프롬프트에 포함
- **모델 능력 제약**: GPT-3.5는 복잡한 Colang 처리 실패 가능

### 6. LangChain 통합의 전략적 의미

**통합 방식**:
- LangChain `Runnable` 래핑 → 기존 체인에 가드레일 추가
- Colang 내부에서 LangChain 호출 → 대화 흐름 중 도구 사용

**생태계 효과**:
- LangChain 사용자에게 NeMo Guardrails 노출
- LangChain의 도구(tools) 생태계 활용 가능
- **상호 보완적 포지셔닝**: LangChain(도구 오케스트레이션) + NeMo(안전 제어)

### 7. Evaluation의 현실적 어려움

**제공되는 평가**:
- Topical rails, Fact-checking, Moderation, Hallucination

**부족한 부분**:
- **Dialog Rails 평가**: "대화가 의도한 경로를 따랐는가?" 측정 방법 부재
- **User Experience**: 가드레일이 UX를 해치는지 정량화 어려움
- **Red Teaming**: 내부 평가만으로는 실제 공격 대응 검증 불가

**LLM Vulnerability Scanning의 한계**:
- 샘플 리포트(ABC Bot)만 제공 → 일반화 어려움
- 각 도메인별 재평가 필요

### 8. SDK 설계 시 적용 전략

**NeMo Guardrails를 활용할 시나리오**:
1. **대화형 어시스턴트**: Colang으로 주요 대화 경로 설계
2. **RAG 파이프라인**: Retrieval Rails로 검색 품질 보장
3. **외부 API 호출**: Execution Rails로 도구 사용 검증

**AgentSpec과 결합 시**:
```
User Input
  ↓
[NeMo Input Rails] → Jailbreak/PII 검사
  ↓
[NeMo Dialog Rails] → 대화 흐름 결정 ("액션 X 호출해야 함")
  ↓
[AgentSpec Hook] → 액션 실행 전 제약 조건 검증 (predicates)
  ↓
Execute Action
  ↓
[AgentSpec Enforcement] → 결과 검증 (제약 위반 시 fallback)
  ↓
[NeMo Output Rails] → Fact-check/Hallucination 검사
  ↓
Return to User
```

**통합 설계 원칙**:
- **NeMo**: "무엇을 해야 하는가"(what to do)
- **AgentSpec**: "어떻게 안전하게 하는가"(how to do safely)

### 9. 오픈소스 전략의 성공 요인

**GitHub 5.3k stars의 비결**:
- **NVIDIA 브랜딩**: 대기업 신뢰성
- **EMNLP 2023 채택**: 학술적 검증
- **풍부한 예제**: `examples/` 폴더 + 샘플 봇
- **활발한 커뮤니티**: 100명 기여자, 주간 업데이트
- **명확한 문서**: docs.nvidia.com의 체계적 가이드

**한계**:
- **Beta 장기화**: 0.1.0(2023) → 0.18.0(2025)인데 여전히 "beta"
- **Breaking Changes**: Colang 1.0 → 2.0 마이그레이션 부담
- **프로덕션 책임 회피**: "내장 가드레일은 참고용" 면책

### 10. 향후 발전 방향 예측

**Agent 지원 (COMING SOON)**:
- 현재 NeMo는 대화 중심 → 에이전트 워크플로우는 미지원
- AgentSpec의 액션 제어와 경쟁 관계 형성 예상

**Colang 2.0 안정화**:
- 0.12.0에서 기본값 전환 예정
- 1.0 사용자의 마이그레이션 부담 → 점진적 전환 전략 필요

**엔터프라이즈 기능**:
- 감사 로그(audit logging)
- 가드레일 성능 모니터링
- A/B 테스트 프레임워크

**보안 강화**:
- Jailbreak 휴리스틱 → 머신러닝 기반 탐지
- Adversarial Testing 자동화

---

**결론**: NeMo Guardrails는 **대화 흐름 모델링**이라는 독특한 각도로 LLM 안전성 문제에 접근했다. Colang DSL은 혁신적이지만 학습 곡선이 있고, 내장 가드레일은 참고용이므로 프로덕션에서는 커스터마이징이 필수다. AgentSpec과 상호 보완적이며, 두 접근법을 결합하면 **대화 수준(NeMo) + 실행 수준(AgentSpec) 안전성**을 모두 확보할 수 있다.
