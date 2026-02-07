# Database Pages and Blocks Fundamentals

## 출처
- **아티클/논문**: Understanding Database Pages, PostgreSQL Internals: Understanding Page Structure, Pages and Extents Architecture Guide
- **저자/출처**: Adam Djellouli, Stormatics, Microsoft Learn
- **링크**:
  - https://adamdjellouli.com/articles/databases_notes/05_storage_and_indexing/04_database_pages
  - https://stormatics.tech/blogs/postgresql-internals-part-2-understanding-page-structure
  - https://learn.microsoft.com/en-us/sql/relational-databases/pages-and-extents-architecture-guide

---

## AI 요약

### 1. Database Page란?

**Database Page**는 디스크와 메모리 간 데이터 전송의 기본 단위가 되는 고정 길이 저장 블록이다. 데이터베이스는 개별 레코드가 아닌 페이지 단위로 I/O 작업을 수행하여 디스크 접근을 최적화한다.

| 특성 | 설명 |
|------|------|
| 기본 단위 | 디스크 I/O의 최소 단위 |
| 고정 크기 | 2KB ~ 64KB (일반적으로 4KB, 8KB, 16KB) |
| 구성 요소 | 헤더 + 데이터 레코드 + 빈 공간 |
| 목적 | 효율적인 디스크 I/O 및 메모리 관리 |

> **Page vs Block**: 일부 데이터베이스에서는 "page"와 "block"을 동의어로 사용하고, 다른 시스템에서는 구분된 개념으로 취급한다. 본 문서에서는 "page"를 기준으로 설명한다.

---

### 2. 페이지 구조 (Page Structure)

#### 일반적인 페이지 레이아웃

```
┌─────────────────────────────────────────┐
│              Page Header                │  ← 메타데이터 (96 bytes in SQL Server)
│   (페이지 번호, 타입, 객체 ID 등)         │
├─────────────────────────────────────────┤
│                                         │
│              Row 1                      │  ↓ 아래 방향으로 증가
│              Row 2                      │
│              Row 3                      │
│               ...                       │
│                                         │
│         [ Free Space ]                  │  ← 가용 공간
│                                         │
├─────────────────────────────────────────┤
│         Slot Array [3]                  │  ↑ 위 방향으로 증가
│         Slot Array [2]                  │
│         Slot Array [1]                  │
└─────────────────────────────────────────┘
```

**핵심 개념: Dual-Growth 패턴**
- 데이터 레코드: 헤더 다음부터 **아래 방향**으로 증가
- 슬롯 배열: 페이지 끝에서 **위 방향**으로 증가
- 두 영역이 중간에서 만나는 구조

---

### 3. Page Header 상세

#### PostgreSQL Page Header (24 bytes)

| 필드 | 크기 | 설명 |
|------|------|------|
| `pd_lsn` | 8 bytes | Log Sequence Number - 마지막 변경 WAL 위치 |
| `pd_checksum` | 2 bytes | 페이지 무결성 검증용 체크섬 |
| `pd_flags` | 2 bytes | 상태 플래그 (PD_HAS_FREE_LINES, PD_PAGE_FULL) |
| `pd_lower` | 2 bytes | Line pointer 배열의 끝 위치 |
| `pd_upper` | 2 bytes | 가장 최근 힙 튜플의 시작 위치 |
| `pd_special` | 2 bytes | 인덱스 전용 메타데이터 포인터 |
| `pd_pagesize_version` | 2 bytes | 페이지 크기 및 버전 (PostgreSQL 8.3+: 버전 4) |
| `pd_prune_xid` | 4 bytes | 가장 오래된 미정리 트랜잭션 ID |

#### SQL Server Page Header (96 bytes)

| 필드 | 설명 |
|------|------|
| Page Number | 파일 내 페이지 번호 |
| Page Type | 페이지 유형 (Data, Index, Text/LOB 등) |
| Object ID | 소속 객체 식별자 |
| Index ID | 인덱스 식별자 |
| 기타 메타데이터 | 관리용 시스템 정보 |

---

### 4. Row/Tuple 저장 방식

#### Line Pointer (Item Pointer)

PostgreSQL에서 각 튜플은 **Line Pointer**를 통해 참조된다:

```
┌──────────────────────────────────────────────────┐
│                   Page Header                    │
├──────────────────────────────────────────────────┤
│  LP1  │  LP2  │  LP3  │  ...  │     (4 bytes each)
├──────────────────────────────────────────────────┤
│                                                  │
│                  Free Space                      │
│                                                  │
├──────────────────────────────────────────────────┤
│                   Tuple 3                        │
├──────────────────────────────────────────────────┤
│                   Tuple 2                        │
├──────────────────────────────────────────────────┤
│                   Tuple 1                        │
└──────────────────────────────────────────────────┘
```

- **Line Pointer**: 4 bytes - 튜플의 오프셋과 길이 저장
- **Slot Array** (SQL Server): 2 bytes - 행의 바이트 오프셋 저장

#### Row Size 제한

| DBMS | 최대 Row 크기 | 비고 |
|------|--------------|------|
| SQL Server | 8,060 bytes | 8,192 - 96(헤더) - 슬롯 배열 |
| PostgreSQL | ~2KB (TOAST 전) | 페이지의 1/4 이상 시 TOAST 적용 |
| MySQL (InnoDB) | ~8,000 bytes | 페이지 크기에 따라 변동 |

---

### 5. 페이지 크기 선택 (Page Size Trade-offs)

```
작은 페이지 (4KB)                    큰 페이지 (16KB+)
      │                                    │
      ▼                                    ▼
┌─────────────┐                    ┌─────────────┐
│ ✓ 메모리 효율적 │                    │ ✓ 순차 읽기 효율 │
│ ✓ 랜덤 액세스 유리│                    │ ✓ I/O 횟수 감소 │
│ ✗ I/O 횟수 증가 │                    │ ✗ 메모리 소비 증가│
│ ✗ 대용량 처리 불리│                    │ ✗ 공간 낭비 가능 │
└─────────────┘                    └─────────────┘
```

| 페이지 크기 | 장점 | 단점 | 적합한 워크로드 |
|------------|------|------|----------------|
| 4KB | 메모리 효율, 랜덤 액세스 | I/O 횟수 증가 | OLTP, 소규모 레코드 |
| 8KB | 균형잡힌 선택 | - | 범용 |
| 16KB+ | 순차 읽기 효율, I/O 감소 | 메모리 소비 | OLAP, 대용량 레코드 |

---

### 6. 페이지 타입 (Page Types)

#### SQL Server 페이지 타입

| 타입 | 목적 |
|------|------|
| **Data** | 실제 데이터 행 저장 |
| **Index** | B-tree 인덱스 구조 |
| **Text/LOB** | 대용량 객체 (varchar(max), varbinary(max), xml 등) |
| **GAM** | Global Allocation Map - 할당된/미할당 익스텐트 추적 |
| **SGAM** | Shared GAM - 빈 페이지가 있는 혼합 익스텐트 추적 |
| **PFS** | Page Free Space - 페이지별 여유 공간 정보 |
| **IAM** | Index Allocation Map - 힙/인덱스가 사용하는 익스텐트 |
| **DCM** | Differential Changed Map - 마지막 전체 백업 이후 변경 익스텐트 |
| **BCM** | Bulk Changed Map - 대량 작업으로 변경된 익스텐트 |

---

### 7. Extent와 할당 (Extents and Allocation)

#### Extent 개념 (SQL Server)

```
                    Extent (64 KB)
    ┌───────────────────────────────────────────┐
    │ Page │ Page │ Page │ Page │ Page │ Page │ Page │ Page │
    │  0   │  1   │  2   │  3   │  4   │  5   │  6   │  7   │
    └───────────────────────────────────────────┘
         8개의 연속된 페이지 (8 × 8KB = 64KB)
```

#### Extent 유형

| 유형 | 소유자 | 사용 시점 |
|------|--------|----------|
| **Uniform Extent** | 단일 객체 | 8페이지 초과 시 |
| **Mixed Extent** | 최대 8개 객체 공유 | 초기 할당 (작은 테이블) |

#### GAM/SGAM 비트 해석

| 익스텐트 상태 | GAM 비트 | SGAM 비트 |
|--------------|----------|-----------|
| 미할당 (Free) | 1 | 0 |
| Uniform 또는 가득 찬 Mixed | 0 | 0 |
| 빈 페이지가 있는 Mixed | 0 | 1 |

---

### 8. Row Overflow와 대용량 데이터

#### Row Overflow 처리 (SQL Server)

```
일반 데이터 페이지                    Row Overflow 페이지
┌─────────────────────┐              ┌─────────────────────┐
│    Page Header      │              │    Page Header      │
├─────────────────────┤              ├─────────────────────┤
│  Row 1 (일반)       │              │                     │
│  Row 2 (일반)       │              │  오버플로우된       │
│  Row 3:             │──24-byte──→ │  varchar 데이터     │
│   [고정 컬럼]       │   pointer    │                     │
│   [24-byte 포인터]  │              │                     │
└─────────────────────┘              └─────────────────────┘
```

- 행 크기가 8,060 bytes 초과 시 가장 큰 가변 길이 컬럼부터 분리
- 원본 페이지에는 **24-byte 포인터** 유지
- LOB 데이터는 **16-byte 포인터**로 별도 페이지 트리 참조

#### PostgreSQL TOAST (The Oversized-Attribute Storage Technique)

대용량 속성을 별도 TOAST 테이블에 저장:
- 압축 후 저장
- 필요시 조각으로 분할
- 메인 테이블에는 포인터만 유지

---

### 9. Page Split과 단편화 (Fragmentation)

#### Page Split 발생 조건

```
Before Split:                      After Split:
┌─────────────────┐               ┌─────────────────┐  ┌─────────────────┐
│    FULL PAGE    │               │   Page A        │  │   Page B        │
│  [Row 1]        │               │  [Row 1]        │  │  [Row 3]        │
│  [Row 2]        │    ───→       │  [Row 2]        │  │  [Row 5 - NEW]  │
│  [Row 3]        │               │  [Row 4]        │  │                 │
│  [Row 4]        │               │                 │  │                 │
│  No Space!      │               └─────────────────┘  └─────────────────┘
└─────────────────┘
```

#### 단편화 영향
- 관련 레코드가 비연속 페이지에 분산
- I/O 작업 증가
- 캐시 효율성 저하
- 순차 스캔 성능 저하

#### 완화 전략

| 전략 | 설명 | 예시 |
|------|------|------|
| **Fill Factor** | 페이지에 여유 공간 예약 | 70%로 설정 시 30% 공간 예약 |
| **인덱스 재구성** | 단편화된 인덱스 정리 | `ALTER INDEX ... REBUILD` |
| **적절한 인덱스 설계** | 삽입 패턴 고려한 키 선택 | UUID 대신 순차 ID 사용 |

---

### 10. Fill Factor 설정

```sql
-- PostgreSQL: 테이블 생성 시 설정
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INT,
    amount DECIMAL
) WITH (FILLFACTOR = 70);

-- PostgreSQL: 기존 테이블 변경
ALTER TABLE orders SET (FILLFACTOR = 70);

-- SQL Server: 인덱스 생성 시 설정
CREATE INDEX idx_orders_customer
ON orders(customer_id)
WITH (FILLFACTOR = 80);
```

| Fill Factor | 용도 | 트레이드오프 |
|-------------|------|-------------|
| 100% (기본값) | 읽기 전용 테이블 | 저장 공간 최적화, 업데이트 시 분할 발생 |
| 70-80% | 업데이트 빈번한 테이블 | 분할 감소, 저장 공간 증가 |
| 50-60% | 매우 빈번한 업데이트 | I/O 오버헤드 감소, 저장 공간 크게 증가 |

---

### 11. 페이지 검사 및 모니터링

#### PostgreSQL - pageinspect 확장

```sql
-- 확장 설치
CREATE EXTENSION pageinspect;

-- 페이지 헤더 조회
SELECT * FROM page_header(get_raw_page('my_table', 0));

-- 테이블의 페이지 수 확인
SELECT relname AS table_name,
       relpages AS table_pages,
       pg_size_pretty(relpages * 8192) AS size
FROM pg_class
WHERE relname = 'my_table';
```

#### SQL Server - DMV 활용

```sql
-- 페이지 정보 조회 (SQL Server 2019+)
SELECT * FROM sys.dm_db_page_info(DB_ID(), 1, 0, 'DETAILED');

-- 인덱스 물리적 통계 (단편화 포함)
SELECT
    OBJECT_NAME(object_id) AS table_name,
    index_id,
    avg_fragmentation_in_percent,
    page_count
FROM sys.dm_db_index_physical_stats(
    DB_ID(), NULL, NULL, NULL, 'LIMITED'
);

-- Row Overflow 데이터 감지
SELECT * FROM sys.dm_db_index_physical_stats(
    DB_ID(), OBJECT_ID('my_table'), NULL, NULL, 'DETAILED'
)
WHERE alloc_unit_type_desc = 'ROW_OVERFLOW_DATA';
```

---

### 12. Storage Model과 페이지

| Storage Model | 페이지 내 데이터 배치 | 적합한 워크로드 |
|---------------|----------------------|----------------|
| **Row-Based (NSM)** | 전체 레코드가 인접 저장 | OLTP, 트랜잭션 처리 |
| **Column-Based (DSM)** | 같은 컬럼 값들이 인접 저장 | OLAP, 분석 쿼리 |
| **Hybrid (PAX)** | 페이지 내에서 컬럼 그룹화 | 혼합 워크로드 |

```
Row-Based (NSM):                    Column-Based (DSM):
┌────────────────────┐              ┌────────────────────┐
│ ID│Name│Age│Salary│              │ ID │ ID │ ID │ ID │
├───┴────┴───┴──────┤              ├────┴────┴────┴────┤
│ 1 │John│ 30│ 5000 │              │Name│Name│Name│Name│
│ 2 │Jane│ 25│ 6000 │              ├────┴────┴────┴────┤
│ 3 │Bob │ 35│ 5500 │              │ Age│ Age│ Age│Age │
└────────────────────┘              └────────────────────┘
```

---

## 내가 얻은 인사이트

### 성능 관점

1. **I/O가 진정한 병목**
   - 데이터베이스 성능의 핵심은 디스크 I/O 최소화
   - 페이지는 이 I/O를 효율화하기 위한 기본 단위
   - 단일 레코드 조회도 최소 1개 페이지(8KB) 읽기 필요

2. **Dual-Growth 패턴의 우아함**
   - 데이터와 슬롯 배열이 반대 방향으로 증가
   - 삭제된 공간을 자연스럽게 재활용 가능
   - 추가 메타데이터 없이 가용 공간 계산 가능 (upper - lower)

3. **Fill Factor는 예방 의학**
   - Page Split은 비용이 큰 작업 (I/O, 잠금, 단편화)
   - 미리 여유 공간을 확보하면 분할 빈도 감소
   - 저장 공간 vs 성능의 명확한 트레이드오프

### 설계 관점

1. **Row 크기 설계의 중요성**
   - 8,060 bytes 제한은 실제 설계에 영향
   - 불필요하게 큰 varchar 정의 피하기
   - LOB 컬럼은 별도 I/O 발생 고려

2. **Sequential vs Random Access**
   - 페이지 크기 선택은 액세스 패턴에 따라 결정
   - 분석 쿼리: 큰 페이지로 순차 스캔 효율화
   - OLTP: 작은 페이지로 메모리 효율 및 잠금 범위 최소화

3. **Extent 단위 할당의 이유**
   - 연속된 8페이지를 함께 할당하여 물리적 연속성 확보
   - 순차 스캔 시 프리페칭 효율 극대화
   - 작은 테이블은 Mixed Extent로 공간 낭비 방지

### 운영 관점

1. **모니터링의 필수 지표**
   - 단편화 비율 (avg_fragmentation_in_percent)
   - Page Split 빈도
   - Row Overflow 발생 여부

2. **GAM/SGAM/PFS의 역할 이해**
   - 공간 할당을 위한 시스템 페이지
   - 병목 지점이 될 수 있음 (할당 핫스팟)
   - tempdb에서 특히 중요한 고려사항
