# The Missing Layer of AGI: From Pattern Alchemy to Coordination Physics

## 출처
- **논문**: The Missing Layer of AGI: From Pattern Alchemy to Coordination Physics
- **저자**: Edward Y. Chang
- **게재**: arXiv:2512.05765 [cs.AI] (2025년 12월)
- **원문**: https://arxiv.org/abs/2512.05765

---

## AI 요약

### 핵심 주장: LLM은 AGI의 막다른 길이 아니다

**비판자들의 주장**:
```
"LLM은 단순한 패턴 매칭 기계일 뿐이다"
"구조적으로 추론/계획 능력이 불가능하다"
"LLM은 AGI로 가는 막다른 길(dead end)이다"
```

**저자의 반박**:
```
잘못된 진단이다. 
문제는 바다(Ocean)가 아니라 그물(Net)이다.
패턴 저장소(Pattern Repository) = 필요한 System-1 기반
부족한 것 = System-2 조정 계층(Coordination Layer)
```

### 핵심 비유: 바다 vs 그물

**바다 (Ocean) = LLM의 패턴 저장소**:
```
엄청난 양의 패턴/지식 저장
"고양이는 귀엽다"
"미적분은 변화율을 다룬다"
"Paris is the capital of France"
→ 수십억 개의 패턴
```

**그물 (Net) = 조정 계층 (부재)**:
```
어떤 패턴을 꺼낼까? (Selection)
어떤 제약을 걸까? (Constraint)
어떻게 묶을까? (Binding)
→ 이 계층이 없다!
```

**비유 확장**:
```
바다에 물고기(패턴)는 많다
하지만 그물이 없으면 잡을 수 없다
→ LLM 비판: "바다에 물고기 없다" (❌ 잘못된 진단)
→ 진짜 문제: "그물이 없다" (✓ 올바른 진단)
```

### System-1 vs System-2 (Kahneman)

**System-1 (Fast Thinking)**:
```
직관적, 자동적, 빠름
"2 + 2 = ?"
"파리는 프랑스의 수도"
→ 패턴 매칭
→ LLM이 잘하는 것
```

**System-2 (Slow Thinking)**:
```
논리적, 의도적, 느림
"17 × 24 = ?"
"이 계획의 결함은?"
→ 추론/계획
→ LLM이 못하는 것
```

**저자 주장**:
```
System-1 (패턴 저장소) = LLM이 이미 가짐 ✓
System-2 (조정 계층) = 누락됨 ✗
→ System-2를 추가하면 AGI 가능!
```

### UCCT (Universal Coordination via Constraint Theory)

**3가지 핵심 변수**:

**1. ρ_d (Effective Support, 유효 지원도)**:
```
얼마나 많은 패턴이 목표를 지원하는가?

예시: "파리 여행 계획"
높은 ρ_d: 패턴 100개 (항공, 숙박, 관광...)
낮은 ρ_d: 패턴 5개 (정보 부족)
→ 높을수록 좋은 추론
```

**2. d_r (Representational Mismatch, 표현 불일치)**:
```
패턴과 목표 간 거리

예시: "양자역학으로 빵 굽기"
d_r = 높음 (관련 없음)

예시: "오븐 온도로 빵 굽기"
d_r = 낮음 (관련 높음)
→ 낮을수록 좋은 추론
```

**3. γ log k (Adaptive Anchoring Budget, 앵커링 예산)**:
```
얼마나 많은 제약을 걸 수 있는가?

k = 고려할 패턴 수
γ = 제약 강도
→ 계산 자원/시간의 한계
```

### Phase Transition (상전이) 비유

**물 → 얼음 전환처럼, 패턴 매칭 → 추론 전환**:

```
저온 (낮은 γ, 낮은 ρ_d):
물 상태 = 패턴이 자유롭게 흐름
→ Ungrounded Generation (환각)
→ "고양이는 달에 산다" (패턴 매칭만)

고온 (높은 γ, 높은 ρ_d):
얼음 상태 = 패턴이 제약에 고정됨
→ Grounded Reasoning (추론)
→ "달에 산소 없음 → 고양이 못 산다" (제약 적용)
```

**수식**:
```
P(reasoning) ∝ exp(ρ_d / d_r) × γ log k

높은 ρ_d (많은 지원) + 낮은 d_r (낮은 불일치) + 높은 γ (강한 제약)
→ 추론 확률 증가
```

### Ungrounded Generation의 본질

**"환각(Hallucination)"은 버그가 아니라 특징이다**:

```
제약 없는 LLM:
P(output) = Maximum Likelihood Prior
→ "가장 그럴듯한 패턴" 출력
→ 사실 여부 무관

예시:
Q: "에펠탑은 몇 미터?"
A: "324m" (정확) ← 훈련 데이터에 많음

Q: "에펠탑은 런던에 있나?"
A: "Yes" (환각) ← "에펠탑 + 유명 도시" 패턴 매칭
```

**Ungrounded = Unbaited Retrieval**:
```
Bait (미끼) 없이 바다에서 그물 던짐
→ 무작위로 물고기(패턴) 잡힘
→ 목표와 무관한 패턴
```

### MACI: Coordination Stack

**3가지 메커니즘으로 System-2 구현**:

**1. Baiting (미끼 던지기) - Behavior-Modulated Debate**:
```
목표 지향적으로 패턴 선택

예시: "수학 문제 풀기"
Bait: "단계별 풀이", "공식 적용"
→ 관련 패턴만 활성화
→ 무관한 패턴 무시
```

**구현**:
```python
# Debate 메커니즘
agent1: "이 문제는 이차방정식이다"
agent2: "근의 공식을 써야 한다"
agent3: "판별식을 먼저 확인하자"
→ Bait: "이차방정식", "근의 공식"
→ 관련 패턴 검색 집중
```

**2. Filtering (필터링) - Socratic Judging**:
```
소크라테스식 질문으로 패턴 검증

예시: LLM 출력 "고양이는 달에 산다"
Judge: "달에 산소 있나?" → No
Judge: "고양이는 산소 필요한가?" → Yes
Judge: "그럼 고양이가 달에 살 수 있나?" → No
→ 출력 필터링
```

**구현**:
```python
def socratic_judge(claim, knowledge_base):
    questions = generate_critical_questions(claim)
    for q in questions:
        answer = query_knowledge(q)
        if contradicts(answer, claim):
            return REJECT
    return ACCEPT
```

**3. Persistence (지속성) - Transactional Memory**:
```
추론 과정을 트랜잭션처럼 관리

예시: 다단계 추론
Step 1: "x = 2" (COMMIT)
Step 2: "x² = 4" (COMMIT)
Step 3: "x² = 5" (CONFLICT!) → ROLLBACK to Step 2
→ 일관성 유지
```

**구현**:
```python
class ReasoningTransaction:
    def __init__(self):
        self.state = []
        self.checkpoints = []
    
    def commit(self, step):
        if consistent_with(step, self.state):
            self.state.append(step)
            self.checkpoints.append(copy(self.state))
        else:
            self.rollback()
    
    def rollback(self):
        self.state = self.checkpoints[-1]
```

### 실제 적용 예시

**예시 1: 수학 문제**

**Without MACI (Pure LLM)**:
```
Q: "Solve: 2x + 5 = 13"
A: "x = 4" (틀림, 패턴 매칭 오류)
```

**With MACI**:
```
Baiting: "대수 방정식", "항 이동"
Agent1: "양변에서 5를 빼자"
Agent2: "2x = 8"
Agent3: "x = 4"

Filtering (Socratic):
Judge: "2×4 + 5 = 13인가?"
Judge: "8 + 5 = 13" → Yes ✓

Persistence:
COMMIT: x = 4
```

**예시 2: 계획 수립**

**Without MACI**:
```
Q: "파리 여행 3일 계획"
A: "1일차: 에펠탑, 2일차: 콜로세움, 3일차: 자유의 여신상"
(콜로세움=로마, 자유의 여신상=뉴욕 → 환각)
```

**With MACI**:
```
Baiting: "파리 랜드마크", "3일 일정"

Filtering:
Judge: "콜로세움은 파리에 있나?" → No (REJECT)
Judge: "자유의 여신상은 파리에 있나?" → No (REJECT)

Persistence:
COMMIT: 에펠탑 (파리 ✓)
REJECT: 콜로세움 (로마 ✗)
ROLLBACK: 대체안 검색 → 루브르 박물관
```

### 일반적 반대 의견 재해석

**반대 1: "LLM은 추론 못 한다"**

**재해석**:
```
X: LLM에 추론 능력 없음
O: 조정 계층(MACI) 없음
→ MACI 추가하면 추론 가능
```

**반대 2: "LLM은 환각한다"**

**재해석**:
```
X: 결함
O: Unbaited Retrieval (제약 없는 패턴 검색)
→ Baiting/Filtering으로 해결
```

**반대 3: "LLM은 계획 못 한다"**

**재해석**:
```
X: 구조적 한계
O: Persistence 부재 (일관성 관리 없음)
→ Transactional Memory로 해결
```

### 저자의 최종 주장

**AGI로 가는 길**:
```
❌ LLM을 버리고 새 아키텍처 개발
✓ LLM 위에 조정 계층(MACI) 추가

LLM (System-1) + MACI (System-2) = AGI
```

**비유 재방문**:
```
바다(LLM)는 이미 충분히 크다
그물(MACI)을 만들면 된다
→ "바다 vs 그물" 문제 해결
```

---

## 내가 얻은 인사이트

**"패턴 매칭"이 나쁜 게 아니라 "제약 없는 패턴 매칭"이 문제다.** 인간도 System-1은 패턴 매칭이다. "2+2=4"는 추론이 아니라 암기다. 차이는 **System-2가 System-1을 통제**한다는 것. LLM 비판자들은 System-1만 보고 "추론 불가능"이라 하지만, 실제 부족한 건 System-2 조정 계층이다.

**"환각"은 버그가 아니라 기본값(default)이다.** 제약 없이 Maximum Likelihood Prior를 따르면 "가장 그럴듯한 거짓말"을 생성한다. 이건 LLM의 결함이 아니라 **설계대로 작동하는 것**이다. Baiting/Filtering 같은 제약을 걸어야 사실 기반 출력이 나온다. Grounded ≠ 새 모델, Grounded = 제약 추가.

**AGI는 "더 큰 모델"이 아니라 "더 나은 조정"이다.** GPT-5, GPT-6로 파라미터만 늘려도 추론 능력은 선형적으로만 증가한다. 하지만 MACI 같은 조정 계층을 추가하면 **Phase Transition**(상전이)이 일어난다. 패턴 매칭 → 추론으로 질적 변화. "바다를 더 깊게"가 아니라 "그물을 던져라".
