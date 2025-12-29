# Raft: In Search of an Understandable Consensus Algorithm

## 출처
- **논문**: In Search of an Understandable Consensus Algorithm (Extended Version)
- **저자**: Diego Ongaro, John Ousterhout (Stanford University)
- **발표**: USENIX ATC 2014 (Best Paper Award 수상)
- **링크**: https://raft.github.io/raft.pdf
- **시각화**: https://raft.github.io/ (브라우저에서 Raft 동작 확인 가능)

---

## AI 요약

### 1. Raft란?

Raft는 **분산 시스템에서 합의(Consensus)를 달성하기 위한 알고리즘**입니다. 여러 서버가 동일한 상태를 유지하면서, 일부 서버가 실패해도 시스템이 올바르게 동작하도록 보장합니다.

| 특성 | 설명 |
|-----|------|
| **동등성** | Paxos와 동일한 결과 보장, 동일한 효율성 |
| **차별점** | 이해하기 쉽게 설계됨 (Paxos 대비) |
| **이름 유래** | **R**eliable, **A**nd **F**ault-**T**olerant |
| **한계** | Byzantine Fault Tolerant 아님 (악의적 노드 미지원) |

### 2. 왜 Raft를 만들었나?

#### Paxos의 문제점

> "NSDI 커뮤니티의 더러운 비밀은 기껏해야 5명만이 Paxos의 모든 부분을 진정으로, 완전히 이해한다는 것이다." — NSDI Reviewer

> "Paxos 알고리즘의 설명과 실제 시스템의 요구사항 사이에는 상당한 차이가 있다." — Chubby 개발자

#### Raft의 설계 철학

1. **분해(Decomposition)**: 문제를 독립적인 하위 문제로 분리
2. **상태 공간 축소**: Paxos 대비 비결정성과 불일치 가능성 최소화
3. **Strong Leader**: 데이터가 리더에서 팔로워로만 흐름

### 3. Raft의 핵심 구성요소

Raft는 합의 문제를 **세 가지 독립적인 하위 문제**로 분해합니다:
```
┌─────────────────────────────────────────────────────────┐
│                    Raft Consensus                       │
├──────────────────┬──────────────────┬──────────────────┤
│  Leader Election │  Log Replication │      Safety      │
│   (리더 선출)     │   (로그 복제)     │     (안전성)     │
└──────────────────┴──────────────────┴──────────────────┘
```

---

### 4. 서버 상태 (Server States)
```
                 타임아웃,
                선거 시작
    ┌─────────────────────┐
    │                     ▼
┌───────┐           ┌───────────┐
│Follower│◀─────────│ Candidate │
└───────┘  다른 리더  └───────────┘
    ▲      발견           │
    │                     │ 과반 투표 획득
    │    ┌────────┐       │
    └────│ Leader │◀──────┘
         └────────┘
              │
              └── 더 높은 term 발견 시 Follower로
```

| 상태 | 역할 |
|-----|------|
| **Follower** | 수동적. 리더/후보자의 요청에만 응답. 클라이언트 요청은 리더로 리다이렉트 |
| **Candidate** | 선거 진행 중. 다른 서버에 투표 요청 |
| **Leader** | 모든 클라이언트 요청 처리. 로그 복제 담당. 주기적 하트비트 전송 |

---

### 5. Term (임기)

Raft는 시간을 **term**이라는 논리적 단위로 나눕니다:
```
     Term 1      Term 2      Term 3      Term 4      Term 5
  ┌──────────┐┌──────────┐┌──────────┐┌──────────┐┌──────────┐
  │Election  ││Election  ││Election  ││Election  ││Election  │
  │ ↓        ││ ↓        ││(split    ││ ↓        ││ ↓        │
  │Normal    ││Normal    ││ vote)    ││Normal    ││Normal    │
  │Operation ││Operation ││          ││Operation ││Operation │
  └──────────┘└──────────┘└──────────┘└──────────┘└──────────┘
                          (리더 없음)
```

- 각 term은 **선거로 시작**
- term 번호는 **단조 증가**
- term은 **논리적 시계** 역할 (오래된 정보 감지)
- 서버 간 통신 시 term 교환 → 낮은 term의 서버는 즉시 Follower로 전환

---

### 6. Leader Election (리더 선출)

#### 선거 트리거
- Follower가 **election timeout** (150~300ms, 랜덤) 동안 하트비트 미수신

#### 선거 과정
```
1. Follower → Candidate 전환
2. 현재 term 증가
3. 자기 자신에게 투표
4. 다른 모든 서버에 RequestVote RPC 전송
5. 결과:
   a) 과반 투표 획득 → Leader 됨
   b) 다른 리더의 하트비트 수신 → Follower로 복귀
   c) 타임아웃 (split vote) → 새 선거 시작
```

#### Split Vote 방지
```go
// 각 서버는 독립적으로 랜덤 타임아웃 설정
electionTimeout := 150 + rand.Intn(150) // 150~300ms
```

이 랜덤성이 한 서버가 먼저 깨어나 선거에서 승리할 확률을 높임.

#### 투표 제한 (Election Restriction)

**중요**: 후보자의 로그가 투표자보다 "최신"이어야만 투표 획득 가능
```
"최신" 비교 기준:
1. 마지막 로그 entry의 term이 더 큰 쪽
2. term이 같으면 로그 길이가 더 긴 쪽
```

이 제한이 **커밋된 entry가 새 리더에게 반드시 존재함**을 보장.

---

### 7. Log Replication (로그 복제)

#### 로그 구조
```
Index:   1      2      3      4      5      6
       ┌────┬────┬────┬────┬────┬────┐
Leader │x←3 │y←1 │y←9 │x←2 │x←0 │y←7 │
       │t=1 │t=1 │t=1 │t=2 │t=3 │t=3 │
       └────┴────┴────┴────┴────┴────┘
              committed ↑     uncommitted

각 entry = (command, term, index)
```

#### 복제 과정
```
Client ──request──▶ Leader
                      │
                      ▼
              1. 로그에 entry 추가
                      │
                      ▼
              2. AppendEntries RPC를 모든 Follower에 전송
                      │
                      ▼
              3. 과반 Follower 응답 대기
                      │
                      ▼
              4. entry를 "committed"로 표시
                      │
                      ▼
              5. State machine에 적용
                      │
                      ▼
Client ◀──response── Leader
```

#### Commit 규칙

entry가 **committed** 되려면:
1. **과반 서버에 복제됨**
2. **현재 리더의 term에서 생성된 entry** (또는 그 이전 entry가 현재 term의 entry 이후에 커밋)
```
⚠️ 주의: 이전 term의 entry만으로는 커밋 불가
   → 현재 term의 entry가 커밋되면 그 이전 entry도 자동 커밋
```

#### Log Matching Property
```
두 로그가 같은 index, 같은 term의 entry를 가지면:
  1. 그 entry는 동일한 command를 저장
  2. 그 index 이전의 모든 entry도 동일
```

#### 로그 불일치 해결

리더 crash 후 로그 불일치 발생 가능:
```
Leader: [1] [2] [3] [4] [5]
Follower A: [1] [2] [3]         (뒤처짐)
Follower B: [1] [2] [3] [4] [X] (충돌)
```

해결 방법:
1. 리더는 각 Follower마다 `nextIndex` 유지
2. AppendEntries 실패 시 `nextIndex` 감소하며 재시도
3. 일치하는 지점 발견 후 Follower 로그 덮어쓰기
```go
// 리더가 새로 선출되면
for each follower {
    nextIndex[follower] = len(leader.log) + 1
    matchIndex[follower] = 0
}
```

---

### 8. Safety Guarantees (안전성 보장)

Raft가 보장하는 5가지 속성:

| 속성 | 설명 |
|-----|------|
| **Election Safety** | 한 term에 최대 한 명의 리더만 선출 |
| **Leader Append-Only** | 리더는 자신의 로그를 덮어쓰거나 삭제하지 않음 |
| **Log Matching** | 같은 index, term → 같은 command, 동일한 이전 로그 |
| **Leader Completeness** | 커밋된 entry는 이후 모든 리더의 로그에 존재 |
| **State Machine Safety** | 한 서버가 특정 index에 command를 적용하면, 다른 서버도 같은 index에 같은 command 적용 |

---

### 9. 추가 기능

#### Cluster Membership Changes (동적 구성 변경)
```
문제: 구성 변경 중 두 개의 과반이 존재할 수 있음

해결: Joint Consensus
  1. C_old,new (이전+새 구성 모두의 과반 필요)
  2. C_new (새 구성만)
  
안전성: 전환 중 어느 시점에서도 두 리더 불가능
```

#### Log Compaction (로그 압축)

시간이 지나면 로그가 무한히 커지므로 **스냅샷** 사용:
```
Before:
[1] [2] [3] [4] [5] [6] [7] [8] [9] [10]

After Snapshot:
┌─────────────────┐
│ Snapshot        │ [8] [9] [10]
│ (state at idx 7)│
└─────────────────┘
```

---

### 10. RPC 정리

Raft는 **두 가지 기본 RPC**만 사용:

#### RequestVote RPC (후보자 → 모든 서버)
```
Arguments:
  term         - 후보자의 term
  candidateId  - 투표 요청 후보자
  lastLogIndex - 후보자의 마지막 로그 index
  lastLogTerm  - 후보자의 마지막 로그 term

Results:
  term         - 현재 term (후보자 업데이트용)
  voteGranted  - 투표 여부
```

#### AppendEntries RPC (리더 → Follower)
```
Arguments:
  term         - 리더의 term
  leaderId     - Follower가 클라이언트 리다이렉트용
  prevLogIndex - 새 entry 직전 로그 index
  prevLogTerm  - prevLogIndex entry의 term
  entries[]    - 저장할 로그 entry들 (하트비트는 비어있음)
  leaderCommit - 리더의 commitIndex

Results:
  term         - 현재 term
  success      - prevLog 일치 여부
```

---

### 11. Paxos vs Raft 비교

| 항목 | Paxos | Raft |
|-----|-------|------|
| **발표** | 1989 (Lamport) | 2014 (Ongaro, Ousterhout) |
| **이해 난이도** | 매우 어려움 | 상대적으로 쉬움 |
| **리더십** | Weak (다수 리더 가능) | Strong (단일 리더) |
| **데이터 흐름** | 양방향 | 리더 → 팔로워 단방향 |
| **로그 순서** | Out-of-order 허용 | 순차적만 허용 |
| **실무 적용** | 이론적 기반, 구현 어려움 | 실용적, 구현 상대적 용이 |
| **RPC 명명** | phase1a/1b, phase2a/2b | RequestVote, AppendEntries |

#### 학생 연구 결과

- 43명의 학생 대상 실험
- **33명이 Raft를 Paxos보다 더 잘 이해**
- Raft 퀴즈 점수가 평균 4.9점 높음

---

### 12. 실제 사용 사례

| 시스템 | 설명 |
|-------|------|
| **etcd** | Kubernetes의 핵심 Key-Value 저장소 |
| **Consul** | HashiCorp의 서비스 메시 솔루션 |
| **CockroachDB** | 분산 SQL 데이터베이스 |
| **TiKV** | 분산 Key-Value 저장소 (TiDB의 스토리지 엔진) |
| **RabbitMQ** | Quorum Queues에서 사용 |
| **ClickHouse** | Keeper에서 사용 |

---

### 13. Raft의 한계

1. **Single Point of Failure**: 리더가 병목 및 단일 실패점
2. **Byzantine Fault 미지원**: 악의적 노드 가정 안 함
3. **Membership Change 검증 부족**: 공식 safety proof 미완성
4. **확장성 제한**: 서버 수 증가 시 성능 저하

---

## 내가 얻은 인사이트

### 설계 철학 관점

1. **"이해 가능성"도 핵심 설계 목표가 될 수 있다**
   - Paxos가 30년 가까이 "이론적으로 옳지만 실무에서 구현하기 어렵다"는 평가를 받음
   - Raft는 동일한 문제를 더 이해하기 쉽게 재구성함으로써 실무 채택을 이끌어냄
   - 알고리즘의 정확성뿐 아니라 **표현 방식**도 성공에 중요한 요소

2. **분해(Decomposition)의 힘**
   - Leader Election, Log Replication, Safety를 독립적으로 이해 가능
   - 복잡한 문제를 작은 단위로 쪼개면 각각을 검증하고 테스트하기 쉬워짐

3. **Strong Leader 패턴의 Trade-off**
   - 장점: 구현 단순화, 데이터 흐름 명확
   - 단점: 리더가 병목, 단일 실패점
   - 대부분의 실무 시스템에서는 이 trade-off가 수용 가능

### 실무 적용 관점

4. **과반(Majority) 기반 시스템 설계**
   - N개 서버 중 `(N-1)/2`개 실패까지 허용
   - 3대: 1대 실패 허용
   - 5대: 2대 실패 허용
   - **홀수 권장** (짝수는 자원 낭비)

5. **Term과 논리적 시계**
   - 분산 시스템에서 물리적 시간 동기화는 어려움
   - 논리적 시간(term, epoch, generation 등)으로 **인과 관계** 추적
   - "이전 리더의 오래된 메시지"를 안전하게 무시 가능

6. **랜덤화로 경쟁 조건 해결**
   - Election timeout의 랜덤화가 split vote 방지
   - 완벽한 동기화 대신 **확률적 해결**이 더 실용적일 수 있음

### 시스템 설계 패턴

7. **Commit의 두 단계**
```
   Replicated (복제됨) ≠ Committed (커밋됨)
   Committed (커밋됨) ≠ Applied (적용됨)
```
   - 복제만으로는 안전하지 않음
   - 과반 복제 + 현재 term 조건 충족 → Committed
   - Committed 후에만 State Machine에 적용

8. **"No-op" entry 패턴**
   - 새 리더는 즉시 자신의 term으로 빈 entry 추가
   - 이전 term의 uncommitted entry들을 안전하게 커밋하는 트릭
   - 실무에서 자주 사용되는 패턴

### 운영 관점

9. **Kubernetes/etcd 사용 시 고려사항**
   - etcd 클러스터는 보통 3~5대로 구성
   - 네트워크 파티션 시 과반이 없는 쪽은 읽기만 가능
   - 리더 선출 시간(election timeout)이 시스템 복구 시간에 영향

10. **디버깅 포인트**
    - term 불일치: 네트워크 파티션 또는 오래된 노드 복귀
    - 로그 불일치: 리더 crash 후 복구 과정 중 발생 가능
    - Split brain: 네트워크 파티션 + 잘못된 구성

### 학습 자료 추천

- **시각화**: https://raft.github.io/ (인터랙티브)
- **The Secret Lives of Data**: https://thesecretlivesofdata.com/raft/ (가이드 형식)
- **Diego Ongaro PhD 논문**: 더 상세한 내용과 TLA+ 명세 포함