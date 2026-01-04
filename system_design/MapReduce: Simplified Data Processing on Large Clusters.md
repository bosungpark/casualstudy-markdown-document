# MapReduce: Simplified Data Processing on Large Clusters

## 출처
- **논문**: "MapReduce: Simplified Data Processing on Large Clusters"
- **저자**: Jeffrey Dean, Sanjay Ghemawat (Google)
- **발표**: OSDI 2004 (6th Symposium on Operating Systems Design & Implementation)
- **원문**: https://static.googleusercontent.com/media/research.google.com/en//archive/mapreduce-osdi04.pdf

---

## AI 요약

대규모 데이터 처리를 위한 **프로그래밍 모델과 런타임 시스템**을 제안한 논문. Lisp의 `map`과 `reduce` 연산에서 영감을 받아, 분산 처리의 복잡성을 숨기고 개발자가 비즈니스 로직에만 집중할 수 있게 함.

### 배경: 왜 MapReduce가 필요했나?

Google에서 겪은 문제:
- 크롤링된 문서, 웹 로그 등 **대용량 데이터** 처리 필요
- 역색인(inverted index), 페이지랭크 등 다양한 계산
- 수백~수천 대 머신에 분산 필요
- **문제**: 병렬화, 데이터 분배, 장애 처리 코드가 비즈니스 로직을 압도

```
원래 코드:  비즈니스 로직 20% + 분산 처리 코드 80%
MapReduce: 비즈니스 로직 100% (분산 처리는 라이브러리가 처리)
```

---

## 프로그래밍 모델

### 핵심 개념

```
Input (k1, v1) → MAP → (k2, v2)* → SHUFFLE → (k2, [v2]) → REDUCE → (k2, v3)*
```

| 함수 | 입력 | 출력 |
|------|------|------|
| **Map** | (k1, v1) | list(k2, v2) |
| **Reduce** | (k2, list(v2)) | list(v2) |

### 예제 1: Word Count

```python
def map(key, value):
    # key: 문서 이름
    # value: 문서 내용
    for word in value.split():
        emit_intermediate(word, "1")

def reduce(key, values):
    # key: 단어
    # values: ["1", "1", "1", ...]
    result = 0
    for v in values:
        result += int(v)
    emit(str(result))
```

**실행 흐름**:
```
문서1: "hello world"  →  Map  →  (hello, 1), (world, 1)
문서2: "hello foo"    →  Map  →  (hello, 1), (foo, 1)
                            ↓ Shuffle (같은 키 그룹화)
                      (hello, [1, 1]) → Reduce → (hello, 2)
                      (world, [1])    → Reduce → (world, 1)
                      (foo, [1])      → Reduce → (foo, 1)
```

### 예제 2: 다양한 응용

| 응용 | Map 출력 | Reduce 연산 |
|------|----------|-------------|
| **URL 접근 빈도** | (URL, 1) | sum |
| **역색인** | (word, docID) | list |
| **Reverse Web-Link** | (target, source) | list |
| **Term Vector per Host** | (hostname, term_vector) | sum vectors |
| **Inverted Index** | (word, (docID, positions)) | merge |
| **Distributed Sort** | (key, record) | identity |

---

## 실행 아키텍처

### 전체 흐름

```
                    ┌─────────────────────────────────────────────────┐
                    │                    Master                       │
                    │  - Task 할당 (Map M개, Reduce R개)                │
                    │  - Worker 상태 추적                              │
                    │  - 중간 파일 위치 전파                            │
                    └─────────────────────────────────────────────────┘
                           │ (2) assign              │ (2) assign
                           ▼                         ▼
┌──────────┐    (3)    ┌────────────┐           ┌────────────┐
│  Input   │ ───────── │ Map Worker │           │ Reduce     │
│  Splits  │   read    │            │           │ Worker     │
│(GFS, 64MB)│          │ (4) write  │           │            │
└──────────┘           │ to local   │           │ (6) write  │
                       │ disk       │           │ to GFS     │
                       └────────────┘           └────────────┘
                              │                       ▲
                              │ (5) remote read       │
                              └───────────────────────┘
```

### 단계별 설명

| 단계 | 설명 |
|------|------|
| **(1)** | 입력을 M개 split (16-64MB)으로 분할, 프로그램을 모든 머신에 복사 |
| **(2)** | Master가 idle worker에게 Map 또는 Reduce task 할당 |
| **(3)** | Map worker가 입력 split 읽어서 key/value 파싱 후 Map 함수 호출 |
| **(4)** | 중간 결과를 메모리에 버퍼링 → 주기적으로 로컬 디스크에 R개 파티션으로 저장 |
| **(5)** | Reduce worker가 Map worker의 로컬 디스크에서 RPC로 데이터 읽기 |
| **(6)** | Reduce worker가 키 정렬 후 Reduce 함수 호출 → GFS에 최종 출력 |

---

## 장애 처리 (Fault Tolerance)

### Worker 장애

```
Master ──ping──> Worker (주기적)
         │
         ├── 응답 없음 → Worker를 failed로 표시
         │
         ├── 완료된 Map task → idle로 리셋 (재실행 필요)
         │   (출력이 로컬 디스크에 있어서 접근 불가)
         │
         ├── 완료된 Reduce task → 재실행 불필요
         │   (출력이 GFS에 있음)
         │
         └── 진행 중 task → idle로 리셋 (재스케줄링)
```

**실제 사례**: 네트워크 유지보수 중 80대 머신이 수 분간 unreachable
→ Master가 자동으로 재실행 → MapReduce 작업 정상 완료

### 결정적 함수의 의미론

Map/Reduce가 **결정적(deterministic)** 함수인 경우:
- 분산 실행 결과 = 순차 실행 결과 (동일 보장)

비결정적 함수인 경우:
- 약간 더 약한 의미론 (각 Reduce의 출력은 어떤 순차 실행의 결과와 동일)

### Atomic Commit

```python
# Map task 완료 시
worker → master: "Map task 완료, 중간 파일 R개 위치는 ..."
master: 이미 완료된 task면 무시, 아니면 기록

# Reduce task 완료 시  
reduce_worker: 임시 파일 → 최종 파일로 atomic rename
# 동일 task가 여러 머신에서 실행되어도 rename은 atomic
```

---

## 최적화 기법

### 1. Locality (데이터 지역성)

```
네트워크 대역폭 = 희소 자원

GFS: 파일을 64MB 블록으로 나눠 3개 복제본 저장

Master 스케줄링 우선순위:
1순위: 입력 데이터가 있는 머신에 Map task 할당
2순위: 같은 네트워크 스위치의 머신에 할당
3순위: 아무 머신

결과: 대부분의 입력 데이터를 로컬에서 읽음 → 네트워크 부하 최소화
```

### 2. Task Granularity (작업 세분화)

```
M (Map tasks) >> 머신 수
R (Reduce tasks) >> 머신 수

장점:
- 동적 로드 밸런싱 향상
- 장애 복구 가속화 (작은 task들이 여러 머신에 분산)

실제 설정:
- M = 200,000
- R = 5,000  
- Workers = 2,000
```

### 3. Backup Tasks (Straggler 대응)

**문제**: Straggler - 비정상적으로 느린 머신
- 디스크 오류 (30MB/s → 1MB/s)
- 다른 작업과 CPU/메모리/네트워크 경쟁
- 캐시 비활성화 버그 (100배 느려짐!)

**해결책**:
```
MapReduce 완료 임박 시:
- 남은 in-progress task들의 backup 실행 시작
- Primary 또는 Backup 중 먼저 끝나는 것 사용
- 리소스 오버헤드: 수 %

효과: Sort 작업에서 44% 시간 단축
```

### 4. Combiner 함수

네트워크 전송 전에 Map worker에서 부분 집계:

```python
# Combiner 없이
Map1 → (the, 1), (the, 1), (the, 1), (a, 1), (a, 1)  → 네트워크 전송

# Combiner 사용
Map1 → Combiner → (the, 3), (a, 2)  → 네트워크 전송 (데이터 감소!)
```

Word Count에서 Combiner = Reduce 함수와 동일

### 5. Partitioning 함수

기본: `hash(key) mod R`

커스텀 예시:
```python
# URL을 호스트별로 그룹화
def partition(key, R):
    return hash(get_host(key)) % R
```

---

## 성능 측정

### 테스트 환경
- 약 1,800대 머신
- 각 머신: 2×2GHz Xeon, 4GB RAM, 2×160GB IDE 디스크, Gigabit Ethernet

### Grep (1TB에서 패턴 검색)

```
입력: 10^10 × 100byte 레코드 (1TB)
패턴: 3글자 (92,337개 매칭)
M = 15,000, R = 1

결과:
- 피크 처리량: 30+ GB/s (1,764 workers 할당 시)
- 총 시간: 약 150초 (시작 오버헤드 1분 포함)
```

### Sort (1TB 정렬)

```
입력: 10^10 × 100byte 레코드 (1TB)
M = 15,000, R = 4,000
출력: 2TB (2-way 복제)

결과:
- 입력 읽기: 피크 13 GB/s
- Shuffle: 입력보다 낮음 (네트워크 제한)
- 출력 쓰기: Shuffle보다 낮음 (2x 복제 때문)
- 총 시간: 약 900초
```

### Backup Task 효과

| 설정 | Sort 시간 |
|------|-----------|
| Backup task 활성화 | 891초 |
| Backup task 비활성화 | 1,283초 (+44%) |

---

## Google 내부 사용 통계

### 성장 추이

| 시기 | MapReduce 프로그램 수 |
|------|----------------------|
| 2003년 초 | 0 |
| 2004년 9월 | ~900 |
| 2006년 3월 | ~4,000 |

### 월별 통계 (2007년 9월)

| 지표 | 값 |
|------|-----|
| 작업 수 | 2,217,000 |
| 평균 완료 시간 | 395초 |
| 사용 머신-년 | 11,081 |
| Map 입력 | 403 PB |
| Map 출력 | 35 PB |
| Reduce 출력 | 14 PB |
| 평균 머신/작업 | 394 |

### 적용 분야

- 대규모 기계 학습
- Google News, Froogle 클러스터링
- Google Zeitgeist, Trends (인기 검색어)
- 웹 페이지 속성 추출 (지역 정보 등)
- 위성 이미지 처리
- 통계적 기계 번역
- 대규모 그래프 계산
- **Google 웹 검색 인덱싱 시스템** (핵심!)

---

## Large-Scale Indexing 사례

Google 웹 검색 인덱싱 시스템을 MapReduce로 재작성:

### Before vs After

| 측면 | Before | After (MapReduce) |
|------|--------|-------------------|
| 코드 크기 | 3,800줄 C++ | 700줄 |
| 변경 용이성 | 수 개월 | 수 일 |
| 장애 처리 | 수동 | 자동 |
| 확장성 | 어려움 | 머신 추가만 하면 됨 |

### 구조

```
크롤링 문서 (20+ TB, GFS)
       ↓
[MapReduce 1] 문서 파싱
       ↓
[MapReduce 2] ...
       ↓
[MapReduce 8] 최종 인덱스 생성
       ↓
검색 서빙 시스템
```

---

## 핵심 설계 원칙

### 1. 제한된 프로그래밍 모델

```
제약 → 자동 병렬화 가능
     → 자동 분산 가능
     → 자동 장애 복구 가능
```

### 2. 네트워크 대역폭 = 희소 자원

```
최적화 방향:
- Locality: 데이터 가까이에서 계산
- Combiner: 전송 데이터 줄이기
- 중간 데이터는 로컬 디스크에 저장 (GFS 복제 없이)
```

### 3. 재실행 = 장애 복구의 핵심

```
장애 발생 → 해당 task 재실행
- 체크포인팅보다 단순
- Deterministic 함수면 결과 동일
```

---

## MapReduce vs 이후 시스템

| 시스템 | 특징 |
|--------|------|
| **MapReduce** | 배치 처리, 디스크 기반, fault-tolerant |
| **Hadoop** | MapReduce 오픈소스 구현 (Yahoo) |
| **Spark** | 메모리 기반, 반복 계산에 최적화 |
| **Flink** | 스트림 처리 중심 |
| **Presto/Trino** | 대화형 SQL 쿼리 |

### MapReduce의 한계 (이후 개선된 점)

1. **디스크 I/O**: 중간 결과를 항상 디스크에 씀 → Spark는 메모리 캐싱
2. **반복 계산 비효율**: 매번 디스크에서 다시 읽음 → Spark RDD
3. **표현력 제한**: Map → Reduce 단순 구조 → DAG 기반 시스템
4. **실시간 처리 불가**: 배치 전용 → 스트림 처리 시스템

---

## 핵심 인용

> "Our abstraction is inspired by the map and reduce primitives present in Lisp and many other functional languages."

> "MapReduce has been so successful because it makes it possible to write a simple program and run it efficiently on a thousand machines in a half hour, greatly speeding up the development and prototyping cycle."

> "By restricting the programming model, we have made it easy to parallelize and distribute computations and to make such computations fault tolerant."

---

## 역사적 의의

- **Big Data 시대의 시작점**: 대규모 데이터 처리의 표준 패러다임 정립
- **Hadoop 생태계의 기반**: Yahoo가 오픈소스로 구현 → 산업 표준
- **분산 시스템 대중화**: 분산 처리 전문가 아니어도 대규모 계산 가능
- **후속 시스템 영감**: Spark, Flink 등 차세대 시스템의 출발점

---

## 내가 얻은 인사이트
