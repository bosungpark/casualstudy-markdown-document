# CAP Theorem (Brewer's Conjecture)

## 출처
- **논문**: "Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services"
- **저자**: Seth Gilbert, Nancy Lynch (MIT)
- **발표**: ACM SIGACT News, Volume 33 Issue 2 (2002)
- **원문 링크**: https://users.ece.cmu.edu/~adrian/731-sp04/readings/GL-cap.pdf
- **확장 논문**: https://groups.csail.mit.edu/tds/papers/Gilbert/Brewer2.pdf (Perspectives on CAP, 2012)

---

## AI 요약

분산 시스템의 **근본적 한계**를 수학적으로 증명한 정리. Eric Brewer가 2000년 PODC에서 추측으로 발표 → 2002년 Gilbert & Lynch가 형식적 증명.

### 핵심 정리

> **분산 시스템에서 다음 세 가지를 동시에 만족하는 것은 불가능하다:**

| 속성 | 정의 |
|------|------|
| **C**onsistency | 모든 읽기는 가장 최근 쓰기 결과를 반환 (Linearizability) |
| **A**vailability | 모든 요청은 (실패하지 않은 노드에서) 응답을 받음 |
| **P**artition Tolerance | 네트워크 분할에도 시스템이 동작 |

### 왜 불가능한가? (증명 스케치)

```
        [Partition]
    G1 ──────✗────── G2
    │                │
   p1               p2
    │                │
 write(v)        read() → ?
```

1. 네트워크가 G1과 G2로 분할됨
2. 클라이언트가 G1의 p1에 `write(v)` 수행
3. 다른 클라이언트가 G2의 p2에서 `read()` 수행
4. p2는 p1과 통신 불가 → **딜레마**:
   - 응답하면 (A) → 최신 값 모름 (C 위반)
   - 응답 안 하면 (C) → 가용성 없음 (A 위반)

**결론**: P가 발생하면 C와 A 중 하나를 포기해야 함

---

### 더 넓은 맥락: Safety vs Liveness

CAP는 분산 컴퓨팅의 일반적 trade-off의 한 예:

| 개념 | 정의 | CAP에서 |
|------|------|---------|
| **Safety** | 나쁜 일이 절대 안 일어남 | Consistency |
| **Liveness** | 좋은 일이 결국 일어남 | Availability |
| **Unreliable** | 시스템에 장애 가능 | Partition |

> "불안정한 분산 시스템에서 Safety와 Liveness를 동시에 보장하는 것은 불가능하다"

**관련 정리**: FLP Impossibility (1985)
- 1개의 crash failure만 있어도 비동기 시스템에서 consensus 불가능

---

### 실용적 선택지

#### 1. CP 시스템 (Consistency + Partition Tolerance)
- Partition 시 **가용성 포기** (에러/타임아웃 반환)
- 예: MongoDB, HBase, Google Chubby

```
Partition 발생 → 일관성 없는 노드 차단 → 일부 요청 실패
```

#### 2. AP 시스템 (Availability + Partition Tolerance)  
- Partition 시 **일관성 포기** (stale data 반환 가능)
- 예: Cassandra, DynamoDB, DNS, CDN

```
Partition 발생 → 모든 노드 계속 응답 → 데이터 불일치 가능
```

#### 3. CA 시스템 (Consistency + Availability)
- **이론상만 존재** - 실제 분산 시스템에서 Partition 불가피
- 단일 노드 DB (PostgreSQL 단독)가 여기에 해당

---

### 현실적 대응 전략

#### 1. Best Effort Availability (CP 접근)
- 강한 일관성 보장, 가용성은 최선을 다함
- 예: **Google Chubby** (분산 락 서비스)
  - Paxos 기반 replicated state machine
  - 데이터센터 내부에서 운영 (partition 드묾)

#### 2. Best Effort Consistency (AP 접근)
- 높은 가용성 보장, 일관성은 최선을 다함
- 예: **Akamai CDN**
  - 전 세계 캐시 서버에서 빠른 응답
  - 콘텐츠 업데이트 전파에 시간 소요

#### 3. 일관성과 가용성 Trade-off 조절
- **Continuous Consistency** (Yu & Vahdat)
- 예: 항공권 예약 시스템
  - 좌석 많을 때: 약한 일관성 OK
  - 좌석 적을 때: 강한 일관성 필요

#### 4. 시스템 분할 (Segmentation)

| 분할 기준 | 예시 |
|-----------|------|
| **Data** | 장바구니 (AP) vs 결제 (CP) |
| **Operation** | 읽기 (AP) vs 쓰기 (CP) |
| **User/Geography** | 지역별 데이터센터 분리 |
| **Hierarchy** | 상위 레벨은 약한 일관성, 하위는 강한 일관성 |

---

### PACELC: CAP 확장 (2010)

```
if (Partition) {
    choose(Availability, Consistency)  // CAP
} else {
    choose(Latency, Consistency)       // 확장
}
```

| 시스템 | Partition 시 | 정상 시 |
|--------|-------------|---------|
| DynamoDB | A (가용성) | L (지연시간) |
| MongoDB | C (일관성) | C (일관성) |
| Cassandra | A (가용성) | L (지연시간) |
| PNUTS | A (가용성) | L (지연시간) |

---

### 데이터베이스 분류

| 타입 | 특징 | 예시 |
|------|------|------|
| **CP** | Partition 시 일부 노드 차단 | MongoDB, Redis, HBase |
| **AP** | Partition 시 stale data 허용 | Cassandra, CouchDB, DynamoDB |
| **CA** | 단일 노드 (분산 아님) | PostgreSQL (단독), MySQL (단독) |

---

### 흔한 오해

❌ **"셋 중 두 개를 고르면 된다"**

✅ 실제로는:
- P(Partition)는 **선택이 아니라 현실** - 네트워크 장애는 발생함
- 따라서 **C vs A 선택**이 핵심
- 심지어 Partition 없어도 비동기 시스템에서는 문제 발생

❌ **"CAP의 C = ACID의 C"**

✅ 다른 개념:
- CAP의 C: **Linearizability** (모든 노드가 같은 데이터)
- ACID의 C: **Consistency** (무결성 제약 만족)

---

### 핵심 인용

> "In a network subject to communication failures, it is impossible for any web service to implement an atomic read/write shared memory that guarantees a response to every request."

> "The CAP Theorem is simply one example of the fundamental fact that you cannot achieve both safety and liveness in an unreliable distributed system."

---

### 관련 논문

| 논문 | 내용 |
|------|------|
| FLP Impossibility (1985) | 1개 장애로도 consensus 불가능 |
| Paxos (1998) | Consensus 알고리즘 |
| Dynamo (2007) | Amazon의 AP 시스템 |
| Spanner (2012) | Google의 globally-distributed CP 시스템 |

---

## 내가 얻은 인사이트
