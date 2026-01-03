# The Datacenter as a Computer: Designing Warehouse-Scale Machines

## 출처
- **저자**: Luiz André Barroso, Urs Hölzle, Parthasarathy Ranganathan (Google)
- **링크**: https://www.morganclaypool.com/doi/abs/10.2200/S00293ED1V01Y200905CAC006
- **에디션**: 3rd Edition (2019), Morgan & Claypool Publishers
- **무료 PDF**: https://pages.cs.wisc.edu/~shivaram/cs744-readings/dc-computer-v3.pdf

---

## AI 요약

Google의 데이터센터 설계 철학을 담은 책. 핵심 아이디어는 **"데이터센터 자체를 하나의 거대한 컴퓨터로 본다"**는 것.

### 핵심 개념: Warehouse-Scale Computer (WSC)

| 기존 데이터센터 | WSC |
|----------------|-----|
| 여러 조직의 서버 co-location | 단일 조직 소유 |
| 이기종 하드웨어/소프트웨어 | 동종 플랫폼 |
| 서버 간 독립적 | 전체가 하나의 컴퓨터 |
| 서드파티 소프트웨어 | 대부분 자체 개발 |

### 책 구성 (8장)

| 장 | 주제 | 핵심 내용 |
|----|------|----------|
| 1 | Introduction | WSC 정의, 왜 중요한가 |
| 2 | Workloads & Software | 소프트웨어 스택, 워크로드 특성 |
| 3 | Hardware Building Blocks | 서버, 스토리지, 네트워크, 가속기 |
| 4 | Data Center Basics | 전력, 냉각, 빌딩 설계 |
| 5 | Energy Efficiency | PUE, Energy Proportional Computing |
| 6 | Modeling Costs | TCO 분석 |
| 7 | Dealing with Failures | 장애 처리, 복구 |
| 8 | Closing Remarks | 미래 전망, Moore's Law 이후 |

---

### Chapter 2: 소프트웨어 스택

```
┌─────────────────────────────────────┐
│     Application Level Software      │  ← Gmail, Search, YouTube
├─────────────────────────────────────┤
│   Cluster-Level Infrastructure      │  ← Borg, Colossus, BigTable
├─────────────────────────────────────┤
│      Platform-Level Software        │  ← Linux, Drivers, Libraries
├─────────────────────────────────────┤
│           Hardware                  │  ← Servers, Storage, Network
└─────────────────────────────────────┘
```

**WSC vs Desktop 소프트웨어 차이점**:
- **병렬성 풍부**: Data parallelism + Request parallelism
- **빠른 변화**: 릴리즈 주기가 주 단위 (데스크톱은 년 단위)
- **플랫폼 동질성**: 하드웨어 설정이 몇 가지로 제한됨
- **장애 일상화**: 수천 대 서버 → 매일 장애 발생

**핵심 기법들**:

| 기법 | 목적 | 설명 |
|------|------|------|
| **Replication** | 성능/가용성 | 데이터 복제로 처리량, 가용성 향상 |
| **Sharding** | 성능/가용성 | 데이터를 작은 조각(shard)으로 분산 |
| **Load Balancing** | 성능 | 느린 서버가 전체를 지연시키지 않도록 |
| **Health Checking** | 가용성 | 느린/죽은 서버 빠르게 감지 |
| **Eventual Consistency** | 성능/가용성 | 강한 일관성 포기 → 성능 확보 |
| **Canary** | 가용성 | 전체 배포 전 소수 서버에 먼저 테스트 |

---

### Chapter 3: 하드웨어 빌딩 블록

**서버 전력 분포 (2017년 기준)**:
```
CPU:     61%  ████████████████████████████████
DRAM:    18%  █████████
Power:    7%  ████
Network:  5%  ███
Misc:     4%  ██
Cooling:  3%  ██
Storage:  2%  █
```

**Brawny vs Wimpy 서버**:
- **Brawny**: 고성능 CPU (Xeon 등) - 대부분 워크로드에 적합
- **Wimpy**: 저전력 CPU (Atom, ARM) - 특정 워크로드에만 유리

**가속기 (Accelerators)**:
- **GPU**: 범용 병렬 처리
- **TPU**: ML 추론/학습 특화 (Google 자체 개발)

---

### Chapter 5: 에너지 효율

**PUE (Power Usage Effectiveness)**:
```
PUE = 전체 시설 전력 / IT 장비 전력

PUE 2.0 = 50% 효율 (절반이 냉각/전력손실)
PUE 1.1 = 90% 효율 (Google 목표)
```

**Energy Proportional Computing 문제**:

서버는 **idle 상태에서도 전력 소비가 높음**:
```
활용률   전력소비(피크 대비)
  0%  →  ~50% (idle도 절반 소비!)
 50%  →  ~75%
100%  →  100%
```

이상적 시스템 = 활용률에 비례한 전력 소비

---

### Chapter 6: 비용 모델 (TCO)

**Total Cost of Ownership** 구성:

| 비용 유형 | 항목 |
|-----------|------|
| **CapEx** | 서버, 네트워크, 빌딩, 전력/냉각 인프라 |
| **OpEx** | 전기료, 인건비, 유지보수, 대역폭 |

**비용 분포 예시**:
- 서버: ~60%
- 네트워크: ~10%
- 전력/냉각 인프라: ~15%
- 전기료 (연간): ~15%

---

### Chapter 7: 장애 처리

**연간 장애율**:
- 디스크: 2-4%
- 서버 재시작: 1.2-16회/년
- 수천 대 클러스터 → **매 시간 장애 발생**

**장애 원인 분포**:
1. 소프트웨어 버그 (가장 큼)
2. 하드웨어 (디스크, 메모리, CPU)
3. 운영 실수 (설정 오류 등)
4. 네트워크

**핵심 원칙**:
> "Tolerating faults, not hiding them"  
> 장애를 숨기지 말고, 노출하고 대응하라

---

### Latency Numbers Every Engineer Should Know

| 연산 | 시간 |
|------|------|
| L1 cache | 1.5 ns |
| L2 cache | 5 ns |
| L3 cache | 25 ns |
| Main memory | 100 ns |
| SSD random read | 100 μs |
| 1MB from SSD | 500 μs |
| 1MB from 10Gbps network | 1 ms |
| 1MB from disk | 10 ms |
| Disk seek | 10 ms |
| CA→Netherlands→CA | 150 ms |

---

### Tail Latency 문제

단일 서버: 99% < 10ms, 1% = 1s

| 서버 수 | P(응답 > 1s) |
|--------|--------------|
| 1 | 1% |
| 100 | **63%** |
| 2000 | 거의 100% |

→ **Tail Tolerance** 기법 필요 (redundant execution 등)

---

### 핵심 인사이트

1. **Scale changes everything**: 규모가 커지면 모든 것이 달라짐
2. **Failures are normal**: 장애는 예외가 아니라 일상
3. **Software defines the system**: 하드웨어보다 소프트웨어가 시스템 정의
4. **End-to-end optimization**: 전체 스택 최적화 필요
5. **Measure everything**: 측정 없이 최적화 불가

---

## 내가 얻은 인사이트

(여기에 직접 작성)