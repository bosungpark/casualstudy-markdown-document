# Quorum은 Linearizability를 보장하지 않는다

## 출처
- **아티클/논문**: Please stop calling databases CP or AP, DDIA Chapter 9
- **저자/출처**: Martin Kleppmann
- **링크**:
  - https://martin.kleppmann.com/2015/05/11/please-stop-calling-databases-cp-or-ap.html
  - https://timilearning.com/posts/ddia/part-two/chapter-9-1/

---

## AI 요약

### 1. 흔한 오해: R + W > N이면 Strong Consistency?

많은 개발자들이 쿼럼 조건 `R + W > N`을 만족하면 강한 일관성(Strong Consistency)이 보장된다고 믿는다. 하지만 이는 **명백한 오해**다.

| 오해 | 현실 |
|------|------|
| R + W > N → 최신 데이터 보장 | 최신 데이터를 **읽을 가능성**이 있을 뿐 |
| 쿼럼 = Linearizability | 쿼럼만으로는 Linearizability 불가능 |
| 노드 겹침 = 일관성 | 동시성 상황에서는 겹쳐도 불일치 발생 |

---

### 2. Linearizability란?

Linearizability(선형성)의 정의:
> 연산 B가 연산 A의 **완료 후**에 시작되었다면,
> B는 A 완료 시점의 상태 또는 **더 최신 상태**를 봐야 한다.

```
시간 →
─────────────────────────────────────────────────
Client A:  ├── write(x=1) ──┤
                              │
Client B:                     ├── read(x) ──┤

Linearizable: B는 반드시 x=1을 읽어야 함
```

---

### 3. 쿼럼이 실패하는 시나리오

#### 시나리오 1: Concurrent Read/Write

```
N=3, W=3, R=2 설정

Writer:     Node A ←── write(x=1)
            Node B ←── write(x=1)  (지연 중)
            Node C ←── write(x=1)  (지연 중)

Reader 1:   Node A, B에서 읽음 → x=1 (A), x=0 (B) → ???
Reader 2:   Node A, C에서 읽음 → x=1 (A), x=0 (C) → ???
```

**문제**: 네트워크 지연으로 쓰기가 모든 노드에 도달하기 전에 읽기 발생
→ 두 Reader가 **다른 값**을 볼 수 있음

#### 시나리오 2: Failed Write (Partial Update)

```
Writer: Node A, B에 성공, Node C에 실패
        → W=2 만족, 성공으로 처리

Reader 1: Node A, C에서 읽음 → 새 값, 구 값
Reader 2: Node B, C에서 읽음 → 새 값, 구 값

문제: 어느 것이 "최신"인지 판단 불가
      Rollback도 없음 → Dirty Read 가능
```

---

### 4. Last-Write-Wins의 함정

| 문제 | 설명 |
|------|------|
| Clock Skew | 노드 간 시계가 다르면 "마지막"의 기준이 불명확 |
| 인과 관계 무시 | 물리적 시간 ≠ 논리적 순서 |
| 데이터 유실 | 동시 쓰기 시 하나가 사라짐 |

```
Node A 시계: 10:00:00.100  →  write(x=1)
Node B 시계: 10:00:00.050  →  write(x=2)  (실제로는 더 늦게 발생)

LWW 결과: x=1 (A의 시계가 더 큼)
실제 의도: x=2가 최종값이어야 함
```

---

### 5. Sloppy Quorum의 추가 문제

Dynamo 스타일 시스템의 Sloppy Quorum:

```
정상 상황:    [A] [B] [C]  ← Preference List
                 ↓
장애 시:      [A] [X] [C] [D]  ← D가 대신 참여 (Hinted Handoff)
```

| 문제점 | 설명 |
|--------|------|
| Strict Majority 아님 | 겹침 보장이 깨질 수 있음 |
| 두 쓰기가 다른 노드셋에 기록 | 동시 쓰기 충돌 감지 불가 |
| Hint 유실 시 데이터 손실 | 대리 노드 장애 시 복구 불가 |

---

### 6. Linearizability를 위해 필요한 것

쿼럼만으로는 부족하고, 다음 중 하나가 필요하다:

| 방법 | 설명 | 예시 |
|------|------|------|
| **동기식 Read Repair** | 읽기 전 모든 복제본 동기화 | 성능 저하 심각 |
| **쓰기 전 읽기** | Writer가 최신 상태 확인 후 쓰기 | Read-Modify-Write |
| **합의 프로토콜** | Raft, Paxos 등 분산 합의 | etcd, ZooKeeper |
| **Single Leader** | 모든 쓰기가 리더 경유 | PostgreSQL, MySQL |

```
Linearizable 시스템 구조:

┌─────────────────────────────────────────────┐
│           Consensus Layer (Raft/Paxos)      │
│    ┌─────────┬─────────┬─────────┐          │
│    │ Leader  │Follower │Follower │          │
│    │  (A)    │  (B)    │  (C)    │          │
│    └────┬────┴─────────┴─────────┘          │
│         │                                    │
│    모든 쓰기는 Leader를 통해 순서화           │
└─────────────────────────────────────────────┘
```

---

### 7. 실제 데이터베이스들의 현실

| 시스템 | Linearizable? | 이유 |
|--------|---------------|------|
| **Cassandra** | ❌ | 쿼럼만 사용, LWT 없이는 불가 |
| **DynamoDB** | ❌ | Eventual Consistency 기본 |
| **MongoDB** | ❌ | 최대 설정에서도 비선형 읽기 가능 |
| **ZooKeeper** | ⚠️ | `sync` 호출 없이는 불가 |
| **etcd** | ✅ | Raft 합의 사용 |
| **CockroachDB** | ✅ | 분산 트랜잭션 + Raft |

---

## 내가 얻은 인사이트

### 이론 vs 현실 관점

1. **수학적 조건 ≠ 실제 보장**
   - `R + W > N`은 "겹칠 가능성"을 수학적으로 보장할 뿐
   - 동시성, 네트워크 지연, 부분 실패는 고려하지 않음
   - 분산 시스템에서 "가능성"과 "보장"은 완전히 다른 개념

2. **CAP 정리의 과잉 단순화**
   - CP/AP 이분법은 실무에서 무의미할 정도로 단순화된 모델
   - 실제로는 Latency, 부분 장애, 트랜잭션 격리 등 훨씬 복잡한 요소들이 존재
   - "우리 시스템은 CP다"라는 말은 거의 항상 틀림

### 설계 관점

1. **일관성 수준의 명시적 선택**
   - Linearizability가 정말 필요한지 먼저 질문해야 함
   - 대부분의 경우 Eventual Consistency나 Causal Consistency로 충분
   - 강한 일관성은 성능과 가용성의 큰 비용을 수반

2. **합의 프로토콜의 필요성**
   - 진정한 Linearizability는 Raft/Paxos 없이 불가능
   - 쿼럼은 "최적화"일 뿐, "보장"을 위한 도구가 아님
