
# Calvin: Fast Distributed Transactions for Partitioned Database Systems

## 출처
- [블로그 원문](https://www.mydistributed.systems/2020/08/calvin.html)
- 논문: Alexander Thomson et al., SIGMOD 2012

---

## 1. 문제의식과 배경

분산 데이터베이스에서 트랜잭션의 일관성과 원자성을 보장하려면 보통 2PL(2-Phase Locking)과 2PC(2-Phase Commit)를 조합한다. 하지만 2PL은 비결정적(nondeterministic)이라, 분산 환경에서 트랜잭션 순서가 샤드마다 달라질 수 있고, 2PC는 락 경합(Contetion Footprint)과 지연(latency)을 키운다.

예시: 두 트랜잭션 T1, T2가 여러 샤드에 동시에 도달하면, 각 샤드에서 실행 순서가 달라질 수 있고, deadlock 회피를 위해 abort가 발생할 수 있다. 이로 인해 isolation/atomicity가 깨질 수 있다. 이를 막으려면 2PC로 모든 샤드의 커밋을 조율해야 한다.

하지만 2PC+2PL 조합은 락을 오래 잡게 되어 경합이 커지고, 장애 복구도 복잡하다.

---

## 2. Calvin의 핵심 아이디어: 결정론적 순서화와 실행

Calvin은 "트랜잭션의 글로벌 순서"를 미리 정하고, 각 샤드가 이 순서를 따라 트랜잭션을 실행한다. 이로써 2PC 없이도 분산 트랜잭션의 일관성과 원자성을 보장할 수 있다.

- **Deterministic Locking**: 트랜잭션의 read/write set을 미리 파악해, 락을 FIFO로 잡고, 충돌 없는 트랜잭션은 병렬 실행.
- **Stored Procedure Only**: 트랜잭션은 반드시 stored procedure(비대화적, 사전 정의) 형태여야 하며, 실행 전 read/write set이 파악되어야 한다.
- **Replicated Log**: 모든 트랜잭션은 replicated log(분산 WAL)에 기록되어 장애 복구와 원자성 보장에 활용된다.

---

## 3. 아키텍처 및 동작 방식 (원문 구조 충실)

### 3.1 Sequencing Layer (글로벌 순서 결정)
- 각 노드의 Sequencer가 트랜잭션을 수집, 라운드로빈 및 배치(batch)로 글로벌 순서 결정.
- 복제(replication)는 비동기/동기 모두 지원. 동기 복제는 Paxos 등 합의 프로토콜 사용.
- 모든 트랜잭션은 replicated log에 기록. 장애 복구, durability, atomicity 보장.
- 트랜잭션 코드 내 비결정성(랜덤, 시스템 시간 등)은 Sequencer에서 미리 평가/제거(Pre-execution)하여 모든 복제본이 동일하게 실행되도록 함.

### 3.2 Scheduling Layer (결정론적 락킹)
- Sequencer에서 전달된 순서대로 각 샤드의 Scheduler가 트랜잭션을 처리.
- **Deterministic Locking**: 트랜잭션의 read/write set에 대해 락을 미리 요청, FIFO로 처리. 충돌 없는 트랜잭션은 병렬 실행 가능.
- Deadlock이 발생하지 않으며, abort 없이 항상 순서대로 실행.
- 락 테이블에 각 오브젝트별로 대기 큐를 두고, 필요한 락을 모두 획득하면 실행.

### 3.3 Storage Layer (실제 실행)
- Executor thread가 트랜잭션을 실행. 여러 샤드가 연관된 경우, 필요한 데이터를 서로 주고받으며 실행.
- 예시: 트랜잭션 T가 샤드 A의 x를 읽고, 샤드 B의 y를 x+1로 업데이트할 때, A에서 x를 읽어 B로 전달, B에서 y를 갱신.
- 모든 샤드가 동일한 순서와 논리로 트랜잭션을 실행하므로, 복제본 간 데이터 불일치가 발생하지 않음.

---

## 4. Complications (실제 적용 시 고려점, 원문 예시 충실)

### 4.1 Dependent Transactions (동적 read/write set)
- 트랜잭션 실행 중에 read/write set이 결정되는 경우(예: x를 읽고, 값에 따라 y 또는 z를 업데이트).
- Calvin은 reconnaissance query(탐색 쿼리)로 1차 read 후, 값이 바뀌면 재시도(2-phase). 이 과정에서 starvation(기아) 가능성 존재.
- strict serializability(선형성)는 보장됨. 성공 응답은 실제 커밋이 확정된 후에만 반환.

### 4.2 Disk Access Bottleneck
- 대량의 디스크 접근이 필요한 트랜잭션은 Sequencer에서 지연시켜 미리 데이터를 메모리에 올린 뒤 실행.
- Sequencer가 지연 시간을 추정해야 하며, 과소/과대 추정 모두 성능 저하 유발.
- 2PL에서는 트랜잭션 실행 중 락을 점진적으로 잡으나, Calvin은 시작 시점에 모든 락을 잡으므로, 느린 트랜잭션이 전체 병목이 될 수 있음.

---

## 6. 내가 얻은 인사이트

1. 분산 트랜잭션의 복잡성(2PC, deadlock, abort 등)을 "순서의 결정론" 하나로 극적으로 단순화할 수 있다.
2. Stored Procedure 기반 설계는 유연성(대화형 트랜잭션, 동적 쿼리) 대신, 예측 가능성과 일관성을 극대화하는 설계.
3. OLTP/OLAP 분리로 Calvin류 시스템은 OLTP(고정 트랜잭션, 높은 일관성)에는 강력하지만, OLAP/Ad-hoc 쿼리에는 부적합.
4. 실제 시스템 적용 시, read/write set 추론 자동화, 디스크 병목 완화, starvation 방지 등 추가 엔지니어링 필요.
5. Calvin의 아이디어는 현대 분산 DB(예: FaunaDB, FoundationDB 등)에 직접적 영향을 미침.
6. 결정론적 실행은 복제, 장애 복구, 일관성 유지 등 분산 시스템의 여러 난제를 동시에 해결하는 강력한 패턴임을 실감.
