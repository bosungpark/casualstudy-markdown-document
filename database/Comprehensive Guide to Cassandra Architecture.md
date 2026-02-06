# Comprehensive Guide to Cassandra Architecture

## 출처
- **링크**: https://www.instaclustr.com/blog/cassandra-architecture/
- **사이트**: Instaclustr (NetApp Company)

---

## AI 요약

### 핵심 분산 아키텍처

Apache Cassandra는 **마스터 노드 없이 모든 노드가 동등한 피어-투-피어(Peer-to-Peer) 분산 시스템**입니다. 각 노드가 독립적으로 클라이언트 요청을 처리할 수 있어 단일 장애점(Single Point of Failure)이 존재하지 않습니다.

### 클러스터 토폴로지

**Gossip Protocol**:
- 각 노드는 **매초마다 최대 3개의 피어와 상태 정보를 교환**
- 중앙 조정자 없이 클러스터 전체가 각 노드의 상태를 파악
- Seed 노드는 신규 노드 부트스트래핑에만 사용되며 장애점이 아님

**구성 요소**:
- **노드(Node)**: 데이터를 저장하는 기본 단위
- **랙(Rack)**: 물리적 위치 또는 논리적 그룹
- **데이터 센터(DC)**: 지리적으로 분산된 배포 단위

### 데이터 파티셔닝 & 토큰 분배

**Consistent Hashing**:
- 파티션 키가 **Murmur3Partitioner**를 통해 토큰(signed 64-bit integer)으로 변환
- 토큰 범위: -2^63 ~ +2^63-1
- 각 노드는 토큰 링에서 특정 범위를 담당

**Virtual Nodes (Vnodes)**:
```
물리 노드 1개 = 256개의 Vnode (기본값)

장점:
- 토큰 수동 할당 불필요
- 노드 추가/제거 시 자동 균등 분배
- 노드 복구 시 여러 노드에서 병렬 스트리밍
```

### Replication 전략

**복제 팩터(Replication Factor)**:
- 데이터 복제본 수 설정 (일반적으로 3 권장)
- Keyspace 레벨에서 데이터 센터별로 설정 가능

| 전략 | 설명 | 사용 사례 |
|------|------|----------|
| **SimpleStrategy** | 단일 DC용, 토큰 순서대로 복제 | 개발/테스트 환경 |
| **NetworkTopologyStrategy** | 랙/DC 인식 복제 | **프로덕션 필수** |

**Snitch**:
- 노드 → 랙 → 데이터센터 매핑 정보 제공
- GossipingPropertyFileSnitch가 권장됨

### Tunable Consistency (조정 가능한 일관성)

Cassandra는 **쿼리 레벨에서 일관성을 조절**할 수 있습니다:

| 레벨 | 의미 | 트레이드오프 |
|------|------|-------------|
| ONE | 1개 노드 응답 | 최고 가용성, 최저 일관성 |
| QUORUM | (RF/2)+1 노드 응답 | 균형 |
| LOCAL_QUORUM | 로컬 DC에서 쿼럼 | 멀티 DC에서 권장 |
| ALL | 모든 복제본 응답 | 최고 일관성, 가용성 저하 |

**핵심 공식**:
```
R + W > RF → Strong Consistency 보장
(R: 읽기 레벨, W: 쓰기 레벨, RF: Replication Factor)
```

### Write Path (쓰기 경로)

```
Client Request
    ↓
Coordinator Node (아무 노드나 가능)
    ↓
┌─────────────────────────────────────┐
│ 1. Commit Log 기록 (WAL)           │
│    - 디스크에 순차 쓰기             │
│    - 장애 복구용                    │
├─────────────────────────────────────┤
│ 2. Memtable에 추가                 │
│    - 인메모리 구조                  │
│    - 파티션 키별로 정렬             │
├─────────────────────────────────────┤
│ 3. Memtable Flush → SSTable        │
│    - 메모리 임계값 도달 시          │
│    - 불변(immutable) 파일 생성      │
└─────────────────────────────────────┘
```

**핵심 특징**:
- 모든 쓰기는 **Append-Only** (덮어쓰기 없음)
- SSTable은 **불변** → 업데이트는 새 버전 생성
- **Last-Write-Wins**: 타임스탬프 기반 충돌 해결

### Read Path (읽기 경로)

```
Client Request
    ↓
Coordinator Node
    ↓
복제본 노드들에 병렬 요청
    ↓
┌─────────────────────────────────────┐
│ 1. Memtable 확인                   │
│ 2. Row Cache 확인 (활성화된 경우)   │
│ 3. Bloom Filter로 SSTable 필터링   │
│ 4. Partition Index → SSTable 접근  │
│ 5. 타임스탬프로 최신 버전 병합      │
└─────────────────────────────────────┘
```

**Bloom Filter**:
- 공간 효율적인 확률적 자료구조
- SSTable에 데이터 존재 여부를 빠르게 판단
- False Positive는 있지만 False Negative는 없음

### Compaction (압축)

**문제**: SSTable이 계속 쌓이면 읽기 성능 저하

**해결**: Compaction이 SSTable들을 병합

```
SSTable_1 + SSTable_2 + SSTable_3
            ↓ Compaction
     New_SSTable (정리된 최신 데이터)
```

**Compaction이 하는 일**:
1. 중복 키의 최신 버전만 유지
2. **Tombstone**(삭제 마커) 정리
3. 파일 수 감소 → 읽기 성능 향상

**주요 전략**:
| 전략 | 특징 | 적합한 워크로드 |
|------|------|----------------|
| **SizeTieredCompactionStrategy (STCS)** | 비슷한 크기끼리 병합 | 쓰기 중심 |
| **LeveledCompactionStrategy (LCS)** | 레벨별로 정리 | 읽기 중심 |
| **TimeWindowCompactionStrategy (TWCS)** | 시간 윈도우별 병합 | 시계열 데이터 |

### Tombstone과 TTL

**삭제 처리**:
- 즉시 삭제 불가 (분산 시스템의 한계)
- 대신 **Tombstone** 마커 생성
- Compaction 시 gc_grace_seconds 이후 제거

**TTL (Time-To-Live)**:
```sql
INSERT INTO users (id, name) VALUES (1, 'Alice') USING TTL 86400;
-- 24시간 후 자동으로 Tombstone 생성
```

### Anti-Entropy 메커니즘

백그라운드에서 일관성을 유지하는 메커니즘들:

| 메커니즘 | 동작 | 사용 시점 |
|----------|------|----------|
| **Read Repair** | 읽기 시 복제본 비교 후 동기화 | 쿼럼 읽기 중 |
| **Hinted Handoff** | 다운된 노드용 힌트 임시 저장 | 노드 일시 장애 |
| **Anti-Entropy Repair** | Merkle Tree로 차이 감지 후 동기화 | 정기 유지보수 |

### CQL (Cassandra Query Language)

SQL과 유사하지만 **중요한 제약**:
- ❌ JOIN 불가
- ❌ 서브쿼리 불가
- ✅ 파티션 키 필수 지정
- ✅ ORDER BY는 클러스터링 키 컬럼만

**데이터 모델링 핵심**:
```
"쿼리 주도 설계" - 쿼리 패턴에 맞춰 테이블 설계
→ 정규화보다 비정규화 우선
→ 읽기 최적화를 위해 데이터 중복 허용
```

### 아키텍처 설계 원칙

**Replication Factor 권장사항**:
- 홀수 권장 (일반적으로 3)
- 랙 수는 RF의 배수로 설정
- 데이터 센터당 최소 3개 랙

**선형 확장성**:
- 노드 추가 시 성능이 선형적으로 향상
- 단, 적절한 리소스 할당과 Vnode 설정 필요

---

## 내가 얻은 인사이트

Cassandra는 "쓰기 최적화"와 "가용성"을 최우선으로 설계된 데이터베이스입니다. Commit Log → Memtable → SSTable로 이어지는 쓰기 경로는 모든 쓰기를 순차 I/O로 처리하여 극도로 빠른 쓰기를 가능하게 합니다.

하지만 이 설계의 대가로 읽기는 여러 SSTable을 병합해야 하고, 삭제는 Tombstone으로 처리되어 즉시 공간을 확보하지 못합니다. Tunable Consistency는 개발자에게 일관성-가용성 트레이드오프를 쿼리 단위로 제어할 수 있는 강력한 도구를 제공하지만, 동시에 분산 시스템의 복잡성을 제대로 이해하지 못하면 데이터 불일치 문제를 야기할 수 있습니다.

"쿼리 주도 설계"라는 데이터 모델링 철학은 관계형 DB 사고방식에서 벗어나야 함을 의미합니다. 먼저 쿼리 패턴을 정의하고, 그에 맞춰 테이블을 설계하는 접근 방식이 필수입니다.
