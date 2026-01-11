# Benchmarking Cloud Serving Systems with YCSB

## 출처
- **링크**: https://research.cs.wisc.edu/wind/Publications/ycsb-socc10.pdf
- **저자**: Brian F. Cooper, Adam Silberstein, Erwin Tam, Raghu Ramakrishnan, Russell Sears (Yahoo! Research)
- **학회**: SoCC (ACM Symposium on Cloud Computing) 2010

---

## AI 요약

### 논문의 배경과 동기

**2010년 당시의 문제**:
- NoSQL 시스템 폭발적 증가: Cassandra, HBase, PNUTS, MongoDB, Voldemort, CouchDB 등
- 각 시스템마다 성능 특성이 다르지만 **공정한 비교 불가능**
- 개발자들이 8개 시스템을 직접 설치/테스트해야 했던 사례 (Digg 사례)
- 전통적 DB 벤치마크(TPC-C 등)는 NoSQL에 부적합

**YCSB의 목표**:
> "클라우드 서빙 시스템을 위한 표준 벤치마크 프레임워크 제공"

---

### YCSB의 핵심 구성

**1. 벤치마크 계층 (Benchmark Tiers)**

```
Tier 1: Performance (성능)
- 부하 증가에 따른 레이턴시/처리량 측정
- Latency vs Throughput 곡선

Tier 2: Scaling (확장성)
- Scaleup: 서버 증가 시 성능 유지 여부
- Elastic Speedup: 운영 중 서버 추가 시 성능 향상

Tier 3: Availability (가용성) - 제안만
Tier 4: Replication (복제) - 제안만
```

**2. 워크로드 패키지 (Core Workloads)**

| 워크로드 | 작업 비율 | 레코드 선택 | 실제 사례 |
|----------|-----------|-------------|-----------|
| **A (Update heavy)** | Read 50% / Update 50% | Zipfian | 세션 스토어 |
| **B (Read heavy)** | Read 95% / Update 5% | Zipfian | 사진 태깅 |
| **C (Read only)** | Read 100% | Zipfian | 사용자 프로필 캐시 |
| **D (Read latest)** | Read 95% / Insert 5% | Latest | 사용자 상태 업데이트 |
| **E (Short ranges)** | Scan 95% / Insert 5% | Zipfian/Uniform | 스레드 대화 |

**데이터셋 구조**:
- 레코드: 1KB (10개 필드 × 100바이트)
- 총 데이터: 120GB (1억 2천만 레코드)
- 키: `user234123` 형태의 문자열

**3. YCSB Client 아키텍처**

```
┌─────────────────────────────────────┐
│   Workload Executor                 │
│   (CoreWorkload or Custom)          │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │  Threads      │ (부하 생성)
       │  (1~500개)    │
       └───────┬───────┘
               │
┌──────────────┴──────────────────────┐
│   Database Interface Layer          │
│   (Cassandra/HBase/PNUTS/MySQL)     │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       │  DB System    │
       └───────────────┘
```

**확장 방식**:
- 새 DB 추가: `read()`, `insert()`, `update()`, `delete()`, `scan()` 구현
- 새 워크로드 추가: 파라미터 파일 작성 or Java 코드 작성

---

### 핵심 실험 결과 (2010년 기준)

**테스트 환경**:
- 서버 6대: Dual quad-core 2.5GHz Xeon, 8GB RAM, RAID-10
- 데이터: 서버당 20GB (총 120GB)
- 클라이언트: 별도 8코어 머신, 최대 500 스레드

**주요 발견**:

**1. Read vs Write 트레이드오프 (Workload A - 50/50)**

| 시스템 | 최대 처리량 | Read 레이턴시 | Update 레이턴시 | 특징 |
|--------|-------------|---------------|-----------------|------|
| Cassandra | 11,978 ops/s | 높음 | **매우 낮음** | Write 최적화 |
| HBase | 7,904 ops/s | 높음 | **극도로 낮음** | 메모리 버퍼링 |
| PNUTS | 7,448 ops/s | **낮음** | 중간 | Read 최적화 |
| MySQL | 7,283 ops/s | **낮음** | 중간 | 전통적 방식 |

**왜 이런 차이가?**
```
Cassandra/HBase (Write 최적화):
- 업데이트를 디스크에 순차 쓰기 (Log-Structured)
- 읽기 시 여러 조각 병합 필요 → 느림
- 쓰기는 극도로 빠름

PNUTS/MySQL (Read 최적화):
- 업데이트 시 레코드 덮어쓰기 (In-place Update)
- 읽기 시 1번 I/O로 완전한 레코드 조회
- 쓰기는 랜덤 I/O 필요 → 느림
```

**2. Read Heavy 워크로드 (Workload B - 95% Read)**

```
결과 역전!
- PNUTS/MySQL: Read 레이턴시 5-10ms (최고)
- Cassandra: Read 레이턴시 20-40ms
- HBase: 레이턴시 변동 심함 (파편화 영향)
```

**HBase의 특이점**:
- 메모리 플러시로 생성된 파일 수에 따라 성능 급변
- 파편화 심할 때: 4,800 ops/s
- 컴팩션 후: 8,000+ ops/s

**3. 스캔 성능 (Workload E)**

| 시스템 | 짧은 스캔 (25개) | 긴 스캔 (800개) |
|--------|------------------|-----------------|
| HBase | 1,519 ops/s | **3.5배 빠름** |
| PNUTS | 1,440 ops/s | 느림 |
| Cassandra | **매우 느림** | 매우 느림 |

**이유**:
- HBase: 디스크에 데이터 조밀하게 저장 (Sequential Read 유리)
- PNUTS: B-Tree 사용 → 빈 공간 때문에 긴 스캔 비효율
- Cassandra: 0.5.0 버전에서 Range Scan 최적화 부족

**4. Scalability (확장성)**

```
서버 2대 → 12대 증가 시:

✓ PNUTS: 레이턴시 거의 일정 (완벽한 스케일업)
✓ Cassandra: 레이턴시 거의 일정
✗ HBase: 성능 들쭉날쭉 (3대 미만에서 특히 불안정)
```

**5. Elastic Speedup (운영 중 서버 추가)**

**Cassandra**:
```
서버 추가 시:
- 레이턴시 급증 (100ms → 700ms)
- 데이터 재분배 중 5.5시간 동안 불안정
- 완료 후: 정상 성능 회복
→ 알려진 이슈, 0.6.0에서 개선 중
```

**HBase**:
```
서버 추가 시:
- 레이턴시 일시 증가 후 안정화
- 기존 데이터는 이동 안 함 (컴팩션 시에만)
- 새 서버 활용도 낮음
```

**PNUTS**:
```
서버 추가 시:
- 레이턴시 증가하나 80분 내 안정화
- 가장 빠른 재분배
- 안정화 후 성능 우수
```

---

### 시스템별 설계 결정 비교

| 시스템 | Read/Write 최적화 | 내구성 | 복제 방식 | 저장 구조 |
|--------|-------------------|--------|-----------|-----------|
| **PNUTS** | Read | Durable (fsync) | Async | Row |
| **BigTable** | Write | Durable | Sync | Column |
| **HBase** | Write | Latency 우선 | Async | Column |
| **Cassandra** | Write | 조정 가능 | 조정 가능 | Column |
| **MySQL** | Read | Durable | Async | Row |

---

### 분산 분포 (Distribution) 구현의 어려움

**논문에서 가장 흥미로운 부분**:

**문제 1: Zipfian 분포의 클러스터링**
```python
# Gray et al. 알고리즘 그대로 사용하면:
- 인기 아이템이 0, 1, 2, ... 순서로 배치
- 실제로는 인기 아이템이 키스페이스 전체에 분산되어야 함

# 해결: 해싱
item = zipfian_generator.next()
key = hash(item)  # FNV 해시 사용

# 문제: 충돌로 20%만 생성됨!
# 최종 해결:
- 훨씬 큰 키스페이스 생성 (10배) -> ..? ㅋㅋㅋㅋㅋ
- FNV 해시 적용
- mod N으로 축소
→ 99.97% 키스페이스 활용, Zipfian 분포 유지
```

**문제 2: Latest 분포의 동적 변화**
```python
# 새 레코드 삽입 시:
- Latest: 인기도가 새 레코드로 이동 (재계산 필요)
- Zipfian: 기존 인기 아이템 유지 (미리 계산)

# 해결:
- Gray 알고리즘 수정하여 증분 계산 가능하게 변경
- 삽입마다 상수 재계산 (O(1))
```

---

## 내가 얻은 인사이트

하나의 시스템이 모든 워크로드에 최적일 수 없다. 각 시스템은 특정 워크로드에 최적화되어 있으며, **표준화된 벤치마크로 트레이드오프를 명확히 이해**해야 한다.
