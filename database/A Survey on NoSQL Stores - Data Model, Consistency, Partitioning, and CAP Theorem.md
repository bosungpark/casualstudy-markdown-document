# A Survey on NoSQL Stores

## 출처
- **논문**: "A Survey on NoSQL Stores"
- **저자**: Ali Davoudian, Liu Chen, Mengchi Liu
- **저널**: ACM Computing Surveys (CSUR), Vol. 51, No. 2, Article 40
- **출판**: April 2018
- **DOI**: https://doi.org/10.1145/3158661
- **인용 횟수**: 376회 (Google Scholar 기준)
- **키워드**: NoSQL, Data Model, Consistency Model, Partitioning, CAP Theorem, ACID, Replication, Elasticity

---

## AI 요약

### 1. 연구 배경 및 목적
빅데이터 저장 및 쿼리에 대한 최근 요구사항은 전통적인 관계형 데이터베이스 시스템(RDBMS)의 다양한 한계를 드러냈습니다. 이에 따라 NoSQL이라는 새로운 비관계형 데이터 저장소가 등장했습니다. 본 서베이는 **분산 데이터베이스 시스템의 4가지 비직교적(non-orthogonal) 설계 원칙**에 따라 NoSQL 저장소의 설계 결정을 명확히 하는 것을 목표로 합니다:

1. **Data Model** (데이터 모델)
2. **Consistency Model** (일관성 모델)
3. **Data Partitioning** (데이터 파티셔닝)
4. **CAP Theorem** (CAP 정리)

### 2. 4가지 핵심 설계 원칙

#### 2.1 Data Model (데이터 모델)

NoSQL 데이터베이스는 다음 4가지 주요 데이터 모델로 분류됩니다:

##### (1) Key-Value Stores
- **개념**: 가장 단순한 형태. Key → Value 매핑
- **특징**: 빠른 읽기/쓰기, 수평적 확장성 우수
- **예시**: Redis, DynamoDB, Riak, Voldemort
- **사용 사례**: 세션 저장, 캐싱, 메타데이터 관리

##### (2) Document Stores
- **개념**: JSON, XML, BSON 등의 문서 형태로 데이터 저장
- **특징**: 스키마 유연성, 복잡한 중첩 구조 지원
- **예시**: MongoDB, CouchDB, RavenDB
- **사용 사례**: 콘텐츠 관리 시스템(CMS), 카탈로그, 사용자 프로필

##### (3) Column-Family Stores
- **개념**: 컬럼을 기준으로 데이터를 그룹화 (Row Key → Column Family → Column)
- **특징**: 대규모 분석 쿼리에 최적화, 압축 효율 높음
- **예시**: Cassandra, HBase, BigTable
- **사용 사례**: 시계열 데이터, 로그 분석, IoT 센서 데이터

##### (4) Graph Stores
- **개념**: 노드(Node)와 엣지(Edge)로 관계를 명시적으로 표현
- **특징**: 복잡한 관계 탐색에 최적화 (소셜 그래프, 추천 시스템)
- **예시**: Neo4j, OrientDB, JanusGraph, ArangoDB
- **사용 사례**: 소셜 네트워크, 지식 그래프, 사기 탐지, 추천 엔진

#### 2.2 Consistency Model (일관성 모델)

분산 시스템에서 복제된 데이터의 일관성을 어떻게 보장할 것인가에 대한 다양한 모델:

##### Strong Consistency (강한 일관성)
- **Linearizability**: 모든 읽기는 최신 쓰기를 반환
- **Sequential Consistency**: 모든 프로세스가 동일한 순서로 연산을 관찰
- **장점**: 데이터 정확성 보장
- **단점**: 높은 지연 시간, 가용성 저하 가능
- **예시**: Google Spanner, CockroachDB

##### Weak Consistency (약한 일관성)
- **Eventual Consistency**: 충분한 시간이 지나면 모든 복제본이 동일한 상태로 수렴
- **Causal Consistency**: 인과 관계가 있는 연산만 순서 보장
- **Session Consistency**: 동일 세션 내에서만 일관성 보장
- **장점**: 높은 가용성, 낮은 지연
- **단점**: 일시적 불일치 허용
- **예시**: DynamoDB, Cassandra (튜닝 가능), Riak

##### 일관성 트레이드오프
```
Strong Consistency
    ↑
    |  높은 정확성, 낮은 성능
    |
    ├── Sequential Consistency
    ├── Causal Consistency
    ├── Session Consistency
    |  
    |  낮은 정확성, 높은 성능
    ↓
Eventual Consistency
```

#### 2.3 Data Partitioning (데이터 파티셔닝)

대규모 데이터를 여러 노드에 분산 저장하는 전략:

##### (1) Hash-based Partitioning
- **Consistent Hashing**: 노드 추가/제거 시 최소한의 데이터 이동
- **특징**: 부하 분산 우수, 범위 쿼리 비효율
- **예시**: Cassandra, DynamoDB, Riak
- **장점**: 균등한 데이터 분산
- **단점**: Range Query 지원 어려움

##### (2) Range-based Partitioning
- **개념**: 키 범위에 따라 데이터 분할 (1-1000 → Node A, 1001-2000 → Node B)
- **특징**: 범위 쿼리 효율적, Hot Spot 발생 가능
- **예시**: HBase, BigTable, MongoDB (Range-based Sharding)
- **장점**: 순차 스캔 성능 우수
- **단점**: 특정 범위에 트래픽 집중 시 불균형

##### (3) Hybrid Approaches
- **개념**: Hash + Range 조합
- **예시**: Cassandra의 Compound Partition Key

#### 2.4 CAP Theorem (CAP 정리)

분산 시스템은 다음 3가지 중 **최대 2가지만** 동시에 보장할 수 있습니다:

- **C (Consistency)**: 모든 노드가 동시에 같은 데이터를 보여줌
- **A (Availability)**: 모든 요청이 응답을 받음 (일부 노드 장애 시에도)
- **P (Partition Tolerance)**: 네트워크 분할에도 시스템이 동작

##### NoSQL 시스템의 CAP 선택

**CP 시스템 (Consistency + Partition Tolerance)**
- 가용성을 일부 희생하고 일관성 우선
- 예시: HBase, MongoDB, Redis Cluster
- 사용 사례: 금융 거래, 재고 관리

**AP 시스템 (Availability + Partition Tolerance)**
- 일관성을 일부 희생하고 가용성 우선
- 예시: Cassandra, DynamoDB, Riak, CouchDB
- 사용 사례: 소셜 미디어, IoT, 로그 수집

**CA 시스템 (Consistency + Availability)**
- 네트워크 분할을 허용하지 않음 (단일 노드 또는 완벽한 네트워크 가정)
- 예시: 전통적인 RDBMS (MySQL, PostgreSQL in single-node mode)
- 현실적으로 분산 시스템에서는 불가능 (P는 필수)

```
       Consistency (C)
            /\
           /  \
          /    \
         /  CP  \
        /        \
       /          \
      /     CA     \
     /______________\
    /                \
   /        AP        \
  /__________________\
Availability (A)    Partition Tolerance (P)
```

### 3. ACID vs BASE

#### ACID (전통적 RDBMS)
- **Atomicity**: 트랜잭션의 모든 연산이 성공 또는 모두 실패
- **Consistency**: 트랜잭션 후 데이터베이스는 유효한 상태 유지
- **Isolation**: 동시 실행 트랜잭션들이 서로 격리
- **Durability**: 커밋된 트랜잭션은 영구 저장

#### BASE (NoSQL 시스템)
- **Basically Available**: 기본적으로 가용
- **Soft state**: 상태가 시간에 따라 변할 수 있음
- **Eventually consistent**: 최종적으로 일관성 도달

### 4. 복제 (Replication) 전략

#### Master-Slave Replication
- **특징**: 단일 마스터에 쓰기, 여러 슬레이브에서 읽기
- **장점**: 읽기 성능 향상, 백업 용이
- **단점**: 마스터 장애 시 쓰기 불가, 일관성 지연

#### Multi-Master Replication
- **특징**: 여러 노드에 쓰기 가능
- **장점**: 높은 가용성, 낮은 지연
- **단점**: 충돌 해결 복잡

#### Quorum-based Replication
- **개념**: N개 복제본 중 W개 쓰기 성공, R개 읽기 필요
- **공식**: W + R > N → 강한 일관성
- **예시**: Cassandra (Tunable Consistency)

### 5. 주요 NoSQL 시스템 분류

| 시스템 | 데이터 모델 | CAP | 일관성 모델 | 파티셔닝 |
|--------|------------|-----|------------|---------|
| **Cassandra** | Column-Family | AP | Tunable (Eventual → Strong) | Consistent Hashing |
| **MongoDB** | Document | CP | Strong (default) | Range-based Sharding |
| **DynamoDB** | Key-Value | AP | Eventual | Consistent Hashing |
| **HBase** | Column-Family | CP | Strong | Range-based |
| **Redis** | Key-Value | CP | Strong | Hash-based |
| **Neo4j** | Graph | CP | Strong | Graph-specific |
| **Riak** | Key-Value | AP | Eventual | Consistent Hashing |
| **CouchDB** | Document | AP | Eventual | Consistent Hashing |

### 6. 설계 결정 시 고려사항

#### 데이터 모델 선택
- **관계형 데이터 많음** → RDBMS 또는 Graph Store
- **유연한 스키마 필요** → Document Store
- **대규모 분석 쿼리** → Column-Family Store
- **단순 Key-Value 접근** → Key-Value Store

#### 일관성 vs 가용성
- **금융, 재고** → Strong Consistency (CP)
- **소셜 미디어, 로그** → Eventual Consistency (AP)
- **세션 관리** → Session Consistency

#### 파티셔닝 전략
- **균등 분산 중요** → Hash-based
- **범위 쿼리 많음** → Range-based
- **Hot Spot 회피** → Consistent Hashing + Virtual Nodes

---

## 내가 얻은 인사이트

하나같이 어디선가 한 번씩 들어본 이야기들인데, 모아서 보니까 반가웠다. 특별하지는 않았다.