# SSTable and Log Structured Storage

## 출처
- **링크**: https://www.igvita.com/2012/02/06/sstable-and-log-structured-storage-leveldb/
- **사이트**: igvita.com (Ilya Grigorik)
- **추가 참고**: https://www.scylladb.com/glossary/sstable/

---

## AI 요약

### SSTable이란?

**SSTable(Sorted String Table)** 은 정렬된 키-값 쌍을 저장하는 불변(immutable) 파일 포맷입니다. Cassandra, ScyllaDB, LevelDB, RocksDB 등 다양한 데이터베이스에서 사용됩니다.

```
SSTable = Sorted String Table
         = 정렬된 문자열(키-값) 테이블
         = 디스크에 저장되는 불변 파일
```

### 핵심 특성

| 특성 | 설명 |
|------|------|
| **정렬됨 (Sorted)** | 키 기준으로 정렬되어 저장 |
| **불변 (Immutable)** | 한번 쓰면 수정 불가, 새 파일로 대체 |
| **순차 I/O 최적화** | 랜덤 I/O 대신 순차 쓰기로 고성능 |

### LSM-Tree 아키텍처

SSTable은 **Log-Structured Merge Tree (LSM-Tree)** 구조의 핵심 구성요소입니다.

```
┌─────────────────────────────────────────────────────┐
│                    Memory                           │
├─────────────────────────────────────────────────────┤
│  MemTable (Red-Black Tree / Skip List)              │
│  - 모든 쓰기가 여기로 먼저                            │
│  - 정렬된 상태 유지                                  │
│  - 일정 크기 도달 시 → Flush                         │
└─────────────────────────────────────────────────────┘
                         ↓ Flush
┌─────────────────────────────────────────────────────┐
│                     Disk                            │
├─────────────────────────────────────────────────────┤
│  SSTable Level 0: [SST] [SST] [SST]                │
│  SSTable Level 1: [  SSTable  ] [  SSTable  ]      │
│  SSTable Level 2: [      SSTable           ]       │
│                                                     │
│  → 레벨이 내려갈수록 크기 증가                        │
│  → Compaction으로 병합                              │
└─────────────────────────────────────────────────────┘
```

### SSTable 파일 구성

하나의 SSTable은 여러 파일로 구성됩니다:

| 파일 | 확장자 | 역할 |
|------|--------|------|
| **Data** | `-Data.db` | 실제 키-값 데이터 |
| **Index** | `-Index.db` | 파티션 키 → 데이터 오프셋 매핑 |
| **Summary** | `-Summary.db` | Index의 샘플링된 요약본 |
| **Bloom Filter** | `-Filter.db` | 키 존재 여부 빠른 판단 |
| **Compression Info** | `-CompressionInfo.db` | 압축 메타데이터 |
| **Statistics** | `-Statistics.db` | 통계 정보 |
| **TOC** | `-TOC.txt` | 파일 목록 (Table of Contents) |

### Write Path (쓰기 경로)

```
Client Write
    ↓
1. Commit Log 기록 (WAL - Write Ahead Log)
   - 장애 복구용
   - Append-Only로 매우 빠름
    ↓
2. MemTable에 삽입
   - 인메모리 정렬 구조 (Skip List 등)
   - 즉시 반환 → 쓰기 완료
    ↓
3. MemTable 크기 임계값 도달
    ↓
4. MemTable → SSTable Flush
   - 정렬된 상태 그대로 순차 쓰기
   - 불변 파일 생성
```

**왜 빠른가?**
```
전통적 B-Tree: 랜덤 I/O (디스크 헤드 이동 필요)
LSM/SSTable:   순차 I/O (연속 쓰기, 100배 이상 빠름)
```

### Read Path (읽기 경로)

```
Client Read (Key = "user:123")
    ↓
1. MemTable 확인
   - 있으면 즉시 반환
    ↓
2. Bloom Filter 확인 (각 SSTable마다)
   - "이 SSTable에 키가 있을 수 있는가?"
   - No → 해당 SSTable 스킵
   - Maybe → 다음 단계로
    ↓
3. Summary → Index → Data 순서로 조회
    ↓
4. 여러 SSTable에서 발견 시
   - 타임스탬프 비교 → 최신 값 반환
```

### Bloom Filter의 역할

```
Bloom Filter: 확률적 자료구조

"키가 존재하는가?"
  → NO: 100% 확신 (절대 없음)
  → YES: 아마도 (False Positive 가능)

장점: 불필요한 디스크 I/O 방지
      SSTable 10개 중 9개를 스킵할 수 있음
```

### Update와 Delete 처리

SSTable은 불변이므로 **제자리 수정(in-place update)이 불가능**합니다.

**Update 처리**:
```
기존: SSTable_old에 {key: "a", value: "1", ts: 100}
업데이트: MemTable에 {key: "a", value: "2", ts: 200} 추가
읽기 시: 타임스탬프 비교 → "2" 반환
```

**Delete 처리**:
```
삭제 요청: key = "a"
    ↓
Tombstone 마커 기록: {key: "a", tombstone: true, ts: 300}
    ↓
읽기 시: Tombstone 발견 → "없음" 반환
    ↓
Compaction 시: 실제 데이터와 함께 제거
```

### Compaction (압축/병합)

**문제**: SSTable이 계속 쌓이면
- 같은 키의 여러 버전 존재
- 삭제된 데이터(Tombstone) 잔존
- 읽기 시 여러 파일 검색 필요 → 성능 저하

**해결**: Compaction으로 병합

```
SSTable_1: {a:1, b:2, c:3}
SSTable_2: {a:5, d:4}        ← a가 업데이트됨
SSTable_3: {b:DEL}           ← b가 삭제됨
           ↓ Compaction
New_SSTable: {a:5, c:3, d:4} ← 최신 상태만 유지
```

### Compaction 전략

| 전략 | 동작 방식 | 적합한 워크로드 |
|------|----------|----------------|
| **Size-Tiered (STCS)** | 비슷한 크기의 SSTable끼리 병합 | 쓰기 중심 |
| **Leveled (LCS)** | 레벨별로 고정 크기 유지, 점진적 병합 | 읽기 중심 |
| **Time-Window (TWCS)** | 시간 윈도우별로 병합 | 시계열 데이터 |

**Size-Tiered vs Leveled**:
```
STCS: 쓰기 증폭 낮음, 공간 증폭 높음, 읽기 증폭 높음
LCS:  쓰기 증폭 높음, 공간 증폭 낮음, 읽기 증폭 낮음
```

### Write Amplification (쓰기 증폭)

LSM-Tree의 단점 중 하나:

```
사용자 쓰기: 1MB
    ↓
MemTable → SSTable (1회)
    ↓
Level 0 → Level 1 Compaction (다시 쓰기)
    ↓
Level 1 → Level 2 Compaction (다시 쓰기)
    ↓
실제 디스크 쓰기: 10-30MB (10-30x 증폭)
```

### SSTable vs B-Tree 비교

| 특성 | SSTable (LSM) | B-Tree |
|------|---------------|--------|
| **쓰기 성능** | 매우 빠름 (순차 I/O) | 느림 (랜덤 I/O) |
| **읽기 성능** | 여러 파일 검색 필요 | 단일 트리 탐색 |
| **공간 효율** | Compaction 전 비효율적 | 효율적 |
| **쓰기 증폭** | 높음 (Compaction) | 낮음 |
| **사용처** | Cassandra, RocksDB, LevelDB | MySQL, PostgreSQL |

---

## 내가 얻은 인사이트

SSTable은 "쓰기 최적화"를 위한 핵심 설계입니다. 모든 쓰기를 순차 I/O로 변환하여 HDD/SSD 모두에서 최고의 쓰기 성능을 달성합니다.

하지만 공짜 점심은 없습니다:
- **읽기 시 여러 SSTable 검색** → Bloom Filter, Index로 완화
- **공간 낭비 (여러 버전 공존)** → Compaction으로 해결
- **쓰기 증폭** → Compaction이 백그라운드에서 추가 I/O 발생

"Append-Only + 불변 파일 + 주기적 병합"이라는 LSM-Tree 패턴은 분산 시스템에서 특히 유리합니다. 불변성 덕분에 복제, 백업, 복구가 단순해지고, 순차 쓰기 덕분에 높은 처리량을 달성할 수 있습니다.

RocksDB(Facebook), LevelDB(Google), Cassandra, ScyllaDB, HBase 등 현대 데이터베이스들이 이 구조를 채택한 이유가 여기에 있습니다.
