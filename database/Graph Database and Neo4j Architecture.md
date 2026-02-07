# Graph Database and Neo4j Architecture

## 출처
- **아티클/논문**: Neo4j System Architecture, What is a Graph Database
- **저자/출처**: Neo4j Documentation, DeepWiki
- **링크**:
  - https://deepwiki.com/neo4j/neo4j/2-neo4j-system-architecture
  - https://neo4j.com/docs/getting-started/graph-database/

---

## AI 요약

### 1. Graph Database란?

그래프 데이터베이스는 데이터를 **노드(Node)**, **관계(Relationship)**, **속성(Property)**으로 저장하는 데이터베이스이다. 테이블이나 문서가 아닌 그래프 구조로 데이터를 표현하여 관계 중심의 쿼리에 최적화되어 있다.

| 구성 요소 | 설명 | 예시 |
|-----------|------|------|
| **Node** | 엔티티를 표현하는 개체 | Person, Product, Order |
| **Relationship** | 노드 간 연결 (방향성 필수) | KNOWS, PURCHASED, LIKES |
| **Property** | 노드/관계에 저장되는 key-value 쌍 | name: "John", age: 30 |
| **Label** | 노드의 역할/분류를 식별 | :User, :Admin |

```
     ┌─────────────┐          KNOWS           ┌─────────────┐
     │   Person    │ ───────────────────────▶ │   Person    │
     │  name: Bob  │                          │ name: Alice │
     │  age: 30    │                          │  age: 28    │
     └─────────────┘                          └─────────────┘
           │
           │ PURCHASED
           ▼
     ┌─────────────┐
     │   Product   │
     │ name: Phone │
     │ price: 999  │
     └─────────────┘
```

### 2. Neo4j 시스템 아키텍처

Neo4j는 여러 계층으로 구성된 아키텍처를 가진다.

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interfaces                         │
│              (Cypher Shell, Browser, Drivers)               │
├─────────────────────────────────────────────────────────────┤
│                    Query Processing                         │
│         Parser → Semantic Analysis → Planning → Execution   │
├─────────────────────────────────────────────────────────────┤
│                     Database Engine                         │
│    ┌─────────────────┐    ┌─────────────────────────────┐  │
│    │ Transaction Mgmt│    │      Storage Engine         │  │
│    │  (ACID 보장)    │    │  (Nodes, Rels, Properties)  │  │
│    └─────────────────┘    └─────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                 Recovery & Configuration                    │
│           (Transaction Logs, Checkpoints, Settings)         │
└─────────────────────────────────────────────────────────────┘
```

### 3. Query Processing Pipeline

Cypher 쿼리는 4단계 파이프라인을 통해 처리된다.

| 단계 | 역할 | 상세 |
|------|------|------|
| **Parser** | 쿼리 문자열을 AST로 변환 | 문법 검증 |
| **Semantic Analysis** | 유효성 검증 | 변수 스코프, 타입 체크, 패턴 검증 |
| **Planning** | 실행 계획 생성 | 인덱스, 통계 기반 최적화 |
| **Execution** | 트랜잭션 컨텍스트 내 실행 | 결과 집계 및 반환 |

```cypher
// Cypher 쿼리 예시
MATCH (p:Person)-[:KNOWS]->(friend:Person)
WHERE p.name = 'Bob'
RETURN friend.name, friend.age
```

### 4. Storage Engine

스토리지 엔진은 그래프 데이터의 영속성을 담당한다.

| 저장 요소 | 설명 |
|-----------|------|
| Node Records | 노드 데이터 저장 |
| Relationship Records | 관계 데이터 저장 |
| Property Store | 속성 key-value 저장 |
| Label/Type Tokens | 레이블 및 관계 타입 토큰화 |
| Schema Indexes | 스키마 인덱스 관리 |
| Transaction Logs | 트랜잭션 로그 (WAL) |

### 5. Transaction Management (ACID)

Neo4j는 완전한 ACID 트랜잭션을 지원한다.

| 속성 | 구현 방식 |
|------|-----------|
| **Atomicity** | KernelTransaction으로 원자적 연산 보장 |
| **Consistency** | 제약 조건 및 검증 |
| **Isolation** | 동시 연산 간 격리 |
| **Durability** | Transaction Log를 통한 영속성 |

### 6. Recovery System

장애 복구 프로세스:

```
1. Transaction Log 검사
        ↓
2. 미완료 트랜잭션 식별
        ↓
3. 커밋된 트랜잭션 적용 (Redo)
        ↓
4. 미커밋 트랜잭션 롤백 (Undo)
        ↓
5. Checkpoint 생성
        ↓
6. 인덱스 복구/수리
```

### 7. Graph DB vs Relational DB

| 항목 | Graph DB | Relational DB |
|------|----------|---------------|
| **JOIN 연산** | 불필요 (관계가 저장됨) | 비용이 큰 JOIN 필요 |
| **스키마** | 유연함, 동적 변경 가능 | 고정 스키마 |
| **관계 탐색** | O(1) - 직접 포인터 | O(n) - 인덱스 스캔 |
| **적합한 쿼리** | 관계 중심 쿼리 | 집계, 범위 쿼리 |
| **확장성** | 복잡한 관계에 강함 | 단순 데이터에 효율적 |

---

## 내가 얻은 인사이트

### 데이터 모델링 관점

1. **관계의 1급 시민화 (First-class Citizen)**
   - RDBMS에서 관계는 외래키로 표현되어 JOIN이 필요하지만, Graph DB에서는 관계 자체가 저장 단위
   - 관계에도 속성을 부여할 수 있어 "언제 친구가 되었는지", "얼마나 자주 연락하는지" 등 표현 가능

2. **Index-free Adjacency**
   - 각 노드가 인접 노드에 대한 직접 포인터를 가짐
   - 관계 탐색이 데이터 크기와 무관하게 일정한 성능 (O(1))

### 아키텍처 관점

1. **쿼리 최적화의 중요성**
   - Cypher Query Planner가 통계, 인덱스, 제약 조건을 기반으로 실행 계획 최적화
   - RDBMS의 Query Optimizer와 유사한 역할이지만 그래프 순회에 특화

2. **ACID와 성능의 균형**
   - Transaction Log를 통한 WAL(Write-Ahead Logging) 방식으로 durability 보장
   - Recovery 시스템이 Redo/Undo 로직으로 일관성 복구

### 활용 관점

1. **적합한 Use Case**
   - 소셜 네트워크: 친구 관계, 영향력 분석
   - 추천 시스템: "이 상품을 산 사람이 본 다른 상품"
   - 금융 사기 탐지: 복잡한 자금 흐름 추적
   - 지식 그래프: 개념 간 관계 표현

2. **부적합한 Use Case**
   - 단순 CRUD 중심 애플리케이션
   - 대량 집계/분석 쿼리 (OLAP)
   - 관계가 거의 없는 독립적인 레코드 저장
