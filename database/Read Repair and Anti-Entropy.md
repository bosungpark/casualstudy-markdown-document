# Read Repair와 Anti-Entropy: 쿼럼을 보완하는 메커니즘

## 출처
- **아티클/논문**: Anti-Entropy in Distributed Systems, Read Repair and Anti-Entropy
- **저자/출처**: System Design School, The Algorists, InfluxData
- **링크**:
  - https://systemdesignschool.io/blog/anti-entropy
  - https://efficientcodeblog.wordpress.com/2017/12/26/read-repair-and-anti-entropy-two-ways-to-remedy-replication-lag-in-dynamo-style-datastores-leaderless-replication/
  - https://www.influxdata.com/blog/eventual-consistency-anti-entropy/

---

## AI 요약

### 1. 왜 쿼럼만으로는 부족한가?

쿼럼 시스템의 근본적 문제:

```
쓰기 성공 후:
[Node A]: x = 1  ✓
[Node B]: x = 1  ✓
[Node C]: x = 0  (네트워크 지연으로 미반영)

시간이 지나도 C는 스스로 복구되지 않음
→ 영구적 불일치 상태 지속 가능
```

| 쿼럼의 한계 | 보완 메커니즘 |
|-------------|---------------|
| 쓰기 후 복제본 동기화 안 함 | Read Repair |
| 드물게 읽히는 데이터 방치 | Anti-Entropy |
| 장애 복구 후 정합성 검증 없음 | Merkle Tree 비교 |

---

### 2. Read Repair: 읽기 시점 복구

#### 동작 원리

```
Client가 R=2로 읽기 요청:

[Node A]: x = 1, version = 5  ──┐
[Node B]: x = 0, version = 3  ──┼──→ Client
[Node C]: (읽지 않음)           │
                                │
Client: "A가 최신이네"          │
        ↓                       │
        B에 x = 1 쓰기 (repair) │
```

#### 상세 프로세스

```
1. 병렬 읽기
   Client → [A, B, C] 중 R개에 요청

2. 버전 비교
   응답: A(v5), B(v3)
   최신 버전: v5 (A)

3. Stale 노드 감지
   B는 v3 → stale

4. Read Repair 실행
   Client → B: write(x=1, v5)

5. 응답 반환
   Client ← x = 1
```

#### 특징

| 장점 | 단점 |
|------|------|
| 추가 백그라운드 프로세스 불필요 | 읽히지 않는 데이터는 복구 안 됨 |
| 즉시 복구 | 읽기 latency 증가 가능 |
| 자주 읽는 데이터는 항상 최신 | 모든 복제본 읽어야 완전한 repair |

---

### 3. Anti-Entropy: 백그라운드 동기화

#### 동작 원리

```
Anti-Entropy Process (Background):

┌─────────────────────────────────────────────────────┐
│  주기적으로 실행 (예: 1시간마다)                      │
├─────────────────────────────────────────────────────┤
│  1. 각 노드의 데이터 해시 계산                       │
│  2. 노드 간 해시 비교                                │
│  3. 불일치 구간 식별                                 │
│  4. 최신 데이터로 덮어쓰기                           │
└─────────────────────────────────────────────────────┘

[Node A] ←──비교──→ [Node B] ←──비교──→ [Node C]
```

#### Merkle Tree 활용

```
전체 데이터를 해시 트리로 구성:

                    [Root Hash]
                    /          \
            [Hash 1-2]        [Hash 3-4]
            /        \        /        \
        [Hash1]  [Hash2]  [Hash3]  [Hash4]
           │        │        │        │
        [Data1] [Data2]  [Data3] [Data4]

비교 과정:
1. Root Hash 비교 → 다름
2. 하위 노드 비교 → Hash 3-4 다름
3. 더 하위 비교 → Hash3 다름
4. Data3만 동기화

→ 전체 데이터 비교 없이 불일치 구간만 찾음
```

#### Merkle Tree의 효율성

| 비교 방식 | 전송량 | 시간 복잡도 |
|-----------|--------|-------------|
| 전체 데이터 비교 | O(n) | O(n) |
| Merkle Tree | O(log n) | O(log n) |

---

### 4. Read Repair vs Anti-Entropy 비교

| 항목 | Read Repair | Anti-Entropy |
|------|-------------|--------------|
| **트리거** | 클라이언트 읽기 | 백그라운드 스케줄 |
| **타이밍** | 즉시 | 지연 (분~시간) |
| **커버리지** | 읽힌 데이터만 | 전체 데이터 |
| **순서 보장** | 읽기 순서 | 순서 보장 없음 |
| **오버헤드** | 읽기 시 추가 작업 | 백그라운드 리소스 |
| **데이터 신뢰성** | 자주 읽는 데이터에 적합 | 드물게 읽는 데이터 보호 |

---

### 5. 실제 시스템 적용

#### Amazon Dynamo

```
┌─────────────────────────────────────────────┐
│              Dynamo Architecture             │
├─────────────────────────────────────────────┤
│  Read Repair: 읽기마다 버전 비교 & 복구      │
│  Anti-Entropy: Merkle Tree로 주기적 동기화   │
│  Vector Clock: 인과 관계 추적                │
└─────────────────────────────────────────────┘
```

#### Apache Cassandra

| 기능 | 설정 |
|------|------|
| Read Repair | `read_repair_chance` (0.0 ~ 1.0) |
| Anti-Entropy | `nodetool repair` 수동 실행 |
| Merkle Tree | Hash Tree Exchange 프로토콜 |

```cql
-- Cassandra Read Repair 설정
ALTER TABLE users
WITH read_repair_chance = 0.1
AND dclocal_read_repair_chance = 0.1;
```

#### Riak

```
Active + Passive Anti-Entropy 혼합:

Active:  백그라운드에서 능동적 비교
Passive: 데이터 요청 시에만 검증

→ 리소스 사용량과 일관성 사이 균형
```

---

### 6. 한계와 주의사항

#### Read Repair의 한계

```
드물게 읽히는 데이터:

마지막 읽기: 6개월 전
[Node A]: x = 최신값
[Node B]: x = 6개월 전 값
[Node C]: x = 6개월 전 값

→ Anti-Entropy 없이는 영구 불일치
→ 내구성(Durability) 감소
```

#### Anti-Entropy의 한계

| 한계 | 설명 |
|------|------|
| 리소스 집약적 | Merkle Tree 계산, 네트워크 전송 |
| Hot Shard 제외 | 활발히 쓰이는 샤드는 repair 불가 |
| 순서 보장 없음 | 쓰기 순서와 무관하게 동기화 |
| 타이밍 지연 | 주기 사이에 불일치 존재 |

---

## 내가 얻은 인사이트

### 계층적 방어 관점

1. **단일 메커니즘은 없다**
   - 쿼럼: 기본적인 겹침 보장
   - Read Repair: 읽기 경로 복구
   - Anti-Entropy: 전체 데이터 정합성
   - Hinted Handoff: 장애 시 임시 저장

   → 모든 계층이 함께 작동해야 Eventual Consistency 달성

2. **Active vs Passive 트레이드오프**
   - Active Anti-Entropy: 일관성 ↑, 리소스 ↑
   - Passive (Read Repair only): 리소스 ↓, 드문 데이터 방치
   - 워크로드 특성에 따라 선택 필요

### 운영 관점

1. **Read Repair의 숨겨진 비용**
   - 읽기마다 여러 노드 접근 → latency 증가
   - 복구 쓰기 추가 → throughput 감소
   - 확률적 설정(`read_repair_chance`)으로 조절 필요

2. **Anti-Entropy 스케줄링**
   - 너무 자주: 리소스 낭비, 서비스 성능 저하
   - 너무 드물게: 불일치 누적, 복구량 폭증
   - 트래픽 낮은 시간대 실행 권장

3. **Merkle Tree 재구축 비용**
   - 데이터 변경 시 트리 일부 재계산
   - 대용량 데이터셋에서는 상당한 CPU 사용
   - Incremental rebuild 전략 필요
