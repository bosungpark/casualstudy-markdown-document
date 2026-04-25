# Odysseus/DFS — DBMS와 분산 파일 시스템의 통합

## 출처
- **아티클/논문**: Odysseus/DFS: Integration of DBMS and Distributed File System for Transaction Processing of Big Data
- **저자/출처**: Jun-Sung Kim, Kyu-Young Whang, Hyuk-Yoon Kwon, Il-Yeol Song (KAIST)
- **링크**: [arXiv:1406.0435](https://arxiv.org/abs/1406.0435)
- **발표**: 2014, 35 pages, 13 figures
- **기반 시스템**: KAIST에서 24년 이상 개발한 Odysseus RDBMS

---

## AI 요약

### 1. Odysseus/DFS란?

**한 줄 정의**: 관계형 DBMS(Odysseus)의 저장소를 로컬 디스크가 아닌 **분산 파일 시스템(DFS)** 으로 대체하여, **DBMS의 고수준 기능(SQL/스키마/트랜잭션)과 DFS의 확장성/신뢰성을 동시에** 얻으려는 시스템.

| 특성 | 전통 RDBMS | NoSQL (HBase 등) | Odysseus/DFS |
|------|-----------|------------------|--------------|
| 저장소 | 로컬 디스크 | 분산 파일 시스템 | **분산 파일 시스템** |
| SQL/스키마 | ✅ | ❌ (제한적) | ✅ |
| ACID 트랜잭션 | ✅ | ❌ (행 단위만) | ✅ |
| 수평 확장성 | ❌ (어려움) | ✅ | ✅ |
| 신뢰성/복제 | 별도 구현 | DFS가 제공 | **DFS가 제공** |
| 인덱싱 | 풍부함 | 제한적 | 풍부함 |

**핵심 아이디어**: "둘 중 하나를 포기"하던 기존 트레이드오프를 깨고, **DFS를 RDBMS의 스토리지 레이어로 흡수**한다.

---

### 2. 왜 이 문제가 어려운가? (배경)

빅데이터 시대에 두 가지 흐름이 경쟁하고 있었다:

```
   [전통 RDBMS]                    [NoSQL + DFS]
   ┌────────────┐                  ┌────────────┐
   │  SQL/ACID  │                  │  Scale-out │
   │  스키마    │                  │  복제/내결함│
   │  인덱스    │                  │  단순 KV   │
   └─────┬──────┘                  └─────┬──────┘
         │                               │
   ┌─────▼──────┐                  ┌─────▼──────┐
   │ Local Disk │                  │   HDFS     │
   └────────────┘                  └────────────┘

   확장성 ❌                        고수준 기능 ❌
```

- RDBMS는 **단일 노드 디스크 기반**이라 빅데이터 규모에서 막힘.
- NoSQL은 **DFS의 확장성**을 가져왔지만 SQL/조인/트랜잭션을 포기.
- → 논문은 "**DBMS 자체가 DFS를 스토리지로 직접 사용**"하는 통합 아키텍처를 제안.

---

### 3. 시스템 아키텍처

Odysseus/DFS는 **하나의 마스터 노드 + 여러 DBMS 서버 노드 + 여러 DFS 슬레이브 노드** 로 구성된다.

```
                    ┌────────────────────┐
                    │   Master Node      │
                    │ (Metadata / NameNode)│
                    └─────────┬──────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
  ┌─────▼──────┐        ┌─────▼──────┐        ┌─────▼──────┐
  │ DBMS Server│        │ DBMS Server│        │ DBMS Server│
  │   Node 1   │        │   Node 2   │  ...   │   Node N   │
  │            │        │            │        │            │
  │ ┌────────┐ │        │ ┌────────┐ │        │ ┌────────┐ │
  │ │ DBMS   │ │        │ │ DBMS   │ │        │ │ DBMS   │ │
  │ │ Server │ │        │ │ Server │ │        │ │ Server │ │
  │ ├────────┤ │        │ ├────────┤ │        │ ├────────┤ │
  │ │Meta DFS│ │        │ │Meta DFS│ │        │ │Meta DFS│ │
  │ │File Mgr│ │        │ │File Mgr│ │        │ │File Mgr│ │
  │ ├────────┤ │        │ ├────────┤ │        │ ├────────┤ │
  │ │  DFS   │ │        │ │  DFS   │ │        │ │  DFS   │ │
  │ │ Txn Mgr│ │        │ │ Txn Mgr│ │        │ │ Txn Mgr│ │
  │ ├────────┤ │        │ ├────────┤ │        │ ├────────┤ │
  │ │  DFS   │ │        │ │  DFS   │ │        │ │  DFS   │ │
  │ │ Client │ │        │ │ Client │ │        │ │ Client │ │
  │ └────┬───┘ │        │ └────┬───┘ │        │ └────┬───┘ │
  └──────┼─────┘        └──────┼─────┘        └──────┼─────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
  ┌─────▼──────┐         ┌─────▼──────┐         ┌─────▼──────┐
  │ DFS Slave  │         │ DFS Slave  │         │ DFS Slave  │
  │ (DataNode) │   ...   │ (DataNode) │   ...   │ (DataNode) │
  │ 데이터블록  │         │ 데이터블록  │         │ 데이터블록  │
  └────────────┘         └────────────┘         └────────────┘
```

**DBMS 서버 노드의 4개 컴포넌트**

| 컴포넌트 | 역할 |
|----------|------|
| **DBMS Server** | SQL 파싱, 쿼리 처리, 인덱스, 버퍼 매니저 등 전통 RDBMS 기능 |
| **Meta DFS File Manager** | DBMS의 페이지/익스텐트 단위 I/O를 DFS 파일 단위로 변환 |
| **DFS Transaction Manager** | DFS 위에서 ACID를 보장 — recovery + concurrency control |
| **DFS Client** | 실제로 DFS 슬레이브 노드와 통신해서 블록을 읽고 씀 |

---

### 4. 핵심 개념: Meta DFS File

논문의 가장 중요한 기여. **"DBMS의 페이지 추상화"와 "DFS의 파일 추상화" 사이의 미스매치**를 메우는 레이어다.

#### 4.1 왜 필요한가?

| 레이어 | 단위 | 특성 |
|--------|------|------|
| DBMS | 페이지(보통 4–16KB), 익스텐트, 테이블 | 작은 랜덤 I/O, in-place update 빈번 |
| DFS (HDFS류) | 블록(보통 64–128MB), 파일 | 대용량 순차 I/O, **append-only**, 파일 단위 복제 |

- DBMS가 페이지를 1개 갱신할 때마다 DFS 파일 1개를 만든다? → **메타데이터 폭증**, 마스터 노드 OOM.
- DBMS가 모든 데이터를 단일 거대 DFS 파일에 넣는다? → **append-only 제약** 때문에 in-place update 불가.

#### 4.2 Meta DFS File의 역할

```
   DBMS 관점                Meta DFS File              DFS 관점
   ──────────              ────────────────           ──────────
   Table A         ┌──▶  메타 매핑 정보         ──▶   /odysseus/blockA1
   ├ Page 1        │     - logical page → block      /odysseus/blockA2
   ├ Page 2  ──────┤     - 익스텐트 단위 그룹핑      /odysseus/blockA3
   ├ Page 3        │     - 페이지 위치 인덱스        ...
   └ Page N        │
                   │
   Table B  ──────┤
   ├ Page 1        │
   └ ...           └──▶  여러 페이지를 한 DFS
                          파일에 묶어 관리
```

- **여러 DBMS 페이지를 모아 하나의 DFS 파일**로 매핑 → 파일 수 폭발 방지.
- 메타 파일이 "**어느 논리적 페이지가 어느 DFS 파일의 어느 위치에 있는지**" 인덱스 역할.
- DBMS는 평소처럼 페이지 번호로 I/O를 요청하면, Meta DFS File Manager가 알아서 DFS 좌표로 번역.

---

### 5. 트랜잭션 관리 (Recovery + Concurrency Control)

DFS의 큰 약점: **append-only, immutable block**. 즉 일반적인 in-place update가 불가능하다. 그런데 RDBMS는 update가 핵심이다. 이걸 어떻게 풀었는가?

#### 5.1 Recovery 전략 (요약)

```
  Transaction Begin
       │
       ├─▶ Update Page (in-memory buffer)
       │
       ├─▶ WAL (Write-Ahead Log) → DFS 위 로그 파일에 append
       │
       ├─▶ ... 더 많은 update ...
       │
       ├─▶ Commit → 로그 force-write to DFS
       │
       └─▶ Background: dirty page를 DFS의 새 블록에 flush
                        + Meta DFS File 메타 매핑 갱신
```

- **WAL은 append-only**라 DFS와 본질적으로 잘 맞음 → 그대로 활용.
- **데이터 페이지 갱신은 immutable 특성을 우회**하기 위해, 변경된 페이지를 새 위치에 쓰고 Meta DFS File의 매핑만 바꿈 (shadow paging 스타일에 가까움).
- 장애 시 마지막 체크포인트 + WAL replay로 복구 가능.

#### 5.2 Concurrency Control

- DBMS 레벨에서 **2PL(Two-Phase Locking)** 또는 **MVCC** 등 전통 기법을 그대로 사용 가능.
- DFS는 단지 스토리지일 뿐이므로, lock manager는 DBMS 노드에 위치.
- HBase가 row-level만 보장하는 것과 달리, **다중 행/다중 테이블 트랜잭션** 가능.

---

### 6. HBase / 전통 RDBMS와의 비교

| 항목 | HBase | 전통 RDBMS (로컬 디스크) | Odysseus/DFS |
|------|-------|------------------------|--------------|
| 데이터 모델 | Wide-column KV | Relational | **Relational** |
| 트랜잭션 | Row 단위 | 멀티-스테이트먼트 ACID | **멀티-스테이트먼트 ACID** |
| 인덱스 | 제한적 (Row Key) | B-Tree, Hash 등 | **B-Tree, Hash 등** |
| 확장성 | ✅ DFS 기반 | ❌ 단일 노드 | **✅ DFS 기반** |
| 신뢰성 | DFS 복제 | 별도 백업 | **DFS 복제** |
| 트랜잭션 처리 성능 | 느림 | 매우 빠름 | **HBase보다 빠름, RDBMS와 비슷하거나 약간 느림** |

#### 성능 결과 요약

- **vs HBase**: Odysseus/DFS가 **트랜잭션 처리에서 더 빠름** — NoSQL의 행 단위 처리보다 효율적인 페이지 기반 I/O와 인덱스 활용 덕분.
- **vs Local RDBMS**: **comparable or marginally degraded** — 즉 DFS를 거치는 네트워크/메타 매핑 오버헤드가 있긴 하지만, "약간 느린 수준"에 그침.

---

### 7. 한 장 요약

```
   ┌──────────────────────────────────────────────────┐
   │  Q: RDBMS 기능을 포기하지 않고 빅데이터를 다룰 수  │
   │     있을까?                                       │
   ├──────────────────────────────────────────────────┤
   │  A: DBMS 자체의 스토리지 레이어를 DFS로 교체하자.  │
   │                                                  │
   │  핵심 발명:                                       │
   │   1) Meta DFS File                               │
   │      - DBMS 페이지와 DFS 블록 사이의 매핑 레이어   │
   │      - 파일 폭증/append-only 문제를 동시에 해결    │
   │                                                  │
   │   2) DFS Transaction Manager                     │
   │      - Shadow-paging 스타일 update                │
   │      - WAL은 DFS와 자연스럽게 정합                │
   │      - 락/MVCC는 DBMS 노드에서 처리              │
   │                                                  │
   │  결과: ACID + SQL + 수평 확장 + DFS 신뢰성 동시 확보│
   │       HBase보다 트랜잭션 처리 빠름                 │
   └──────────────────────────────────────────────────┘
```

---

## 내가 얻은 인사이트

### 아키텍처 관점

1. **레이어를 어디서 자를 것인가는 시스템 설계의 본질이다**
   - HBase는 "DFS 위에 KV 저장소"로 layer를 잘랐고, Odysseus/DFS는 "DBMS 내부의 storage manager만 DFS로 바꿈"으로 layer를 잘랐다.
   - 같은 컴포넌트 조합(DBMS + DFS)이라도 **자르는 위치에 따라 ACID 가능 여부와 인덱스 풍부도가 결정**된다.

2. **Meta File 패턴은 일반화 가능한 추상화다**
   - "작은 단위의 추상(페이지)"과 "큰 단위의 저장(블록/파일)" 사이에 인덱스 매핑 레이어를 두는 것은 LSM-Tree의 SSTable index, Iceberg/Delta Lake의 manifest, S3 위의 Parquet metadata 등에서 반복적으로 나타나는 **범용 디자인 패턴**이다.

3. **immutable storage 위에 mutable semantics를 얹는 표준 레시피**
   - WAL append + shadow page + 메타 포인터 스왑.
   - 이 패턴은 이후 Delta Lake, Iceberg, Hudi, FoundationDB 등에서도 동일한 형태로 등장 — 2014년에 이걸 RDBMS 차원에서 구현했다는 점이 인상적.

### 트레이드오프 관점

1. **"comparable or marginally degraded"의 의미**
   - DFS를 끼면 네트워크 hop, 복제 오버헤드, 메타 lookup이 추가된다. 그럼에도 로컬 RDBMS와 비슷한 성능이 나오는 이유는 **워크로드가 충분히 페이지 캐시에 담기기 때문**일 가능성이 높다.
   - 캐시 미스가 많은 워크로드(랜덤 OLTP, 매우 큰 working set)에서는 격차가 더 벌어질 것.

2. **HBase보다 빠른 이유는 "더 똑똑해서"가 아니라 "더 적게 일해서"**
   - HBase는 row 단위 RPC, MemStore→HFile flush, compaction, region split 등 무거운 일을 매번 한다.
   - Odysseus/DFS는 DBMS의 buffer pool과 페이지 단위 I/O를 그대로 쓰니까 **CPU/네트워크 cost per row가 훨씬 작다**.

### 실무 적용 관점

1. **현대 데이터 레이크하우스의 선구적 개념**
   - 2026년 시점에서 보면 Snowflake, Databricks Delta Lake, Iceberg + Trino 같은 시스템이 결국 같은 비전을 실현했다: **"분산 스토리지 위의 ACID 데이터베이스"**.
   - Odysseus/DFS의 메타 파일 개념 ≈ Iceberg의 metadata.json + manifest list.

2. **"DBMS를 처음부터 DFS-aware로 만든다" vs "기존 DBMS 위에 DFS 어댑터를 끼운다"**
   - 후자(예: PostgreSQL + S3 외부 테이블)는 쉬운 통합이지만 ACID가 외부 테이블에 적용 안 됨.
   - 전자(Odysseus/DFS, Snowflake)는 **storage manager부터 다시 설계**해야 하는 비용이 크지만, 일관된 시맨틱을 보장.
   - **시스템의 일관성은 결국 "가장 깊은 레이어부터 통합 설계됐는가"에 달려 있다.**

3. **append-only 스토리지는 제약이 아니라 기회**
   - Immutable block은 캐시·복제·읽기 일관성 측면에서 오히려 단순함을 준다.
   - in-place update를 포기하는 대신 메타 포인터 swap을 받아들이면, 분산 환경에서의 동시성 제어가 훨씬 쉬워진다 → MVCC가 자연스럽게 따라온다.

### 학습 관점

1. **"왜 이 컴포넌트가 여기 필요한가?"를 먼저 묻기**
   - Meta DFS File Manager, DFS Transaction Manager 같은 이름만 보면 "또 무슨 매니저야"가 되지만, **"DBMS 페이지 ↔ DFS 블록의 임피던스 미스매치"라는 단 하나의 문제**로 환원하면 구조가 명확해진다.
   - 분산 시스템 논문을 읽을 때는 항상 **"이 레이어가 없다면 어떤 문제가 생기나?"** 를 자문하는 게 효과적.

2. **이 논문이 사실상 HTAP의 초기 청사진**
   - 빅데이터 + 트랜잭션 = 오늘날의 HTAP / Lakehouse.
   - 2014년에 KAIST가 이 방향을 명확히 정의했다는 점에서, 한국 DB 연구의 흐름을 이해하는 좋은 출발점.

---

## Sources

- [Odysseus/DFS arXiv 1406.0435](https://arxiv.org/abs/1406.0435)
- [ADS Abstract](https://ui.adsabs.harvard.edu/abs/2014arXiv1406.0435K/abstract)
- [ResearchGate Publication](https://www.researchgate.net/publication/262805718_OdysseusDFS_Integration_of_DBMS_and_Distributed_File_System_for_Transaction_Processing_of_Big_Data)
- [Internet Archive Mirror](https://archive.org/details/arxiv-1406.0435)
- [PARADISE: Big data analytics using the DBMS tightly integrated with the DFS (후속 논문)](https://link.springer.com/article/10.1007/s11280-014-0312-2)
