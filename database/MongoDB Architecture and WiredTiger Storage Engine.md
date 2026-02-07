# MongoDB Architecture and WiredTiger Storage Engine

## 출처
- **아티클/논문**: WiredTiger Storage Engine Overview, MongoDB Internals: How Collections and Indexes Are Stored, MongoDB Replication and Sharding
- **저자/출처**: Severalnines, MongoDB Dev Community, GeeksforGeeks, WiredTiger Official Docs
- **링크**:
  - https://severalnines.com/blog/overview-wiredtiger-storage-engine-mongodb/
  - https://dev.to/mongodb/mongodb-internals-how-collections-and-indexes-are-stored-in-wiredtiger-2ed
  - https://source.wiredtiger.com/develop/arch-index.html
  - https://www.geeksforgeeks.org/mongodb-replication-and-sharding/

---

## AI 요약

### 1. MongoDB 아키텍처 개요

MongoDB는 **문서 지향 NoSQL 데이터베이스**로, WiredTiger 스토리지 엔진(v3.2+ 기본값) 위에서 동작하며 Replica Set과 Sharding을 통해 고가용성과 수평 확장을 제공한다.

| 구성 요소 | 역할 |
|----------|------|
| **WiredTiger** | 스토리지 엔진 - 실제 데이터 저장/검색 담당 |
| **Replica Set** | 고가용성 - 데이터 복제 및 자동 페일오버 |
| **Sharding** | 수평 확장 - 데이터 분산 저장 |
| **mongos** | 쿼리 라우터 - 클라이언트 요청을 적절한 샤드로 라우팅 |

```
┌─────────────────────────────────────────────────────────────────┐
│                      MongoDB Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Client Application                                             │
│          │                                                       │
│          ▼                                                       │
│   ┌─────────────┐                                               │
│   │   mongos    │  ← Query Router                               │
│   └──────┬──────┘                                               │
│          │                                                       │
│    ┌─────┴─────┬─────────────┐                                  │
│    ▼           ▼             ▼                                  │
│ ┌──────┐   ┌──────┐     ┌──────┐                               │
│ │Shard1│   │Shard2│     │Shard3│  ← Each Shard = Replica Set   │
│ └──────┘   └──────┘     └──────┘                               │
│                                                                  │
│         ┌────────────────────┐                                  │
│         │   Config Servers   │  ← Metadata (Replica Set)        │
│         └────────────────────┘                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2. WiredTiger 스토리지 엔진

#### 핵심 특성

WiredTiger는 **MVCC(Multi-Version Concurrency Control)** 기반 스토리지 엔진으로, B-Tree와 LSM-Tree의 장점을 결합했다.

| 특성 | 설명 |
|------|------|
| **동시성 제어** | Document-level locking (문서 수준 잠금) |
| **압축** | Snappy, zlib, zstd 지원 |
| **저널링** | Write-Ahead Logging (WAL) |
| **체크포인트** | 주기적 스냅샷 (기본 60초) |
| **캐싱** | 내부 캐시 + OS 페이지 캐시 활용 |

#### 아키텍처 계층

```
┌─────────────────────────────────────────────────────────────┐
│                    WiredTiger Architecture                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   API Layer                          │    │
│  │   Connections │ Sessions │ Cursors │ Transactions   │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 Data Organization                    │    │
│  │        Schema │ Metadata │ Data Handles             │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  Data Sources                        │    │
│  │      B-Tree │ Row Store │ Column Store              │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                   │
│  ┌───────────────────┐  ┌───────────────────────────┐       │
│  │   Memory Layer    │  │    Persistence Layer      │       │
│  │  Cache │ Eviction │  │ Block Manager │ Checkpoint│       │
│  │  Concurrency      │  │ Logging │ Recovery        │       │
│  └───────────────────┘  └───────────────────────────┘       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### B-Tree vs LSM-Tree 하이브리드

| 구조 | 특징 | 적합한 워크로드 |
|------|------|----------------|
| **B-Tree** | 균형 트리, O(log n) 검색/삽입/삭제 | 읽기 중심, 랜덤 액세스 |
| **LSM-Tree** | 랜덤 쓰기 → 순차 쓰기 변환 | 쓰기 중심, 대량 삽입 |

WiredTiger는 기본적으로 **B-Tree**를 사용하며, 특정 워크로드에서 LSM-Tree의 이점도 활용한다.

---

### 3. 데이터 저장 구조

#### 파일 구조

```
data/
├── WiredTiger                    # 엔진 메타데이터
├── WiredTiger.lock               # 락 파일
├── WiredTiger.turtle             # 부트스트랩 메타데이터
├── WiredTiger.wt                 # 메타데이터 테이블
├── _mdb_catalog.wt               # MongoDB 카탈로그 (컬렉션/인덱스 매핑)
├── sizeStorer.wt                 # 크기 통계
├── collection-0-xxx.wt           # 컬렉션 데이터
├── index-1-xxx.wt                # 인덱스 데이터
├── journal/                      # WAL 저널 파일
│   └── WiredTigerLog.xxx
└── diagnostic.data/              # 진단 데이터
```

#### _mdb_catalog: 네임스페이스 디렉토리

`_mdb_catalog.wt`는 MongoDB의 내부 카탈로그로, 컬렉션과 인덱스를 WiredTiger 테이블에 매핑한다.

```
┌─────────────────────────────────────────────────────────────┐
│                    _mdb_catalog.wt                           │
├─────────────────────────────────────────────────────────────┤
│  Collection: mydb.users                                      │
│    → table:collection-0-6917019827977430149                 │
│    → Indexes:                                                │
│        _id_ → table:index-1-6917019827977430149             │
│        email_1 → table:index-2-6917019827977430149          │
├─────────────────────────────────────────────────────────────┤
│  Collection: mydb.orders                                     │
│    → table:collection-3-6917019827977430149                 │
│    → Indexes:                                                │
│        _id_ → table:index-4-6917019827977430149             │
└─────────────────────────────────────────────────────────────┘
```

#### B-Tree 페이지 구조

| 페이지 타입 | 타입 번호 | 내용 |
|------------|----------|------|
| **Branch Page** | 6 | 키 범위 + 자식 포인터 + 체크섬 |
| **Leaf Page** | 7 | 실제 (key, value) 쌍 |

```
                    ┌─────────────────┐
                    │  Branch Page    │
                    │   (Type 6)      │
                    │  [k1] [k2] [k3] │
                    └───┬───┬───┬────┘
                        │   │   │
          ┌─────────────┘   │   └─────────────┐
          ▼                 ▼                 ▼
    ┌───────────┐     ┌───────────┐     ┌───────────┐
    │ Leaf Page │     │ Leaf Page │     │ Leaf Page │
    │ (Type 7)  │     │ (Type 7)  │     │ (Type 7)  │
    │ k:v pairs │     │ k:v pairs │     │ k:v pairs │
    └───────────┘     └───────────┘     └───────────┘
```

#### RecordId와 문서 저장

컬렉션의 각 문서는 **RecordId**(unsigned 64-bit integer)를 키로 사용하여 저장된다.

```
Collection B-Tree:
┌─────────────────────────────────────────────────┐
│  Key (RecordId)  │         Value (BSON)         │
├──────────────────┼──────────────────────────────┤
│        1         │ { _id: ObjectId, name: "A" } │
│        2         │ { _id: ObjectId, name: "B" } │
│        3         │ { _id: ObjectId, name: "C" } │
└─────────────────────────────────────────────────┘

Index B-Tree (_id index):
┌─────────────────────────────────────────────────┐
│    Key (_id value)     │   Value (RecordId)     │
├────────────────────────┼────────────────────────┤
│  ObjectId("abc123")    │          1             │
│  ObjectId("def456")    │          2             │
│  ObjectId("ghi789")    │          3             │
└─────────────────────────────────────────────────┘
```

---

### 4. 동시성 제어 (MVCC)

#### Document-Level Concurrency

WiredTiger는 **문서 수준 잠금**을 제공하여 높은 동시성을 달성한다.

```
┌─────────────────────────────────────────────────────────────┐
│              MVCC: Multi-Version Concurrency Control         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Transaction T1 (Read)     Transaction T2 (Write)          │
│          │                         │                         │
│          ▼                         ▼                         │
│   ┌─────────────┐           ┌─────────────┐                 │
│   │ Snapshot @  │           │ Snapshot @  │                 │
│   │ Time = 100  │           │ Time = 101  │                 │
│   └─────────────┘           └─────────────┘                 │
│          │                         │                         │
│          ▼                         ▼                         │
│   Sees: Doc v1              Creates: Doc v2                 │
│   (consistent view)         (new version)                   │
│                                                              │
│   ┌─────────────────────────────────────────┐               │
│   │        Document Version History          │               │
│   │  v1 (time=100) ──► v2 (time=101) ──► ...│               │
│   └─────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

| 잠금 수준 | 범위 | 특징 |
|----------|------|------|
| **Collection-level** | 전체 컬렉션 | DDL 작업 시 |
| **Document-level** | 개별 문서 | DML 작업 시 (기본) |

#### 제약 사항

- 문서 **업데이트는 전체 다시 쓰기** (in-place 수정 불가)
- MVCC 특성상 동시 쓰기 시 새 버전 생성

---

### 5. 인덱스 구조

#### Primary Index (_id)

모든 컬렉션은 `_id` 필드에 대한 고유 인덱스를 자동 생성한다.

```javascript
// 문서 조회 과정
db.users.findOne({ _id: ObjectId("abc123") })

// 1. _id 인덱스에서 RecordId 조회
//    ObjectId("abc123") → RecordId: 42

// 2. 컬렉션 B-Tree에서 RecordId로 문서 조회
//    RecordId: 42 → { _id: ObjectId("abc123"), name: "John", ... }
```

#### Secondary Index

```javascript
// 인덱스 생성
db.users.createIndex({ email: 1 })

// Secondary Index B-Tree:
// Key: email 값
// Value: RecordId
```

#### Multikey Index (배열 필드)

배열 필드에 인덱스를 생성하면 각 배열 요소마다 별도 인덱스 엔트리가 생성된다.

```javascript
// 문서
{ _id: 1, tags: ["mongodb", "database", "nosql"] }

// Multikey Index 엔트리:
// "database" → RecordId: 1
// "mongodb"  → RecordId: 1
// "nosql"    → RecordId: 1
```

---

### 6. 저널링과 체크포인트

#### Write-Ahead Logging (WAL)

```
┌─────────────────────────────────────────────────────────────┐
│                    Write Path                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Client Write                                               │
│        │                                                     │
│        ▼                                                     │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│   │   Journal   │───►│   Cache     │───►│    Disk     │     │
│   │   (WAL)     │    │  (Memory)   │    │ (Checkpoint)│     │
│   └─────────────┘    └─────────────┘    └─────────────┘     │
│        │                    │                  ▲             │
│        │                    │                  │             │
│        ▼                    └──────────────────┘             │
│   Durability             Background Sync              │
│   Guaranteed             (every 60s)                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

| 구성 요소 | 기능 | 주기 |
|----------|------|------|
| **Journal** | 모든 쓰기 작업 기록 (durability 보장) | 매 쓰기 또는 100ms |
| **Checkpoint** | 메모리 → 디스크 스냅샷 | 기본 60초 |

#### 복구 과정

```
Crash Recovery:
1. 마지막 체크포인트 로드
2. 저널에서 체크포인트 이후 작업 재생 (replay)
3. 일관된 상태 복원
```

---

### 7. 압축 (Compression)

#### 지원 알고리즘

| 알고리즘 | 압축률 | 속도 | 용도 |
|---------|--------|------|------|
| **snappy** (기본) | 중간 | 빠름 | 범용 |
| **zlib** | 높음 | 느림 | 저장 공간 중시 |
| **zstd** | 높음 | 빠름 | 균형 (권장) |
| **none** | - | - | CPU 최소화 |

#### Prefix Compression

인덱스에서 공통 접두사를 압축하여 저장 공간 절약:

```
원본 키:          압축 후:
"user_001"       "user_" + "001"
"user_002"                  "002"
"user_003"                  "003"
```

---

### 8. Replica Set 아키텍처

#### 구성 요소

```
┌─────────────────────────────────────────────────────────────┐
│                     Replica Set                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│        ┌─────────────────────────────────┐                  │
│        │           PRIMARY               │                  │
│        │  • 모든 쓰기 작업 처리           │                  │
│        │  • Oplog 생성                   │                  │
│        └───────────────┬─────────────────┘                  │
│                        │ Replication                         │
│            ┌───────────┴───────────┐                        │
│            ▼                       ▼                        │
│   ┌─────────────────┐     ┌─────────────────┐              │
│   │   SECONDARY 1   │     │   SECONDARY 2   │              │
│   │  • 데이터 복제   │     │  • 데이터 복제   │              │
│   │  • 읽기 분산    │     │  • 읽기 분산    │              │
│   └─────────────────┘     └─────────────────┘              │
│                                                              │
│   [Arbiter: 투표만 참여, 데이터 저장 안 함]                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Oplog (Operation Log)

Primary의 모든 변경 사항을 기록하는 **Capped Collection**:

```javascript
// Oplog 엔트리 예시
{
  "ts": Timestamp(1234567890, 1),
  "op": "i",                    // i=insert, u=update, d=delete
  "ns": "mydb.users",
  "o": { "_id": 1, "name": "John" }
}
```

#### 자동 페일오버

```
Primary 장애 발생
        │
        ▼
┌─────────────────────┐
│   Election 시작     │  ← Secondaries가 투표
└─────────────────────┘
        │
        ▼
┌─────────────────────┐
│  새 Primary 선출    │  ← 과반수 투표 필요
└─────────────────────┘
        │
        ▼
    서비스 재개
```

---

### 9. Sharding 아키텍처

#### 핵심 구성 요소

```
┌─────────────────────────────────────────────────────────────┐
│                    Sharded Cluster                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────────────────────────────────────┐       │
│   │              Client Applications                 │       │
│   └───────────────────────┬─────────────────────────┘       │
│                           │                                  │
│   ┌───────────────────────▼─────────────────────────┐       │
│   │                    mongos                        │       │
│   │            (Query Router Cluster)                │       │
│   └─────┬─────────────────┬─────────────────┬───────┘       │
│         │                 │                 │                │
│   ┌─────▼─────┐     ┌─────▼─────┐     ┌─────▼─────┐         │
│   │  Shard 1  │     │  Shard 2  │     │  Shard 3  │         │
│   │(Replica   │     │(Replica   │     │(Replica   │         │
│   │  Set)     │     │  Set)     │     │  Set)     │         │
│   │           │     │           │     │           │         │
│   │ Chunks:   │     │ Chunks:   │     │ Chunks:   │         │
│   │ A-F       │     │ G-M       │     │ N-Z       │         │
│   └───────────┘     └───────────┘     └───────────┘         │
│                                                              │
│   ┌─────────────────────────────────────────────────┐       │
│   │              Config Servers                      │       │
│   │           (Replica Set - CSRS)                   │       │
│   │  • Chunk 메타데이터                              │       │
│   │  • Shard 매핑 정보                               │       │
│   └─────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

#### Shard Key 전략

| 전략 | 특징 | 장점 | 단점 |
|------|------|------|------|
| **Range Sharding** | 키 범위로 분할 | 범위 쿼리 효율적 | 핫스팟 발생 가능 |
| **Hashed Sharding** | 해시값으로 분할 | 균등 분산 | 범위 쿼리 비효율적 |
| **Zone Sharding** | 지역/조건별 분할 | 데이터 지역성 보장 | 설정 복잡 |

```javascript
// Range Sharding
sh.shardCollection("mydb.users", { "created_at": 1 })

// Hashed Sharding
sh.shardCollection("mydb.users", { "_id": "hashed" })
```

#### Chunk와 Balancer

```
Chunk: 연속된 Shard Key 범위의 문서 그룹

┌─────────────────────────────────────────────────────────────┐
│                        Balancer                              │
│  • 자동으로 Chunk를 샤드 간 이동                             │
│  • 균등한 데이터 분산 유지                                   │
│  • 기본: 백그라운드에서 동작                                  │
└─────────────────────────────────────────────────────────────┘

Before Balancing:          After Balancing:
Shard1: 100 chunks         Shard1: 50 chunks
Shard2: 20 chunks   →      Shard2: 50 chunks
Shard3: 30 chunks          Shard3: 50 chunks
```

---

### 10. 메모리 관리

#### WiredTiger 캐시

```
┌─────────────────────────────────────────────────────────────┐
│                    Memory Architecture                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Total RAM                                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                                                      │   │
│   │  ┌────────────────────┐  ┌────────────────────┐     │   │
│   │  │ WiredTiger Cache   │  │   OS Page Cache    │     │   │
│   │  │ (Internal Cache)   │  │  (Filesystem)      │     │   │
│   │  │                    │  │                    │     │   │
│   │  │ • Uncompressed     │  │ • Compressed data  │     │   │
│   │  │   working set      │  │ • Read-ahead       │     │   │
│   │  │ • 50% of RAM - 1GB │  │ • Eviction by OS   │     │   │
│   │  │   (default)        │  │                    │     │   │
│   │  └────────────────────┘  └────────────────────┘     │   │
│   │                                                      │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### 캐시 설정

```javascript
// mongod.conf
storage:
  wiredTiger:
    engineConfig:
      cacheSizeGB: 4  // 내부 캐시 크기 지정

// 기본값: max(50% of (RAM - 1GB), 256MB)
```

#### Eviction 정책

- LRU (Least Recently Used) 기반
- 압축된 데이터는 OS 캐시에서 관리
- Dirty 페이지는 체크포인트 시 디스크로 flush

---

## 내가 얻은 인사이트

### 스토리지 관점

1. **Document-Level Locking의 의미**
   - RDBMS의 row-level locking과 유사하지만, 문서가 복잡한 중첩 구조를 가질 수 있어 더 큰 단위
   - 업데이트가 전체 문서 다시 쓰기라는 점은 성능 고려 필요
   - 큰 문서 + 잦은 부분 업데이트 = 비효율적

2. **RecordId 설계의 우아함**
   - 문서 이동 시에도 인덱스 재구성 불필요
   - 인덱스는 RecordId만 가리키므로 컬렉션 재구성이 용이
   - PostgreSQL의 CTID와 유사한 개념

3. **Dual Cache 전략**
   - WiredTiger 내부 캐시: 압축 해제된 작업 세트
   - OS 페이지 캐시: 압축된 데이터
   - 메모리 효율과 성능의 균형

### 분산 시스템 관점

1. **Replica Set은 필수**
   - Sharded Cluster에서도 각 샤드는 Replica Set
   - Config Server도 Replica Set
   - 단일 장애점(SPOF) 제거 설계

2. **Shard Key 선택의 중요성**
   - 한번 설정하면 변경 어려움 (4.4+에서 resharding 지원)
   - 카디널리티, 쿼리 패턴, 쓰기 분산 모두 고려 필요
   - 잘못된 Shard Key = 핫스팟 + 성능 저하

3. **mongos의 역할**
   - 클라이언트는 단일 엔드포인트로 인식
   - 복잡한 분산 쿼리 처리 추상화
   - Stateless하므로 수평 확장 용이

### 운영 관점

1. **저널링과 체크포인트 이해**
   - 저널: 즉각적 durability (100ms 이내)
   - 체크포인트: 메모리 → 디스크 동기화 (60초)
   - 복구 시간 = 마지막 체크포인트 이후 저널 재생 시간

2. **압축 알고리즘 선택**
   - snappy: 빠른 응답 중시
   - zstd: 저장 공간과 성능 균형 (권장)
   - zlib: 레거시, 압축률 중시

3. **WiredTiger 도구 활용**
   - `wt dump`: 테이블 내용 덤프
   - `db.collection.stats()`: 컬렉션 통계
   - `db.serverStatus().wiredTiger`: 엔진 상태 모니터링
