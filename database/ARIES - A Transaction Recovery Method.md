# ARIES: A Transaction Recovery Method

## 출처
- **아티클/논문**: ARIES: A Transaction Recovery Method Supporting Fine-Granularity Locking and Partial Rollbacks Using Write-Ahead Logging (Mohan et al., 1992, ACM TODS)
- **저자/출처**: C. Mohan, D. Haderle, B. Lindsay, H. Pirahesh, P. Schwarz (IBM Almaden Research)
- **링크**: https://cs.stanford.edu/people/chrismre/cs345/rl/aries.pdf
- **보조 자료**:
  - [Database Recovery Demystified - Yash Agarwal](https://yashagw.github.io/blog/db-recovery/)
  - [Write-ahead logging and the ARIES crash recovery algorithm - Kevin Sookocheff](https://sookocheff.com/post/databases/write-ahead-logging/)
  - [CMU 15-445 Lecture 21 - ARIES Database Crash Recovery](https://15445.courses.cs.cmu.edu/fall2019/notes/21-recovery.pdf)

---

## AI 요약

### 1. ARIES란?

**ARIES (Algorithms for Recovery and Isolation Exploiting Semantics)**는 IBM이 1992년 발표한 트랜잭션 복구 알고리즘으로, 오늘날 거의 모든 상용 RDBMS (DB2, SQL Server, PostgreSQL, MySQL InnoDB 등)의 복구 엔진 설계 원형이 되었다.

핵심은 **WAL (Write-Ahead Logging) + No-Force/Steal 버퍼 정책 + 3-Phase Recovery** 의 조합이다.

| 특성 | 값 |
|---|---|
| **버퍼 정책** | Steal + No-Force |
| **로깅 방식** | Physical / Physiological Logging |
| **복구 방식** | Repeating History → Selective Undo |
| **로그 모델** | Redo + Undo + CLR (Compensation) |
| **잠금 단위** | Record-level (Fine-Granularity) |
| **체크포인트** | Fuzzy Checkpoint (non-blocking) |
| **부분 롤백** | Savepoint 지원 |

### 2. 왜 ARIES가 필요한가? — Steal/No-Force의 함정

상용 DB는 성능을 위해 두 가지 공격적인 버퍼 정책을 채택한다.

| 정책 | 의미 | 부작용 |
|---|---|---|
| **STEAL** | 커밋되지 않은 트랜잭션의 더티 페이지를 디스크에 쓸 수 있다 | 크래시 시 미커밋 변경이 디스크에 남음 → **UNDO 필요** |
| **NO-FORCE** | 커밋 시점에 모든 더티 페이지를 디스크에 쓰지 않아도 된다 | 크래시 시 커밋된 변경이 디스크에 없을 수 있음 → **REDO 필요** |

```
 [Buffer Pool]                       [Disk]
   ┌─────────┐                    ┌──────────┐
   │ Page A  │ ── STEAL 가능 ──▶ │ Page A'  │  (T1 미커밋이지만 flush됨)
   │ (T1)    │                    └──────────┘
   ├─────────┤
   │ Page B  │ ── NO-FORCE  ──▶  (T2 커밋했지만 아직 flush 안 됨)
   │ (T2 ✓) │                    
   └─────────┘
       ↓ Crash
  복구 시: A는 UNDO해야 하고, B는 REDO해야 함
```

→ 이를 해결하려면 **로그 한 줄에 Before-Image (UNDO용) + After-Image (REDO용)** 가 모두 들어가야 한다.

### 3. Write-Ahead Logging (WAL) 프로토콜

ARIES의 가장 근본적인 규칙은 두 가지다.

1. **로그 우선 (Log-Ahead)**: 데이터 페이지 P를 디스크에 쓰기 전에, P를 수정한 모든 로그 레코드가 먼저 안정 저장소(stable storage)에 기록되어야 한다.
2. **커밋 시 강제 (Force-at-Commit)**: 트랜잭션 커밋을 사용자에게 알리기 전에, COMMIT 로그 레코드가 안정 저장소에 도달해야 한다.

```
 ┌─────────────────────────────────────────────┐
 │  Rule:  pageLSN(P) ≤ flushedLSN             │
 │         (P를 디스크에 쓰려면 flushedLSN이    │
 │          pageLSN을 따라잡아야 한다)          │
 └─────────────────────────────────────────────┘
```

**성능 이점**: 1,000개 페이지를 수정한 트랜잭션이 1,000번의 랜덤 디스크 쓰기 대신 **단 한 번의 순차 로그 쓰기**로 커밋을 완료할 수 있다.

### 4. 핵심 자료구조 — LSN과 두 개의 테이블

#### 4-1. LSN (Log Sequence Number) 패밀리

LSN은 단조 증가하는 로그 레코드의 고유 식별자이며, ARIES는 여러 변종을 사용한다.

| 이름 | 위치 | 의미 |
|---|---|---|
| **LSN** | 로그 레코드 | 레코드의 고유 ID (단조 증가) |
| **pageLSN** | 각 페이지 헤더 | 그 페이지를 마지막으로 수정한 로그의 LSN |
| **flushedLSN** | 메모리 | 디스크에 안정적으로 기록된 마지막 LSN |
| **prevLSN** | 로그 레코드 내부 | 같은 트랜잭션의 직전 로그 LSN (역방향 체인) |
| **lastLSN** | Transaction Table | 트랜잭션이 마지막으로 쓴 로그 LSN |
| **recLSN** | Dirty Page Table | 페이지를 더티로 만든 가장 오래된 LSN |

```
 Log:   [LSN10]──[LSN20]──[LSN30]──[LSN40]──[LSN50]
         T1.upd   T2.upd   T1.upd   T2.upd   T1.upd
           ↑________prevLSN________↑________prevLSN_↑
                                                    └── T1.lastLSN
```

#### 4-2. Transaction Table (TT)

활성 트랜잭션 추적용.

| TxnID | Status | lastLSN |
|---|---|---|
| T1 | Running | 50 |
| T2 | Committed | 40 |

#### 4-3. Dirty Page Table (DPT)

버퍼 풀에 있는 더티 페이지 추적용. **recLSN은 REDO의 시작점을 결정**한다.

| PageID | recLSN |
|---|---|
| P5 | 10 |
| P9 | 25 |

크기는 DB 전체가 아닌 **버퍼 풀 크기**에 비례한다 (디스크에 flush되면 제거됨).

### 5. 로그 레코드 종류와 구조

```
┌────────────────────────────────────────────────┐
│ LSN | Type | TxnID | prevLSN | PageID | ...    │
│   (UPDATE의 경우)   | Before-Image | After-Img │
└────────────────────────────────────────────────┘
```

| Type | 용도 |
|---|---|
| **BEGIN** | 트랜잭션 시작 |
| **UPDATE** | 페이지 수정 (UNDO/REDO용 이미지 포함) |
| **COMMIT** | 트랜잭션 커밋 |
| **ABORT** | 트랜잭션 중단 시작 |
| **CLR** (Compensation Log Record) | UNDO 수행 기록 |
| **TXN-END** | 트랜잭션 완전 종료 |
| **CHECKPOINT** | 체크포인트 (TT/DPT 스냅샷) |

### 6. 3-Phase Recovery — ARIES의 심장

크래시 후 복구는 정확히 세 단계로 수행된다.

```
   Log: ─────[CKPT]─────────────────[CRASH]────▶

   Phase 1: ANALYSIS    →→→→→→→→→→→ (Forward)
            (CKPT부터 끝까지 스캔, TT/DPT 복원)

   Phase 2: REDO        →→→→→→→→→→→ (Forward)
            (RedoLSN = min(recLSN) 부터 모든 변경 재실행)

   Phase 3: UNDO        ←←←←←←←←←←← (Backward)
            (Loser 트랜잭션의 변경을 역순으로 되돌림)
```

#### Phase 1: Analysis (분석)

마지막 체크포인트에서 시작해 로그를 **순방향**으로 스캔.

- COMMIT/ABORT 발견 → TT에서 제거
- UPDATE 발견 → TT에 트랜잭션 추가, DPT에 페이지 추가 (recLSN = 해당 LSN)
- 결과물: **복원된 TT, DPT, RedoLSN** (`= min(recLSN in DPT)`)

#### Phase 2: Redo (재실행) — "Repeating History"

`RedoLSN`부터 순방향으로 모든 UPDATE/CLR을 재실행. **커밋 여부와 무관하게 모든 변경을 재적용**한다 (ARIES의 시그니처).

**REDO 스킵 조건** (셋 중 하나라도 만족하면 skip):
1. 영향받은 페이지가 DPT에 없음
2. 페이지가 DPT에 있지만 `recLSN > log.LSN` (더 오래된 변경)
3. `pageLSN ≥ log.LSN` (이미 디스크에 반영됨)

```
   for each log record L from RedoLSN forward:
       if L.type in {UPDATE, CLR}:
           page = fetch(L.pageID)
           if page.pageLSN < L.LSN:
               apply L's after-image to page
               page.pageLSN = L.LSN
```

→ 이 시점에서 DB는 **크래시 직전 상태와 동일** (미커밋 변경 포함).

#### Phase 3: Undo (취소) — Selective

Analysis 결과 TT에 남아있는 트랜잭션 = **Loser**. 이들의 변경을 **역방향**으로 되돌리며, 각 UNDO마다 **CLR을 기록**한다.

```
   ToUndo = { lastLSN of each loser txn }
   while ToUndo not empty:
       L = max(ToUndo); remove from ToUndo
       if L is CLR:
           ToUndo += { L.undoNextLSN }   # 이미 undo된 부분은 skip
       else:  # UPDATE
           write CLR(L), apply L's before-image
           ToUndo += { L.prevLSN }
```

### 7. CLR (Compensation Log Record) — UNDO의 멱등성

**복구 도중 또 크래시가 나면?** ARIES는 CLR로 해결한다.

- CLR은 UNDO 수행을 기록한 로그 (Redo-only, **never undone**).
- CLR에는 `undoNextLSN` 포인터가 있어, 다음에 undo해야 할 로그를 가리킨다.
- 복구 중 크래시 → 재복구 시 CLR이 있는 부분은 자동으로 건너뛰어진다 → **멱등성** 보장.

```
   원본 로그:       LSN10 (T1.upd P5: A→B)
                   LSN20 (T1.upd P9: X→Y)
                   LSN30 (T1.upd P5: B→C)
                   [CRASH]

   UNDO 진행:
                   LSN40 CLR(undo LSN30, undoNext=20)  ← P5: C→B
                   LSN50 CLR(undo LSN20, undoNext=10)  ← P9: Y→X
                   LSN60 CLR(undo LSN10, undoNext=NULL)← P5: B→A
                   LSN65 TXN-END(T1)
```

### 8. Fuzzy Checkpoint — 멈추지 않는 체크포인트

전통적 체크포인트는 모든 트랜잭션을 멈추고 모든 더티 페이지를 flush해야 하지만, ARIES는 **non-blocking**이다.

```
   [BEGIN_CHECKPOINT] LSN
       ... 트랜잭션은 계속 진행 ...
   [END_CHECKPOINT]   (TT, DPT 스냅샷 포함)
       ... 더티 페이지는 비동기로 flush ...

   Master Record: BEGIN_CHECKPOINT의 LSN을 가리킴
```

복구 시작점: Master Record → `BEGIN_CHECKPOINT` LSN → Analysis 시작.

### 9. 전체 흐름 한눈에

```
 ┌──────────────────────────────────────────────────────────┐
 │  정상 동작                                                │
 │  ─────────                                                │
 │  Txn ──▶ Buffer ──▶ Log Buffer ──▶ Log Disk             │
 │              │            │                              │
 │              │            └── (WAL: 먼저 flush)           │
 │              └── (lazy flush, 비동기)                     │
 │                                                          │
 │  Commit: COMMIT 로그가 디스크에 도달하면 사용자에게 응답  │
 └──────────────────────────────────────────────────────────┘
                          ↓ CRASH
 ┌──────────────────────────────────────────────────────────┐
 │  복구                                                     │
 │  ────                                                    │
 │  1. Master Record → 마지막 체크포인트 찾기                │
 │  2. ANALYSIS: TT, DPT 복원 → RedoLSN 계산                │
 │  3. REDO:     RedoLSN부터 모든 변경 재실행 (Repeat Hist) │
 │  4. UNDO:     Loser 트랜잭션 역순 취소 (CLR 기록)        │
 │  5. 새 체크포인트 → 정상 서비스 재개                      │
 └──────────────────────────────────────────────────────────┘
```

### 10. ARIES의 핵심 이점

| 이점 | 설명 |
|---|---|
| **빠른 정상 처리** | No-Force + Steal로 디스크 I/O 최소화 |
| **빠른 복구** | Fuzzy checkpoint로 ANALYSIS 범위 축소 |
| **부분 롤백** | Savepoint별로 prevLSN 체인 따라 일부만 UNDO |
| **고동시성** | Record-level locking + 짧은 latch |
| **복구 중 크래시 견딤** | CLR의 멱등성 |
| **간단한 종료** | Repeating History → 분석 로직이 단순 |

---

## 내가 얻은 인사이트

### 시스템 설계 관점

1. **"Repeating History" 라는 반직관적 결정**
   - 직관적으로는 "커밋된 것만 redo하면 되지 않나?"라고 생각하기 쉽지만, ARIES는 미커밋 변경까지 모두 재실행한 뒤 UNDO한다.
   - 이 결정의 본질은 **복구 로직을 정상 실행 로직과 동일하게 만드는 것**. 분석/예외 케이스가 적어져 코드가 단순해지고 버그가 줄어든다.
   - "복잡한 분기보다 단순한 반복"이 분산 시스템에서도 자주 통하는 원칙 (예: Raft의 log replication).

2. **CLR — 멱등성을 로그로 구현한 사례**
   - 분산 시스템에서 멱등성을 보장하는 흔한 방법은 idempotency key지만, ARIES는 **CLR이라는 로그 레코드 자체**로 "이미 수행됨"을 영구 기록한다.
   - undoNextLSN 포인터로 "어디까지 undo했는지"를 스킵 리스트처럼 따라가는 구조 → 복구 중 N번 크래시해도 동일한 결과.
   - 이 패턴은 분산 트랜잭션의 **2PC participant log**, Kafka의 transactional producer에서도 변형되어 사용됨.

3. **LSN — 단조 증가 ID의 마법**
   - pageLSN ≤ flushedLSN, recLSN, prevLSN, undoNextLSN... ARIES의 모든 정합성은 LSN 비교 하나로 결정된다.
   - 이건 분산 시스템의 Lamport timestamp, Spanner의 TrueTime, Kafka의 offset과 같은 사상.
   - **"전역 단조 ID + 비교 연산"** 은 상태 기반 시스템 설계의 가장 강력한 도구.

### 트레이드오프 관점

4. **No-Force/Steal의 비용은 "복잡한 복구 로직"으로 지불된다**
   - 정상 시 디스크 I/O를 줄이는 대가로 복구가 복잡해진다. 하지만 크래시는 드물고 정상 동작이 압도적으로 많기 때문에 **amortized 관점에서 압승**.
   - 비슷한 원리: LSM-Tree (write 최적화 → compaction 비용), Copy-on-Write (write 빠름 → GC 비용).
   - 시스템 설계에서는 **drained path vs hot path의 비용 분배**를 의식적으로 결정해야 한다.

5. **Fuzzy Checkpoint — "정확한 스냅샷"을 포기한 대가**
   - 정확한 시점 스냅샷을 만들려면 시스템을 멈춰야 한다. ARIES는 **"근사 스냅샷 + 로그로 보정"** 으로 가용성을 얻었다.
   - 이건 Cassandra의 SSTable flush, Redis의 BGSAVE, ZFS의 snapshot이 공유하는 사상.
   - **"정합성 책임을 한 곳에 몰아주기"** — 체크포인트는 부정확해도 되고, 로그가 진실의 원천.

### 실무 적용 관점

6. **PostgreSQL/MySQL/SQL Server를 운영한다면 ARIES 용어를 알아야 한다**
   - PostgreSQL의 `pg_wal`, MySQL InnoDB의 `redo log` / `undo log`, SQL Server의 `log_reuse_wait` 모두 ARIES 개념의 직접적 구현.
   - 장애 복구가 느릴 때 의심해야 할 것: 체크포인트 간격이 너무 김 → REDO 구간이 길어짐.
   - PostgreSQL의 `checkpoint_timeout`, `max_wal_size` 튜닝의 본질이 바로 이것.

7. **Log-First 사상은 현대 데이터 인프라의 공통 언어**
   - Kafka는 본질적으로 "ARIES의 로그 부분만 떼어내 분산화한 시스템"이라 볼 수 있다.
   - 이벤트 소싱 (Event Sourcing), CDC (Change Data Capture), Stream Processing 모두 "로그가 진실"이라는 ARIES적 세계관 위에 있다.
   - DB의 WAL을 직접 tail하는 도구 (Debezium, Maxwell)가 가능한 이유는 ARIES 로그의 self-describing 한 성질 덕분.

8. **부분 롤백 (Savepoint)의 우아함**
   - `SAVEPOINT s1; ... ROLLBACK TO s1;` 이 가능한 이유는 prevLSN 체인으로 트랜잭션 내부 로그가 양방향 리스트처럼 연결되어 있기 때문.
   - 같은 패턴이 Git의 reflog, 함수형 immutable 자료구조의 history에도 동일하게 나타남.
   - **"역방향 포인터를 함께 기록하는 것"** 은 복구/되돌리기가 필요한 모든 시스템의 필수 패턴.
