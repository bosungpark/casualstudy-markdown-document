# Consistency in Non-Transactional Distributed Storage Systems

## 출처
- **링크**: https://dl.acm.org/doi/10.1145/2926965
- **저자**: Paolo Viotti (EURECOM), Marko Vukolić (IBM Research - Zurich)
- **게재**: ACM Computing Surveys, Vol. 49, No. 1, 2016
- **PDF**: http://vukolic.com/consistency-survey.pdf

---

## AI 요약

### 1. 논문의 핵심 목적과 배경

분산 시스템에서 "일관성(consistency)"의 의미가 시대에 따라 변화해왔다. 80년대에는 "일관성"이 주로 strong consistency(나중에 linearizability로 정의됨)를 의미했으나, 최근 고가용성·확장성 시스템의 등장으로 일관성 개념이 약화되고 모호해졌다. 이 논문은 40년간의 분산 시스템 연구에서 등장한 50개 이상의 일관성 모델을 체계적으로 정리한다.

### 2. 시스템 모델과 형식적 프레임워크

논문은 Burckhardt의 수학적 프레임워크를 확장하여 일관성 시맨틱스를 1차 논리 술어로 정의한다.

**핵심 개념들:**

- **Operation**: `(proc, type, obj, ival, oval, stime, rtime)` 튜플로 표현
- **History (H)**: 실행 중 발생한 모든 연산들의 집합
- **Abstract Execution (A)**: History에 `vis`(visibility)와 `ar`(arbitration) 관계를 추가
  - `vis`: 쓰기 연산의 전파를 나타내는 비순환 관계
  - `ar`: 충돌 해결을 위한 전체 순서

**주요 관계(Relations):**
- `rb` (returns-before): 실시간 선행 관계
- `ss` (same-session): 동일 프로세스의 연산
- `so` (session order): `rb ∩ ss`
- `hb` (happens-before): `(so ∪ vis)+`

### 3. 일관성 모델 상세 분석

#### 3.1 Strong Consistency Family

**Linearizability** (가장 강력한 모델)
```
LINEARIZABILITY = SINGLEORDER ∧ REALTIME ∧ RVAL(F)
```
- 각 연산이 호출과 응답 사이의 특정 시점에 즉각적으로 적용되는 것처럼 보여야 한다.
- **Locality property**: linearizable 객체들의 조합도 linearizable → 모듈러 설계 가능
- **CAP 정리와의 관계**: 네트워크 파티션 상황에서 가용성 또는 linearizability 중 하나를 희생해야 함

**Safe/Regular/Atomic Registers** (Lamport, 1986)
- Figure 2 예시: 레지스터가 0으로 초기화되고, 동시에 WRITE(1)과 WRITE(2)가 발생할 때
  - Atomic: x는 0 또는 1만 가능
  - Regular: x는 0, 1, 또는 2 가능
  - Safe: x는 어떤 값이든 가능

#### 3.2 Eventual/Weak Consistency

**Eventual Consistency**
```
EVENTUALCONSISTENCY = EVENTUALVISIBILITY ∧ NOCIRCULARCAUSALITY ∧ RVAL(F)
```
- 추가 업데이트가 없으면 복제본들이 결국 동일한 복사본으로 수렴한다.
- **한계**: 프로그래머가 일시적 anomaly를 직접 처리해야 함

**Strong Eventual Consistency** (Shapiro et al., 2011)
- Eventual consistency + Strong convergence
- 동일한 쓰기 연산을 적용한 모든 정확한 복제본은 동일한 상태를 가진다.

**Quiescent Consistency**
- 객체가 업데이트를 멈추면(quiescent) 실행이 sequential execution과 동등
- 시스템 전체의 quiescence 기간이 나타나지 않으면 사실상 아무런 보장도 하지 않는다.

#### 3.3 PRAM and Sequential Consistency

**PRAM (Pipeline RAM / FIFO)**
```
PRAM ≜ so ⊆ vis
```
- 모든 프로세스가 특정 프로세스가 발행한 쓰기 연산을 해당 프로세스가 호출한 순서대로 본다.
- 다른 프로세스의 쓰기는 다른 순서로 볼 수 있음
- **증명된 관계**: PRAM = Read-your-writes ∧ Monotonic reads ∧ Monotonic writes

**Sequential Consistency**
```
SEQUENTIALCONSISTENCY = SINGLEORDER ∧ PRAM ∧ RVAL(F)
```
- 모든 연산이 모든 복제본에서 동일한 순서로 직렬화되고, 각 프로세스가 결정한 연산 순서가 보존된다.
- Linearizability와 달리 세션 간 실시간 순서를 요구하지 않음

**Linearizability vs Sequential Consistency 예시** (Figure 3):
```
PA: W1 -- W2 -- W3 -- W5 -- W7
PB: -- W4 -- W6 -- W8

PRAM 허용: 
  SPA: W1 W2 W3 W5 W4 W7 W6 W8
  SPB: W1 W3 W5 W7 W2 W4 W6 W8

Sequential: SPA = SPB (둘 중 하나)

Linearizable: W1 W3 W2 W4 W5 W6 W8 W7 (유일)
```

#### 3.4 Session Guarantees

| 보장 | 정의 | 형식화 |
|------|------|--------|
| **Monotonic Reads** | 연속 읽기가 비감소 쓰기 집합 반영 | `(vis; so\|rd→rd) ⊆ vis` |
| **Read-your-writes** | 자신의 이전 쓰기를 항상 볼 수 있음 | `so\|wr→rd ⊆ vis` |
| **Monotonic Writes** | 세션 내 쓰기 순서 보존 | `so\|wr→wr ⊆ ar` |
| **Writes-follow-reads** | 읽은 값에 의존하는 쓰기 순서 보존 | `(vis; so\|rd→wr) ⊆ ar` |

#### 3.5 Causal Models

**Causal Consistency**
```
CAUSALCONSISTENCY = CAUSALVISIBILITY ∧ CAUSALARBITRATION ∧ RVAL(F)
where:
  CAUSALVISIBILITY ≜ hb ⊆ vis
  CAUSALARBITRATION ≜ hb ⊆ ar
```

- 인과적으로 관련된 연산은 모든 프로세스가 동일한 순서로 보아야 하지만, 인과적으로 무관한(concurrent) 연산은 다른 순서로 볼 수 있다.

**Causal+ Consistency** (Lloyd et al., 2011)
- Causal + Strong convergence (충돌 해결의 일관성)
- 인과적으로 동시인 쓰기 연산이 충돌을 생성할 수 있는데, 이를 commutative/associative 함수로 동일하게 처리

**Real-time Causal Consistency**
- Causal + 실시간 제약
- 인과적으로 동시이면서 실시간으로 겹치지 않는 쓰기는 실시간 순서대로 적용

#### 3.6 Staleness-based Models

**시간 기반 (Delta/Timed/Bounded Staleness)**
```
TIMEDVISIBILITY(Δ) ≜ ∀e ∈ E|wr, ∀e' ∈ E:
  op(e).rtime = t ∧ op(e').stime = t + Δ ⇒ e →vis e'
```
- 쓰기가 최대 Δ 시간 후에 모든 프로세스에게 가시

**버전 기반 (K-atomicity/K-regular/K-safe)**
```
K-LINEARIZABLE(K) = SINGLEORDER ∧ REALTIMEWW ∧ K-REALTIMEREADS(K) ∧ RVAL(F)
```
- 읽기가 최근 K개 값 중 하나를 반환 가능

**Prefix/Timeline Consistency**
- 읽기가 순서화된 쓰기 시퀀스의 프리픽스를 봄 (최신이 아닐 수 있음)
- 순서에 대한 제약이지 최신성에 대한 제약이 아님

#### 3.7 Fork-based Models (Byzantine Fault Tolerance)

신뢰할 수 없는 스토리지와의 상호작용에서 필요한 모델들:

**Fork-linearizability**
```
FORKLINEARIZABILITY = PRAM ∧ REALTIME ∧ NOJOIN ∧ RVAL(F)
```
- 스토리지가 두 프로세스의 히스토리를 단 하나의 연산에서라도 다르게 만들면, 서버가 결함으로 노출되지 않는 한 서로의 쓰기를 다시 관찰할 수 없다.

**Fork-sequential, Fork*, Weak fork-linearizability** 등 다양한 변형 존재

#### 3.8 Tunable/Composite Semantics

**Hybrid Consistency** (Attiya & Friedman, 1992)
- Strong 연산: Sequential consistency로 순서화
- Weak 연산: Eventually visible (eventual consistency처럼)

**RedBlue Consistency** (Li et al., 2012)
- Blue 연산: 로컬 실행 후 eventually consistent하게 복제
- Red 연산: 동기적 조정으로 직렬화

**Conit (Yu & Vahdat, 2002)**
- 3차원 일관성 벡터: [staleness, order error, numerical error]
- Linearizable 실행으로부터의 편차를 정량화

#### 3.9 Per-object Semantics

**Coherence / Cache Consistency**
- 특정 메모리 위치에 쓴 내용이 모든 프로세서에게 어떤 sequential 순서로 가시
- 객체별로 전역 순서 보장 (per-record timeline consistency)

**Processor Consistency**
```
PROCESSORCONSISTENCY = PEROBJECTSINGLEORDER ∧ PRAM ∧ RVAL(F)
```

### 4. 일관성 모델 계층 구조 (Figure 1 요약)

```
                    Linearizability
                          ↓
              ┌───────────┴───────────┐
        Sequential              Real-time causal
              ↓                       ↓
           PRAM ←──────────────── Causal+ 
              ↓                       ↓
    ┌─────────┴─────────┐         Causal
    │                   │             ↓
Monotonic            Monotonic   Session guarantees
  Reads               Writes     (RYW, MR, MW, WFR)
    │                   │             │
    └─────────┬─────────┘             │
              ↓                       │
         Eventual ←───────────────────┘
              ↓
            Weak
```

**화살표 의미**: A → B는 "B를 만족하는 모든 실행이 A도 만족"

### 5. 실용적 시스템 매핑

| 시스템 | 일관성 모델 |
|--------|------------|
| Google Spanner | Linearizability (TrueTime) |
| DynamoDB | Eventual / Strong (선택) |
| Cassandra | Eventual / Tunable |
| COPS | Causal+ |
| Yahoo PNUTS | Timeline (per-record) |
| Windows Azure Storage | Strong consistency |
| Facebook TAO | Eventual + Read-your-writes |

---

## 내가 얻은 인사이트

### 설계 의사결정을 위한 실용적 가이드

1. **CAP 트레이드오프의 구체화**: 단순히 "CP vs AP"가 아니라, 50개 이상의 일관성 모델이 그 사이 스펙트럼에 존재. 시스템 요구사항에 맞는 정확한 지점 선택 가능.

2. **Session Guarantees의 조합 가능성**: Read-your-writes, Monotonic reads/writes, Writes-follow-reads를 조합하면 PRAM과 동등. 필요한 보장만 선택적으로 구현하여 성능 최적화 가능.

3. **Causal Consistency가 "sweet spot"**: 
   - Linearizability보다 저렴하게 구현 가능
   - Eventual보다 프로그래머 친화적
   - Geo-replicated 시스템에서 특히 유용
   - COPS, ChainReaction 등에서 실증

4. **Staleness 기반 모델의 SLA 활용**: PBS(Probabilistically Bounded Staleness)로 "99%의 읽기가 10초 내 최신 데이터 반환" 같은 확률적 보장 제공 가능.

5. **Per-object vs Global 순서화**: 객체별 순서화만으로 충분한 경우 sharding/partitioning 활용하여 성능 향상 가능.
