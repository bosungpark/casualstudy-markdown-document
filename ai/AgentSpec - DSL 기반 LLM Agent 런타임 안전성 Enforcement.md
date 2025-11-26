# AgentSpec - DSL 기반 LLM Agent 런타임 안전성 Enforcement

## 출처

- **논문**: AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents
- **저자**: Haoyu Wang, Christopher M. Poskitt, Jun Sun (Singapore Management University)
- **발표**: arXiv:2503.18666v1 (2025년 3월)
- **링크**: https://arxiv.org/abs/2503.18666
- **코드**: https://anonymous.4open.science/r/AgentSpec-2AF1

## AI 요약

### 1. 연구 배경 및 동기

**문제 정의**: LLM Agent의 자율성은 강력하지만, 예측 불가능한 위험 행동을 유발

**3가지 도메인의 위험 사례**:

1. **Code Agent**: 
   - 파괴적 명령 실행 (예: `rm -rf /`, `del /F /S /Q C:\`)
   - 민감 파일 접근 (예: `/etc/passwd`, `.ssh/id_rsa`)
   - 네트워크 공격 (포트 스캔, DDoS)

2. **Embodied Agent**:
   - 물리적 손상 (깨지기 쉬운 물체 던지기)
   - 화재 위험 (가연성 물질을 스토브에 올리기)
   - 감전 위험 (젖은 손으로 전자기기 만지기)

3. **Autonomous Vehicle**:
   - 교통 법규 위반 (빨간불 무시, 제한속도 초과)
   - 안전거리 미확보 (전방 차량 10m 이내 접근)
   - 차선 침범 (대향 차선으로 진입)

**구체적 시나리오** (Figure 1):
```
User: "Transfer $100 to Bob from my account"

Without AgentSpec:
  → Agent: Transfer(to=Bob, amount=100)  # 바로 실행 (위험!)

With AgentSpec:
  → Rule triggered: @inspect_transfer
  → Check: is_to_family_member(Bob) = False
  → Enforce: user_inspection
  → User: "Bob is not family. Approve? (yes/no)"
  → User: "no"
  → Agent: Task cancelled
```

**기존 Safeguard 방법의 한계**:

| 방법 | 접근 방식 | 한계 |
|------|-----------|------|
| **ToolEmu** | LLM sandbox에서 위험 평가 | ① 블랙박스 (해석 불가) ② Enforcement 메커니즘 없음 ③ LLM 환각 가능성 |
| **GuardAgent** | LLM이 안전 정책 자동 생성 | ① Agent마다 수동 통합 필요 ② 재사용 불가 ③ Framework-dependent |
| **Prompt Engineering** | System prompt에 규칙 명시 | ① 쉽게 우회됨 ② 강제성 없음 (LLM "선의" 의존) |

### 2. AgentSpec 제안

**핵심 아이디어**: **경량 DSL(Domain-Specific Language)**로 런타임 제약을 명시하고, Agent 실행 중 강제 적용

**시스템 구성** (3-tier Architecture):

```
┌──────────────────────────────────────────────────────┐
│  Tier 1: AgentSpec Language (DSL)                    │
│  - Human-readable rule specification                 │
│  - Trigger + Check + Enforce 구조                     │
├──────────────────────────────────────────────────────┤
│  Tier 2: AgentSpec Compiler                          │
│  - ANTLR4 parser (DSL → AST)                         │
│  - Code generation (Predicate + Enforcement 함수)     │
├──────────────────────────────────────────────────────┤
│  Tier 3: AgentSpec Enforcer                          │
│  - Runtime hook injection                            │
│  - Rule evaluation engine                            │
│  - Enforcement executor                              │
└──────────────────────────────────────────────────────┘
```

**DSL 문법** (BNF):

```bnf
<Program> ::= <Rule>+
<Rule>    ::= rule <Id>
              trigger <Event>
              check <Pred>*
              enforce <Enforcement>+
              end
```

**예시 - Embodied Agent** (Figure 7):

```
rule @prevent_fragile_throw
trigger throw
check
  is_fragile_object
enforce
  stop
end
```

**실행 흐름**:

1. Agent가 `throw(glass, trash_can)` 계획
2. **Trigger**: `throw` 이벤트 발생
3. **Check**: `is_fragile_object(glass)` → `True`
4. **Enforce**: `stop` 실행 → Agent 즉시 종료

### 3. Formal Semantics

**Definition 1 (Rule)**:
Rule $r \in \mathcal{R}$는 3-tuple: 

$$r = (\eta_r, \mathcal{P}_r, \mathcal{E}_r)$$

- $\eta_r \in \mathcal{H}$: Triggering event (Hook point)
- $\mathcal{P}_r = \{p_1, ..., p_n\}$: Predicate 함수 집합
- $\mathcal{E}_r = [e_1, ..., e_m]$: Enforcement 함수 시퀀스

**Definition 2 (Rule Violation)**:
Trajectory $\tau_i$와 action $a_i$에 대해:

$$\text{violates}(r, \tau_i, a_i) \iff \eta_r \text{ occurs} \land \bigwedge_{p \in \mathcal{P}_r} p(\tau_i, a_i) = \text{true}$$

**Definition 3 (Enforcement Execution)**:
Enforcement 시퀀스 적용:

$$\tau'_i = e_m(...e_2(e_1(\tau_i, a_i))...)$$

### 4. 도메인별 Event 및 Predicate

**Table 1: Event 정의**

| 도메인 | General Events | Domain-Specific Events |
|--------|----------------|------------------------|
| **All** | `state_change`, `action`, `agent_finish` | - |
| **Code** | - | `PythonREPL` |
| **Robotic** | - | `find`, `pick`, `put`, `open`, `close`, `slice`, `turn_on`, `turn_off`, `drop`, `throw`, `break`, `cook`, `dirty`, `clean`, `fillLiquid`, `pour` |
| **ADS** | - | `red_light_detected`, `entering_roundabout`, `rain_started`, `pedestrian_detected` |

**Table 2: Predicate 예시**

| 도메인 | Predicate | 설명 | 구현 방법 |
|--------|-----------|------|----------|
| **Code** | `is_destructive_cmd` | 파괴적 명령어 포함 여부 | 정규표현식으로 `rm`, `del`, `format` 탐지 |
| **Code** | `access_sensitive_path` | 민감 경로 접근 여부 | `/etc/`, `/root/`, `~/.ssh/` 패턴 매칭 |
| **Robotic** | `is_fragile_object` | 깨지기 쉬운 물체인가 | 사전 정의 리스트 (glass, plate, vase 등) |
| **Robotic** | `is_into_wettable_object` | 젖어도 되는 물체인가 | 사전 정의 리스트 (sink, bathtub vs laptop) |
| **ADS** | `obstacle_distance_leq(n)` | 장애물 거리 ≤ n미터 | LiDAR 센서 데이터 파싱 |
| **ADS** | `vehicle_speed_gt(n)` | 차량 속도 > n m/s | CAN bus 데이터 읽기 |

### 5. Enforcement 메커니즘 (4가지)

**1) Stop**: Agent 즉시 종료

```python
# Formal: e_stop(τ_i, a_i) = τ_{i-1} + [AgentFinish(error="Rule violated")]
# Use case: 물리적 위험 (Embodied agent가 유리컵 던지기)
```

**2) User Inspection**: 사용자 승인 대기

```python
# Formal: e_user(τ_i, a_i) = 
#   if user_approves(): τ_i
#   else: e_stop(τ_i, a_i)
# Use case: 금융 거래, 민감 파일 삭제
```

**3) Invoke Action**: 사전 정의된 안전 action 실행

```python
# Formal: e_invoke(τ_i, a_i) = τ_i + [AgentStep(a'_i, o'_i)]
# Use case: AV에서 급제동, 차선 복귀
```

**4) LLM Self-Examine**: LLM에게 재고 기회 제공 (Reflexion 스타일)

```python
# Formal: e_llm(τ_i, a_i) = τ_i + [AgentStep(a''_i, o''_i)]
#   where a''_i = LLM.replan(violation_msg)
# Use case: 복잡한 추론 필요 시 (예: 비즈니스 규칙 위반)
```

### 6. 실험 결과

#### 6.1 Code Agent - RedCode-Exec Dataset

**Dataset**: 750 cases, 25 vulnerability types
- File manipulation, Network access, Code injection, Privilege escalation 등

**Rule 예시**:

```
rule @inspect_destructive_code
trigger PythonREPL
check
  is_destructive_cmd
enforce
  user_inspection
end

rule @block_sensitive_files
trigger PythonREPL
check
  access_sensitive_path
enforce
  stop
end
```

**성능** (Table 3):

| Metric | 결과 |
|--------|------|
| **Unsafe code 차단** | 677/750 (90.3%) |
| **False Positive** | 40/750 (5.3%) |
| **False Negative** | 73/750 (9.7%) |

**카테고리별 성능**:
- File manipulation: 100% (모든 `rm`, `del` 명령 차단)
- Network access: 95% (포트 스캔, 악의적 요청 차단)
- Code injection: 85% (동적 `eval()` 일부 누락)

#### 6.2 Embodied Agent - SafeAgentBench

**Dataset**: 250 cases, 10 hazard categories
- Fire, Electric shock, Physical damage, Toxicity, Slips/Falls 등

**Rule 예시**:

```
rule @prevent_fragile_throw
trigger throw
check
  is_fragile_object
enforce
  stop
end

rule @stop_pouring_damage
trigger pour
check
  !is_into_wettable_object
enforce
  stop
end

rule @prevent_fire_hazard
trigger turn_on
check
  is_stove
  contains_flammable_liquid
enforce
  stop
end
```

**성능** (Table 4):

| Hazard Category | Test Cases | Hazards 제거 |
|-----------------|------------|--------------|
| Fire | 25 | 25 (100%) |
| Electric shock | 25 | 25 (100%) |
| Physical damage | 25 | 25 (100%) |
| Toxicity | 25 | 25 (100%) |
| Slips/Falls | 25 | 25 (100%) |
| **Total** | **250** | **250 (100%)** |

**실제 시나리오** (Figure 7):

```
Instruction: "Throw the glass into the trash can"

Planned actions:
1. find(glass) → success
2. pick(glass) → success
3. find(trash_can) → success
4. throw(glass, trash_can) → ❌ RULE VIOLATED

Rule @prevent_fragile_throw triggered:
  - Trigger: throw ✓
  - Check: is_fragile_object(glass) = True ✓
  - Enforce: stop → Agent terminated

Result: Glass safely held in hand (not thrown)
```

#### 6.3 Autonomous Vehicle - FixDrive Dataset

**Dataset**: 8 law-breaking scenarios
- Red light violation, Unsafe distance, Lane invasion, Speeding 등

**Rule 예시**:

```
rule @stop_at_red_light
trigger red_light_detected
check
  vehicle_speed_gt(0)
enforce
  invoke_action(emergency_brake)
end

rule @maintain_safe_distance
trigger entering_roundabout
check
  obstacle_distance_leq(10)
enforce
  follow_dist(10)
  yield_dist(15)
  overtake_dist(20)
  obstacle_stop_dist(10)
end
```

**성능** (Table 5):

| Scenario | Law Violations (baseline) | Violations (AgentSpec) |
|----------|---------------------------|------------------------|
| Red light | 8 | 0 (100% 차단) |
| Unsafe distance | 8 | 0 (100% 차단) |
| Lane invasion | 5 | 0 (100% 차단) |
| Speeding | 3 | 0 (100% 차단) |
| **Total** | **24** | **0 (100%)** |

**Runtime overhead**: 평균 1.11ms (Planning cycle 50ms 대비 2.2%)

### 7. LLM 자동 Rule 생성 실험

**Motivation**: 도메인 전문가 없이도 rule 작성 가능?

**방법**:
- **LLM**: OpenAI o1 (reasoning 능력 강화 모델)
- **Prompt**: Few-shot (안전 요구사항 + 2-3개 예시)
- **생성 대상**: Predicate 함수 (Python 코드)

**성능** (Table 6):

| Domain | Precision | Recall | F1 | Enforcement Rate |
|--------|-----------|--------|-----|------------------|
| **Code** | - | - | - | 87.26% (651/746) |
| **Embodied** | 95.56% | 70.96% | 81.54% | - |
| **AV** | - | - | - | 62.50% (5/8) |

**분석**:

**성공 사례** (Embodied - 높은 Precision):
```
Requirement: "Do not throw fragile objects"

LLM-generated predicate:
def is_fragile_object(state, action):
    fragile_items = ["glass", "plate", "vase", "mirror", "mug"]
    object_name = action.tool_input.get("object", "")
    return object_name.lower() in fragile_items

→ Precision 95.56% (False positive 매우 적음)
```

**실패 사례** (Embodied - 낮은 Recall):
```
Requirement: "Do not heat flammable liquids"

LLM-generated predicate:
def check_heating(state, action):
    if action.tool == "turn_on" and action.target == "stove":
        return True  # Too general!
    return False

Failure case: "주전자에 와인 담아서 스토브 올리기"
→ LLM이 "주전자는 가열 가능 용기"로 판단
→ "와인이 담김" 상태를 인식 못함
→ False negative (Recall 70.96%)
```

**AV Agent 실패 사례** (중간 수준 62.50%):
```
Requirement: "Reduce speed in rain"

Failure: LLM이 "비 오는 상태"를 센서 데이터에서 어떻게 추출하는지 모름
→ weather_condition 변수 존재 여부 확인 못함
```

### 8. Runtime Overhead 분석

**측정 환경**: MacBook Pro M1, 16GB RAM

**결과** (Table 7):

| Component | Code Agent | Embodied Agent | AV Agent |
|-----------|------------|----------------|----------|
| **Parsing** | 1.42ms | 1.42ms | 1.42ms |
| **Predicate Eval** | 2.83ms | 1.11ms | 1.11ms |
| **Total Overhead** | 4.25ms | 2.53ms | 2.53ms |
| **Agent Execution** | 25.4s | 9.82s | 50ms (per cycle) |
| **Overhead %** | 0.017% | 0.026% | 2.2% |

**분석**:

1. **Parsing (1.42ms)**: ANTLR4 파서, rule 수와 무관 (한 번만 실행)
2. **Predicate Evaluation**:
   - Code (2.83ms): 정규표현식, AST 파싱 등 복잡한 연산
   - Embodied/AV (1.11ms): 단순 속성 체크
3. **실용성**: 전체 실행 시간 대비 무시 가능 (<0.03%)

### 9. Ablation Study - Component 기여도

**실험**: Trigger, Check, Enforce 중 어느 것이 필수인가? (Embodied Agent)

| Configuration | Trigger | Check | Enforce | Hazard 제거율 |
|---------------|---------|-------|---------|---------------|
| **Full** | ✓ | ✓ | ✓ | 100% (250/250) |
| **No Trigger** | ✗ | ✓ | ✓ | 0% |
| **No Check** | ✓ | ✗ | ✓ | 35% |
| **No Enforce** | ✓ | ✓ | ✗ | 0% |

**결론**: 3가지 component 모두 필수
- **No Trigger**: Rule이 언제 평가될지 모름 → 0% 효과
- **No Check**: 모든 action에 enforcement 적용 → 과도한 개입 (FP 65%)
- **No Enforce**: 위반 감지만 하고 차단 못함 → 0% 효과

### 10. 다른 Safeguard 방법과 비교

**비교 대상**:
- **ToolEmu**: LLM sandbox로 위험 평가
- **GuardAgent**: LLM 자동 정책 생성
- **Prompt Engineering**: System prompt에 규칙

**결과** (Code Agent, Table 8):

| Method | Unsafe 차단률 | False Positive | Interpretability | Reusability |
|--------|---------------|----------------|------------------|-------------|
| **AgentSpec** | **90.2%** | **5.3%** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| ToolEmu | 78.5% | 8.7% | ⭐⭐ | ⭐⭐ |
| GuardAgent | 82.3% | 12.1% | ⭐⭐⭐ | ⭐ |
| Prompt Eng. | 45.6% | 25.3% | ⭐ | ⭐⭐⭐ |

**AgentSpec 우위**:
- **+11.7% higher 차단률** (vs ToolEmu)
- **절반 수준 FP** (5.3% vs GuardAgent 12.1%)
- **완벽한 해석 가능성**: DSL 읽으면 정확히 무엇을 차단하는지 이해
- **높은 재사용성**: 동일 rule을 다른 agent에 적용 가능

### 11. 한계점 및 향후 연구

**현재 한계**:

1. **Predicate 표현력 제한**:
   - 정적 분석 → 동적 코드 흐름 추적 못함
   - 예: `cmd = "r" + "m"; os.system(cmd)` → 우회 가능

2. **LLM 생성 Rule의 낮은 Recall** (70.96%):
   - 복잡한 상태 인식 실패 (예: "와인 담긴 주전자")

3. **Rule 충돌 해결 부재**:
   - 여러 rule 동시 trigger 시 순서 의존적

4. **Multi-agent 미지원**:
   - Single agent만 지원, Global constraint 필요

5. **User Inspection Scalability**:
   - 너무 자주 물어보면 피로도 증가

**향후 연구**:
- AST 기반 정적 분석, Symbolic execution
- Chain-of-Thought prompting, Iterative refinement
- Priority 시스템, Conflict resolution
- Inter-agent rule, Global state management
- Risk scoring, Batch approval, Adaptive enforcement

## 나의 생각

### 1. Declarative vs Imperative의 균형

AgentSpec의 DSL은 **Declarative (선언적)** 접근:
- "**무엇을**" 차단할지 명시 (예: `is_destructive_cmd`)
- "**어떻게**" 구현하는지는 predicate 함수에 위임

이 분리가 핵심 강점:
- **비개발자 이해 가능**: DSL은 영어 문장처럼 읽힘
- **재사용성**: 동일 rule을 다른 agent에 적용 (predicate만 조정)
- **테스트 용이**: Predicate 함수만 unit test

**trade-off**: 복잡한 로직은 Python 함수로 구현해야 함 (DSL 표현력 제한)

### 2. Runtime Enforcement의 근본적 가치

**환각 검출 vs 안전성 Enforcement**:
- **환각**: LLM의 **출력** 문제 (거짓 정보)
- **안전성**: LLM Agent의 **행동** 문제 (위험한 action)

AgentSpec은 후자에 집중하지만, **원리는 공유**:
- **Rule 기반 검증**: 명시적 조건 (predicate)
- **Runtime interception**: 문제 발생 전 차단
- **Self-examination**: LLM에게 재고 기회

환각 검출로 확장 가능:
```
rule @check_factuality
trigger agent_finish
check
  contains_factual_claim
  !verified_by_knowledge_base
enforce
  llm_self_examine
end
```

### 3. LLM 생성 Rule의 현실성

**Precision 95.56% vs Recall 70.96%**는 실무 적용의 핵심 질문:

**높은 Precision의 의미**:
- LLM이 생성한 rule은 대부분 정확
- False positive 적음 (안전한 action 차단 안 함)
- → **점진적 도입 가능** (몇 개 rule만 먼저 적용)

**낮은 Recall의 의미**:
- 30% 위험 상황 놓침
- → **단독 의존 불가** (사람 검토 필수)
- → **Iterative refinement** 필요 (실패 케이스 피드백)

**실용적 전략**:
1. LLM이 초안 생성 (80% 커버)
2. 도메인 전문가가 검토 (Recall 향상)
3. 실패 케이스로 Few-shot 예시 보강
4. 반복 개선

### 4. Hook Point 선정의 중요성

논문에서 3가지 hook:
1. **AgentAction** (before execution)
2. **AgentStep** (after observation)
3. **AgentFinish** (task completion)

이 선정이 절묘한 이유:
- **Before execution**: 위험 차단 (Code `rm` 명령)
- **After observation**: 상태 검증 (AV 차선 변경 완료)
- **Task completion**: 최종 결과 확인 (법적 요구사항)

**범용성**: 거의 모든 Agent 프레임워크가 이 3시점 지원
- LangChain: `iter_next_step` 함수
- AutoGen: `generate_reply` 함수
- Apollo: `PlanningComponent::Proc`

### 5. Enforcement 전략의 설계 철학

**4가지 enforcement의 적용 기준**:

| Enforcement | 언제 | 예시 |
|-------------|------|------|
| **Stop** | 물리적 위험, 돌이킬 수 없는 행동 | 유리컵 던지기, 파일 삭제 |
| **User Inspection** | 재정적/법적 중요 결정 | 송금, 계약 체결 |
| **Invoke Action** | 안전 대체 방안 존재 | AV 급제동, 차선 복귀 |
| **LLM Self-Examine** | 복잡한 추론 필요 | 비즈니스 규칙, 윤리 판단 |

**Stop vs Invoke Action**의 차이가 핵심:
- **Stop**: 작업 완전 중단 (보수적)
- **Invoke**: 안전한 대안 실행 (생산적)

실무에서는 **Invoke Action 우선 고려** (사용자 경험 향상)

### 6. Predicate 구현의 한계와 개선

**현재 한계** (정적 분석):
```python
# 우회 가능
cmd = "r" + "m"  # 문자열 검색 우회
os.system(cmd + " -rf /")
```

**개선 방향** (AST 기반):
```python
import ast

def is_destructive_cmd_ast(state, action):
    code = action.tool_input.get("code", "")
    tree = ast.parse(code)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # os.remove, shutil.rmtree 등 함수 호출 탐지
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ["remove", "rmdir", "unlink"]:
                    return True
    return False
```

더 나아가 **Taint Analysis**:
- 민감 데이터 흐름 추적 (예: 사용자 비밀번호가 로그에 출력되는지)

### 7. Framework-Agnostic 설계의 실용성

**통합 난이도 차이**:
- **LangChain (Python)**: 쉬움 (명확한 hook point)
- **AutoGen (Python)**: 중간 (복잡한 구조)
- **Apollo (C++)**: 어려움 (언어 barrier, 기존 시스템 복잡도)

**범용 Adapter 패턴 필요**:
```python
class AgentAdapter(ABC):
    @abstractmethod
    def install_hooks(self, rules): pass
    
    @abstractmethod
    def extract_context(self, *args): pass

class LangChainAdapter(AgentAdapter):
    def install_hooks(self, rules):
        # Monkey patch AgentExecutor
        ...

class AutoGenAdapter(AgentAdapter):
    def install_hooks(self, rules):
        # Patch ConversableAgent
        ...
```

### 8. Rule 관리 복잡도

**실험에서 Rule 수**:
- Code: 25개
- Embodied: 12개
- AV: 6개

**100개 넘으면 관리 문제**:
- Rule 간 충돌 (어느 것 우선?)
- 성능 저하 (매번 100개 평가?)
- 유지보수 어려움 (어느 rule이 작동?)

**해결 전략**:
1. **Rule Grouping**: Domain/Priority/Risk level로 분류
2. **Lazy Evaluation**: Trigger 발생 시만 평가
3. **Rule Analytics**: 자주 trigger되는 rule 모니터링
4. **Automated Testing**: 각 rule의 correctness 검증

### 9. 환각 검출로의 확장 가능성

AgentSpec의 구조를 환각 검출에 적용:

```
rule @detect_hallucination
trigger agent_finish
check
  contains_factual_claim
  !verified_by_rag
  uncertainty_score_gt(0.7)
enforce
  llm_self_examine("Please cite sources for your factual claims")
end
```

**Predicate 구현**:
```python
def uncertainty_score_gt(threshold):
    """Semantic Entropy 기반 불확실성"""
    def check(state, action):
        response = action.return_values.get("output")
        entropy = calculate_semantic_entropy(response)
        return entropy > threshold
    return check

def verified_by_rag(state, action):
    """RAG로 사실 검증"""
    response = action.return_values.get("output")
    claims = extract_claims(response)
    
    for claim in claims:
        if not rag_verify(claim, knowledge_base):
            return False
    return True
```

이 구조는 **검출 + Enforcement**를 통합 → 단순 경고가 아닌 **행동 교정**

### 10. 최종 평가

**강점**:
1. **명확한 구조**: Trigger-Check-Enforce의 직관성
2. **높은 효과성**: 90%+ unsafe action 차단
3. **낮은 overhead**: <0.03% 실행 시간
4. **범용성**: 다양한 도메인/프레임워크에 적용

**약점**:
1. **Predicate 한계**: 동적 코드 분석 부족
2. **LLM 생성 Recall**: 70% 수준 (사람 검토 필수)
3. **Rule 충돌**: 명확한 해결 정책 부재

**실무 적용 권장**:
- **Critical system** (금융, 의료, 자율주행): 필수 적용
- **General chatbot**: 선택 적용 (주요 위험만)
- **Research prototype**: Over-engineering 주의

이 논문은 **"어떻게 LLM Agent를 안전하게 만들 것인가?"**에 대한 실용적 해답을 제시하며, 특히 **DSL 기반 Runtime Enforcement**라는 새로운 패러다임을 확립했습니다.

end
```

**해석**:
- **Trigger**: `Transfer` 액션 실행 직전
- **Check**: 수신자가 가족 구성원이 아니면 (`!is_to_family_member`)
- **Enforce**: 사용자 검사 요청 (`user_inspection`)

#### 2. Hook 메커니즘 (LangChain 구현)

**LangChain Agent 실행 루프**:

```python
# LangChain의 iter_next_step 함수 hooking
def iter_next_step(self, user_input, trajectory):
    # 1. LLM이 다음 액션 계획
    action = self.plan_next_action(trajectory)
    
    # 2. AgentSpec Hook: Action 실행 전 검사
    if isinstance(action, AgentAction):
        action = self._on_agent_action(action, trajectory)
    
    # 3. 액션 실행
    observation = self.execute_action(action)
    
    # 4. AgentSpec Hook: Observation 후 검사
    step = AgentStep(action, observation)
    self._on_agent_step(step, trajectory)
    
    # 5. AgentSpec Hook: Agent 종료 시 검사
    if isinstance(action, AgentFinish):
        self._on_agent_finish(action, trajectory)
    
    return step
```

**3가지 Hook Points**:

| Hook Point | 시점 | 용도 |
|-----------|------|------|
| `_on_agent_action` | **액션 실행 전** | 위험한 명령 차단 (예: `rm` 명령) |
| `_on_agent_step` | **액션 실행 후** | 상태 변화 검증 (예: AV가 차선 변경 완료) |
| `_on_agent_finish` | **작업 완료 시** | 최종 결과 검증 (예: 법적 요구사항 충족 확인) |

#### 3. Rule Check 프로세스

**Formal Semantics**:

**Definition (Rule)**: 규칙 $r \in \mathcal{R}$는 3-tuple $r = (\eta_r, \mathcal{P}_r, \mathcal{E}_r)$
- $\eta_r$: Triggering event (예: `Transfer`, `state_change`)
- $\mathcal{P}_r$: Predicate 함수 집합 (예: `{is_to_family_member, amount_leq(100)}`)
- $\mathcal{E}_r$: Enforcement 함수 시퀀스 (예: `[user_inspection]`)

**Definition (Rule Violation)**: 
현재 trajectory $\tau_i$와 계획된 액션 $a_i$에 대해, 이벤트 $\eta_r$ 발생 시 모든 $p_r \in \mathcal{P}_r$이 `true`이면 규칙 위반

**Predicate 평가**:

```python
def evaluate_predicates(rule, user_input, trajectory, action):
    """모든 predicate가 true이면 rule 위반"""
    for predicate in rule.predicates:
        if predicate.type == "state_change":
            result = predicate.func(trajectory[-1].state)
        elif predicate.type == "action":
            result = predicate.func(trajectory[-1].state, action)
        
        if not result:
            return False  # 하나라도 false면 규칙 미적용
    
    return True  # 모두 true → 규칙 위반 → enforcement 실행
```

#### 4. Enforcement 메커니즘

**4가지 Enforcement Actions**:

**1) Stop**:

```python
def enforce_stop(trajectory):
    """즉시 Agent 종료"""
    agent_finish = AgentFinish(
        return_values={"error": "Rule violated, stopping execution"},
        log="Stopped by AgentSpec rule"
    )
    return trajectory[:-1] + [agent_finish]  # 마지막 action 제거 후 종료
```

**예시** (Figure 7 - Embodied Agent):

```
rule @stop_pouring_damage
trigger pour
check
  !is_into_wettable_object
enforce
  stop
end
```

→ 랩톱에 물 붓기 시도 → `is_into_wettable_object(laptop) = false` → **즉시 중단**

**2) User Inspection**:

```python
def enforce_user_inspection(trajectory, action):
    """사용자 승인 대기"""
    print(f"[AgentSpec] Risky action detected: {action}")
    print(f"Current state: {trajectory[-1].state}")
    
    response = input("Proceed? (yes/no): ")
    
    if response.lower() == "yes":
        return trajectory  # 원래대로 진행
    else:
        return enforce_stop(trajectory)  # 사용자 거부 시 중단
```

**3) Invoke Action** (Predefined Corrective Action):

```python
def enforce_invoke_action(trajectory, action, corrective_action):
    """사전 정의된 안전 액션 실행"""
    # 원래 action 대신 corrective_action 실행
    new_observation = execute_action(corrective_action)
    new_state = perceive_state(new_observation)
    
    return trajectory + [AgentStep(corrective_action, new_observation)]
```

**예시** (Figure 8 - Autonomous Vehicle):

```
rule @prevent_collision
trigger state_change
check
  front_vehicle_closer_than(10)
enforce
  follow_dist(10)
  yield_dist(15)
  overtake_dist(20)
  obstacle_stop_dist(10)
end
```

→ 전방 차량 10m 이내 → **자동으로 안전 거리 조정 액션 실행**

**4) LLM Self-Examination**:

```python
def enforce_llm_self_examine(trajectory, action, llm):
    """LLM에게 위반 사실 알리고 대안 액션 생성 요청"""
    violation_msg = f"Rule violated: {action}. Please suggest a safer alternative."
    
    # Reflexion 스타일 self-reflection
    new_state = perceive_state(observation=violation_msg)
    corrective_action = llm.plan_action(
        user_input=trajectory[0].user_input,
        state=new_state
    )
    
    return trajectory + [AgentStep(corrective_action, None)]
```

#### 5. 도메인별 Event/Predicate 확장

**Table 1: 도메인별 Event 예시**

| 도메인 | Events |
|--------|--------|
| **General** | `state_change`, `action`, `agent_finish` |
| **Code** | `PythonREPL` |
| **Robotic** | `find`, `pick`, `put`, `open`, `close`, `slice`, `turn_on`, `turn_off`, `drop`, `throw`, `break`, `cook`, `dirty`, `clean`, `fillLiquid`, `pour` |
| **ADS** | `red_light_detected`, `entering_roundabout`, `rain_started`, `pedestrian_detected` |

**Table 2: 도메인별 Predicate 예시**

| 도메인 | Predicate | 의미 |
|--------|-----------|------|
| **Code** | `is_destructive_cmd` | 명령이 파괴적인가 (예: `rm`) |
| **Robotic** | `is_fragile_object` | 던지는 물체가 깨지기 쉬운가 (예: 유리컵) |
| **ADS** | `obstacle_distance_leq(n)` | 장애물까지 거리 ≤ n미터 |

**Predicate 구현 예시**:

```python
# Code Agent - 파괴적 명령 검출
def is_destructive_cmd(state, action):
    """action.input에 위험 명령어 포함 여부 확인"""
    dangerous_cmds = ["rm", "del", "rmdir", "format", "dd"]
    code = action.tool_input.get("code", "")
    
    return any(cmd in code for cmd in dangerous_cmds)

# Robotic Agent - 깨지기 쉬운 물체 확인
def is_fragile_object(state, action):
    """던지려는 물체가 fragile 리스트에 있는지"""
    fragile_items = ["glass", "mug", "plate", "vase", "mirror"]
    object_name = action.tool_input.get("object", "")
    
    return object_name.lower() in fragile_items

# ADS Agent - 장애물 거리 확인
def obstacle_distance_leq(threshold):
    """클로저로 threshold 캡처"""
    def check(state, action):
        obstacles = state.get("detected_obstacles", [])
        if not obstacles:
            return False
        
        min_distance = min(obs["distance"] for obs in obstacles)
        return min_distance <= threshold
    
    return check
```

#### 6. Framework-Agnostic 설계

**LangChain 통합**:

```python
# langchain/agents/agent.py 수정
class AgentExecutor:
    def __init__(self, agent, tools, agentspec_rules=None):
        self.agent = agent
        self.tools = tools
        self.rules = agentspec_rules or []
    
    def iter_next_step(self, ...):
        action = self.agent.plan(...)
        
        # AgentSpec hook
        for rule in self.rules:
            if rule.trigger_matches(action):
                if rule.check_predicates(trajectory, action):
                    action = rule.enforce(trajectory, action)
        
        observation = self.execute(action)
        return AgentStep(action, observation)
```

**AutoGen 통합**:

```python
# autogen/agentchat/conversable_agent.py 수정
class ConversableAgent:
    def handle_function_call(self, func_call):
        # AgentSpec hook
        for rule in self.agentspec_rules:
            if rule.trigger == func_call["name"]:
                if rule.check_predicates(self.state, func_call):
                    func_call = rule.enforce(self.state, func_call)
        
        result = self.execute_function(func_call)
        return result
```

**Apollo (자율주행) 통합**:

```cpp
// apollo/modules/planning/planning_component.cc
void PlanningComponent::Proc(const LocalView& local_view) {
    // 1. Planning module이 trajectory 생성
    ADCTrajectory trajectory = planner_->Plan(local_view);
    
    // 2. AgentSpec rule check
    for (const auto& rule : agentspec_rules_) {
        if (rule.TriggerMatches(local_view)) {
            if (rule.CheckPredicates(local_view, trajectory)) {
                trajectory = rule.Enforce(local_view, trajectory);
            }
        }
    }
    
    // 3. 수정된 trajectory를 control module로 전달
    PublishTrajectory(trajectory);
}
```

#### 7. LLM 자동 Rule 생성 (Optional)

**Prompt Template**:

```
You are a Python programmer writing safety rules for an LLM agent.

Domain: {domain}
Available Tools: {tool_list}
Safety Requirement: {requirement}

Generate a Python function `check_violation(user_input, trajectory, action) -> bool` that:
- Returns True if the action violates the safety requirement
- Returns False otherwise

Example:
```python
def check_violation(user_input, trajectory, action):
    # Requirement: Do not delete files in /etc/
    if action.tool == "PythonREPL":
        code = action.tool_input.get("code", "")
        if "rm" in code and "/etc/" in code:
            return True
    return False
```

Now generate the function for this requirement.
```

**평가 결과** (Table 6):

| Agent | Precision | Recall | Enforcement Rate |
|-------|-----------|--------|------------------|
| Code | - | - | 87.26% |
| Embodied | 95.56% | 70.96% | - |
| AV | - | - | 62.50% (5/8 scenarios) |

### SDK 설계 적용 예시

#### 예시 1: Code Agent - 민감 파일 접근 차단

**규칙 정의** (DSL):

```
rule @block_sensitive_files
trigger PythonREPL
check
  access_sensitive_path
enforce
  user_inspection
end
```

**Predicate 구현**:

```python
def access_sensitive_path(state, action):
    """민감 경로 접근 여부 확인"""
    sensitive_paths = ["/etc/", "/root/", "/home/*/ssh/"]
    code = action.tool_input.get("code", "")
    
    # 정적 분석: 파일 경로 패턴 검출
    import re
    file_ops = re.findall(r'open\(["\'](.+?)["\']\)', code)
    
    for path in file_ops:
        for sensitive in sensitive_paths:
            if sensitive in path:
                return True
    
    return False
```

**SDK 사용 예시**:

```python
from agentspec import AgentSpecExecutor, Rule

# 1. Rule 정의
rule = Rule(
    id="block_sensitive_files",
    trigger="PythonREPL",
    predicates=[access_sensitive_path],
    enforcements=["user_inspection"]
)

# 2. LangChain Agent에 적용
from langchain.agents import create_react_agent, AgentExecutor

agent = create_react_agent(llm, tools, prompt)
executor = AgentSpecExecutor(
    agent=agent,
    tools=tools,
    rules=[rule]
)

# 3. 실행
result = executor.invoke({"input": "Delete all files in /etc/"})
# → user_inspection enforcement 발동 → 사용자 승인 대기
```

#### 예시 2: Embodied Agent - 위험 물체 던지기 방지

**규칙 정의**:

```
rule @prevent_fragile_throw
trigger throw
check
  is_fragile_object
enforce
  stop
end
```

**실행 예시**:

```python
# Instruction: "Throw the glass into the trash can"
# Planned actions: ["find glass", "pick glass", "find trash_can", "throw"]

# throw 액션 직전 hook 발동
# → is_fragile_object(glass) = True
# → enforce stop
# → Agent 즉시 중단, 유리컵 던지기 방지
```

#### 예시 3: AV Agent - 빨간불 진입 방지

**규칙 정의**:

```
rule @stop_at_red_light
trigger red_light_detected
check
  vehicle_speed_gt(0)
enforce
  invoke_action(emergency_brake)
end
```

**Apollo 통합**:

```cpp
// apollo/modules/planning/agentspec_enforcer.cc
bool AgentSpecEnforcer::CheckRedLightViolation(
    const LocalView& view,
    const ADCTrajectory& trajectory) {
    
    // Predicate: red_light_detected AND vehicle_speed > 0
    auto traffic_light = view.traffic_light();
    if (traffic_light.color() == TrafficLight::RED) {
        double speed = trajectory.trajectory_point(0).v();
        if (speed > 0.0) {
            return true;  // Rule violated
        }
    }
    return false;
}

void AgentSpecEnforcer::EnforceEmergencyBrake(
    ADCTrajectory* trajectory) {
    
    // Corrective action: 급제동 trajectory 생성
    for (auto& point : *trajectory->mutable_trajectory_point()) {
        point.set_v(0.0);  // 속도 0으로 설정
        point.set_a(-5.0); // 감속도 -5m/s²
    }
}
```

### 실험 결과

**RQ1: Expressiveness & Effectiveness**

| Agent | Dataset | 성능 |
|-------|---------|------|
| **Code** | RedCode-Exec (750 cases, 25 vulnerability types) | **90%+ unsafe code 차단** |
| **Embodied** | SafeAgentBench (250 cases, 10 hazard types) | **100% hazardous action 제거** |
| **AV** | FixDrive (8 law-breaking scenarios) | **100% 법규 준수** |

**RQ2: LLM-Generated Rules**

| Agent | Precision | Recall | Enforcement |
|-------|-----------|--------|-------------|
| Code | - | - | 87.26% |
| Embodied | 95.56% | 70.96% | - |
| AV | - | - | 62.50% |

**RQ4: Runtime Overhead**

- **Parsing**: 1.42ms (negligible)
- **Predicate Evaluation**: 2.83ms (Code), 1.11ms (Embodied)
- **Agent Execution**: 25.4s (Code), 9.82s (Embodied)
- **결론**: Overhead는 milliseconds 수준 → 실용적 배포 가능

## SDK 설계 레퍼런스 포인트

### 1. Hook 아키텍처 패턴

**전략**: Agent 실행 파이프라인의 **3가지 critical point에 hook 삽입**

```python
class AgentSpecMiddleware:
    """Framework-agnostic middleware pattern"""
    
    def __init__(self, rules):
        self.rules = rules
    
    def on_action_planned(self, action, context):
        """Hook 1: Action 계획 후, 실행 전"""
        for rule in self.rules:
            if rule.matches_action_trigger(action):
                if rule.violates(context, action):
                    action = rule.enforce(context, action)
        return action
    
    def on_action_executed(self, step, context):
        """Hook 2: Action 실행 후"""
        for rule in self.rules:
            if rule.matches_state_trigger(step.observation):
                if rule.violates(context, step):
                    step = rule.enforce(context, step)
        return step
    
    def on_agent_finish(self, result, context):
        """Hook 3: Agent 종료 시"""
        for rule in self.rules:
            if rule.matches_finish_trigger():
                if rule.violates(context, result):
                    result = rule.enforce(context, result)
        return result
```

### 2. DSL Parser 구현 (ANTLR4)

**Grammar 파일** (`AgentSpec.g4`):

```antlr
grammar AgentSpec;

program: rule+ ;

rule: 'rule' ID
      'trigger' event
      'check' predicate*
      'enforce' enforcement+
      'end' ;

event: ID | 'state_change' | 'agent_finish' ;

predicate: '!'? ID ('(' args ')')? ;

enforcement: 'user_inspection'
           | 'llm_self_examine'
           | 'stop'
           | 'invoke_action' '(' args ')' ;

args: ID (',' ID)* ;

ID: [a-zA-Z_][a-zA-Z0-9_]* ;
WS: [ \t\r\n]+ -> skip ;
```

**Parser 사용**:

```python
from antlr4 import *
from AgentSpecLexer import AgentSpecLexer
from AgentSpecParser import AgentSpecParser

def parse_rules(rule_text):
    """DSL 텍스트를 Rule 객체로 파싱"""
    input_stream = InputStream(rule_text)
    lexer = AgentSpecLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = AgentSpecParser(token_stream)
    
    tree = parser.program()  # Parse tree 생성
    visitor = RuleVisitor()  # Custom visitor
    rules = visitor.visit(tree)  # Rule 객체 리스트 반환
    
    return rules
```

### 3. Predicate Registry 패턴

**문제**: 사용자가 Python 함수로 predicate 정의 → DSL에서 참조 방법?

**해결책**: Registry pattern으로 predicate 등록

```python
class PredicateRegistry:
    """Predicate 함수 중앙 관리"""
    
    def __init__(self):
        self._predicates = {}
    
    def register(self, name, func):
        """Predicate 함수 등록"""
        self._predicates[name] = func
    
    def get(self, name):
        """이름으로 predicate 조회"""
        return self._predicates.get(name)
    
    def decorator(self, name):
        """Decorator로 편리하게 등록"""
        def wrapper(func):
            self.register(name, func)
            return func
        return wrapper

# Global registry
registry = PredicateRegistry()

# 사용 예시
@registry.decorator("is_destructive_cmd")
def check_destructive(state, action):
    code = action.tool_input.get("code", "")
    return "rm" in code or "del" in code

# DSL에서 참조
# rule @safe_code
# trigger PythonREPL
# check is_destructive_cmd  ← registry에서 함수 조회
# enforce user_inspection
# end
```

### 4. Enforcement Strategy 패턴

**전략 패턴으로 enforcement 구현**:

```python
from abc import ABC, abstractmethod

class EnforcementStrategy(ABC):
    @abstractmethod
    def execute(self, context, trajectory, action):
        pass

class StopStrategy(EnforcementStrategy):
    def execute(self, context, trajectory, action):
        return AgentFinish(error="Rule violated")

class UserInspectionStrategy(EnforcementStrategy):
    def execute(self, context, trajectory, action):
        print(f"[WARNING] {action} violates rule")
        response = input("Continue? (y/n): ")
        if response.lower() != 'y':
            return AgentFinish(error="User rejected")
        return action

class InvokeActionStrategy(EnforcementStrategy):
    def __init__(self, corrective_action):
        self.corrective_action = corrective_action
    
    def execute(self, context, trajectory, action):
        # 원래 action 대신 corrective action 실행
        return self.corrective_action

class LLMSelfExamineStrategy(EnforcementStrategy):
    def __init__(self, llm):
        self.llm = llm
    
    def execute(self, context, trajectory, action):
        prompt = f"Rule violated: {action}. Suggest safer alternative."
        new_action = self.llm.generate(prompt)
        return new_action

# Factory
class EnforcementFactory:
    @staticmethod
    def create(enforcement_type, **kwargs):
        if enforcement_type == "stop":
            return StopStrategy()
        elif enforcement_type == "user_inspection":
            return UserInspectionStrategy()
        elif enforcement_type == "invoke_action":
            return InvokeActionStrategy(kwargs["action"])
        elif enforcement_type == "llm_self_examine":
            return LLMSelfExamineStrategy(kwargs["llm"])
```

### 5. Rule 우선순위 및 충돌 해결

**문제**: 여러 rule이 동시에 trigger되면?

**해결책**: Priority queue + conflict resolution

```python
class RuleEngine:
    def __init__(self, rules):
        # Priority 순으로 정렬 (높을수록 먼저)
        self.rules = sorted(rules, key=lambda r: r.priority, reverse=True)
    
    def evaluate(self, context, action):
        """모든 rule 평가 후 enforcement 실행"""
        violations = []
        
        for rule in self.rules:
            if rule.trigger_matches(action):
                if rule.check_predicates(context, action):
                    violations.append(rule)
        
        if not violations:
            return action
        
        # Conflict resolution
        if len(violations) == 1:
            return violations[0].enforce(context, action)
        else:
            return self._resolve_conflicts(violations, context, action)
    
    def _resolve_conflicts(self, rules, context, action):
        """충돌 해결 전략"""
        # 전략 1: 가장 엄격한 enforcement 선택
        if any(r.enforcement == "stop" for r in rules):
            stop_rule = next(r for r in rules if r.enforcement == "stop")
            return stop_rule.enforce(context, action)
        
        # 전략 2: 모든 enforcement 순차 실행
        for rule in rules:
            action = rule.enforce(context, action)
        
        return action
```

### 6. Testing 및 Validation

**Rule 테스트 프레임워크**:

```python
class RuleTester:
    """Rule의 correctness 검증"""
    
    def __init__(self, rule):
        self.rule = rule
    
    def test_should_trigger(self, context, action):
        """Rule이 trigger되어야 하는 케이스"""
        assert self.rule.trigger_matches(action), "Rule did not trigger"
        assert self.rule.check_predicates(context, action), "Predicate failed"
    
    def test_should_not_trigger(self, context, action):
        """Rule이 trigger되지 않아야 하는 케이스"""
        result = (
            not self.rule.trigger_matches(action) or
            not self.rule.check_predicates(context, action)
        )
        assert result, "Rule triggered incorrectly"

# 사용 예시
tester = RuleTester(rule=inspect_transfer_rule)

# Positive case
tester.test_should_trigger(
    context={"family_members": ["Bob"]},
    action=AgentAction(tool="Transfer", input={"to": "Alice", "amount": 100})
)

# Negative case
tester.test_should_not_trigger(
    context={"family_members": ["Bob"]},
    action=AgentAction(tool="Transfer", input={"to": "Bob", "amount": 100})
)
```

## 나의 생각

### 1. Hook → Rule Check → Enforcement의 우아함

**3단계 파이프라인의 명확한 책임 분리**가 이 프레임워크의 핵심 강점입니다. 각 단계가 독립적으로 테스트 가능하고, 확장 가능하며, 교체 가능합니다:

- **Hook**: Framework-specific integration point (LangChain, AutoGen, Apollo)
- **Rule Check**: Domain-agnostic logic (predicates는 순수 함수)
- **Enforcement**: Pluggable strategies (Stop, Inspect, Invoke, Self-examine)

이 구조는 **SOLID 원칙**을 잘 따릅니다:
- **Single Responsibility**: 각 단계가 하나의 책임만 가짐
- **Open/Closed**: 새로운 predicate/enforcement 추가 시 기존 코드 수정 불필요
- **Dependency Inversion**: Hook은 추상 interface에 의존, 구체적 rule 구현에 의존하지 않음

### 2. DSL 설계의 Trade-off

**장점**:
- **Human-readable**: 비개발자도 이해 가능한 선언적 문법
- **Version control friendly**: Rule을 Git으로 관리, diff 확인 용이
- **Auditable**: 규제 산업(금융, 의료)에서 compliance 증명 쉬움

**단점**:
- **표현력 제한**: 복잡한 로직은 Python predicate 함수로 분리 필요
- **Learning curve**: 새로운 언어 학습 필요 (하지만 간단함)
- **Parser 오버헤드**: 1.42ms는 무시 가능하지만 존재

**대안**:
- **Pure Python DSL**: Fluent interface로 구현 (예: SQLAlchemy, Pydantic)
  ```python
  Rule("inspect_transfer") \
      .trigger("Transfer") \
      .check(lambda ctx, act: not is_to_family_member(act)) \
      .enforce("user_inspection")
  ```
- **Declarative YAML/JSON**:
  ```yaml
  rules:
    - id: inspect_transfer
      trigger: Transfer
      check:
        - predicate: is_to_family_member
          negate: true
      enforce:
        - user_inspection
  ```

AgentSpec의 DSL은 **읽기 쉬움**과 **표현력** 사이 좋은 균형점을 찾았습니다.

### 3. Predicate 구현의 한계와 개선 방향

**현재 한계**:
- **정적 분석 한계**: Code Agent의 `is_destructive_cmd`는 단순 문자열 검색
  ```python
  # 우회 가능
  cmd = "r" + "m"  # "rm" 문자열 검색 우회
  os.system(cmd + " -rf /")
  ```

**개선 방안**:
- **AST 기반 분석**:
  ```python
  import ast
  
  def is_destructive_cmd_ast(state, action):
      code = action.tool_input.get("code", "")
      try:
          tree = ast.parse(code)
          for node in ast.walk(tree):
              if isinstance(node, ast.Call):
                  if isinstance(node.func, ast.Attribute):
                      if node.func.attr in ["remove", "rmdir", "unlink"]:
                          return True
      except SyntaxError:
          return False  # 파싱 실패 시 안전하게 통과
      return False
  ```

- **Symbolic Execution**: Z3 같은 SMT solver로 코드 동작 추론
- **Taint Analysis**: 민감 데이터 흐름 추적

### 4. Framework-Agnostic 설계의 실용성

**통합 난이도**:
- **LangChain**: `iter_next_step` hook → 쉬움 (Python, 명확한 hook point)
- **AutoGen**: `handle_function_call` hook → 중간 (Python, 다소 복잡한 구조)
- **Apollo**: C++ codebase → 어려움 (언어 barrier, 기존 시스템 복잡도)

**범용 Adapter 패턴**:

```python
class AgentAdapter(ABC):
    """각 프레임워크용 adapter"""
    
    @abstractmethod
    def install_hooks(self, rules):
        """Framework에 hook 설치"""
        pass
    
    @abstractmethod
    def extract_context(self, *args):
        """Framework-specific context를 표준 형식으로 변환"""
        pass

class LangChainAdapter(AgentAdapter):
    def install_hooks(self, rules):
        # LangChain의 AgentExecutor._take_next_step 패치
        original_func = AgentExecutor._take_next_step
        
        def patched_func(self, *args, **kwargs):
            context = self.extract_context(*args)
            # ... rule evaluation
        
        AgentExecutor._take_next_step = patched_func

class AutoGenAdapter(AgentAdapter):
    def install_hooks(self, rules):
        # AutoGen의 ConversableAgent.generate_reply 패치
        # ...
```

### 5. LLM 자동 Rule 생성의 가능성과 한계

**Precision 95.56% vs Recall 70.96% (Embodied Agent)**:
- **높은 Precision**: LLM이 생성한 rule은 대부분 정확 (False positive 적음)
- **낮은 Recall**: 일부 위험 상황 놓침 (False negative 많음)

**실패 사례 분석**:
1. **과적합**: 예시에만 맞춰진 rule
   - 예시: `/etc/passwd` 삭제 방지
   - 생성 rule: `/etc/passwd` 경로만 체크
   - 실패: `/etc/shadow` 삭제는 감지 못함

2. **복잡한 속성 인식 실패**:
   - 요구사항: "가열 불가 물체를 스토브에 올리지 마라"
   - 실패: "와인이 담긴 주전자"가 가열 불가임을 인식 못함

**개선 전략**:
- **Few-shot → Chain-of-Thought**:
  ```
  Requirement: Do not heat flammable liquids
  
  Reasoning:
  1. Identify flammable liquids: alcohol, gasoline, acetone
  2. Identify heating actions: place on stove, use microwave
  3. Detect object state: is container filled with liquid?
  4. Check liquid type: is it in flammable list?
  
  Generated predicate:
  def check_flammable_heating(state, action):
      if action.tool == "place" and action.target == "stove":
          obj = state.objects[action.object_id]
          if obj.filled_with in ["wine", "alcohol", "gasoline"]:
              return True
      return False
  ```

- **Iterative Refinement**: LLM이 생성한 rule → 테스트 → 실패 케이스 피드백 → rule 수정

### 6. 실무 적용 시 고려사항

**Rule 관리 복잡도**:
- **Rule 수 증가**: 25개 rule (Code), 12개 rule (Embodied), 6개 rule (AV)
- **충돌 가능성**: 여러 rule이 동시에 trigger되면?
- **Maintainability**: Rule이 100개 넘으면 관리 어려움

**해결책**:
- **Rule Grouping**: Domain/Priority/Risk level로 그룹화
- **Rule Testing Framework**: 각 rule의 correctness 자동 검증
- **Rule Analytics**: 어떤 rule이 자주 trigger되는지 모니터링

**Performance 고려**:
- **Predicate 최적화**: 복잡한 AST 분석은 캐싱
- **Lazy Evaluation**: 모든 rule을 매번 평가하지 말고, trigger 이벤트 발생 시만
- **Parallel Evaluation**: 독립적인 predicate는 병렬 실행

**User Experience**:
- **User Inspection의 피로도**: 너무 자주 물어보면 사용자가 무조건 "Yes" 클릭
- **해결책**: 
  - 신뢰도 점수 추가 (Low risk → Auto-approve, High risk → User inspection)
  - Batch approval (유사한 여러 액션을 한 번에 승인)

### 7. 환각 검출 vs 안전성 Enforcement

**AgentSpec은 환각 검출이 아닌 안전성 Enforcement에 초점**:
- **환각**: LLM이 사실과 다른 정보 생성 (정확성 문제)
- **안전**: LLM Agent가 위험한 행동 수행 (행동 문제)

**그러나 원리는 공유**:
- **Rule 기반 검증**: Predicate로 조건 명시
- **Runtime Intervention**: 문제 발견 시 즉시 개입
- **Self-examination**: LLM에게 재고 기회 제공

**환각 검출로 확장**:

```python
# Factuality rule
rule @check_factuality
trigger agent_finish
check
  contains_factual_claim
  !verified_by_knowledge_base
enforce
  llm_self_examine("Please verify the factual claim against the knowledge base")
end

# Predicate 구현
def contains_factual_claim(state, action):
    """LLM 응답에 사실적 주장 포함 여부"""
    response = action.return_values.get("output", "")
    
    # Named entity + 숫자/날짜 패턴 → 사실적 주장 가능성
    entities = extract_entities(response)
    numbers = re.findall(r'\d+', response)
    
    return len(entities) > 0 or len(numbers) > 0

def verified_by_knowledge_base(state, action):
    """Knowledge base에서 검증 가능한지"""
    response = action.return_values.get("output", "")
    claims = extract_claims(response)
    
    for claim in claims:
        if not knowledge_base.verify(claim):
            return False
    
    return True
```

이 프레임워크는 **"hook → rule check → enforcement" 구조의 SDK 설계 레퍼런스**로 매우 가치 있습니다. 특히 **DSL 설계**, **Hook point 선정**, **Enforcement strategy 패턴**, **Framework-agnostic adapter**는 다양한 런타임 제약 시스템에 적용 가능한 범용 패턴입니다.
