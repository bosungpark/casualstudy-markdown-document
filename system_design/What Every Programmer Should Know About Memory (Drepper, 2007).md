# What Every Programmer Should Know About Memory (Drepper, 2007)

## 출처
* 링크: https://people.freebsd.org/~lstewart/articles/cpumemory.pdf
* 발행: 2007년 11월 21일
* 저자: Ulrich Drepper (Red Hat, Inc.)
* 분량: 114페이지 (원문)

---

## AI 요약

### 논문의 핵심 메시지
> CPU 코어 속도는 빨라지고 코어 수는 늘어나지만, **대부분의 프로그램에서 병목은 메모리 접근**이다. 하드웨어 설계자들이 CPU 캐시 같은 기술을 만들었지만, **프로그래머의 도움 없이는 최적으로 작동할 수 없다.**

### 배경: CPU와 메모리의 속도 격차
```
초기 컴퓨터: CPU ≈ 메모리 속도
현대 컴퓨터: CPU >> 메모리 속도 (수백 배 차이)
```
- DRAM이 빠르지 않은 이유: 비용 문제 (빠른 RAM은 만들 수 있지만 경제적이지 않음)
- 해결책: 작고 빠른 SRAM(캐시) + 크고 느린 DRAM(메인 메모리)

### 현대 컴퓨터 하드웨어 구조

#### Northbridge/Southbridge 아키텍처
```
       ┌─────────┐     ┌─────────┐
       │  CPU 1  │     │  CPU 2  │
       └────┬────┘     └────┬────┘
            │               │
            └───────┬───────┘
                    │ FSB (Front Side Bus)
            ┌───────┴───────┐
            │  Northbridge  │ ← 메모리 컨트롤러 포함
            │               │
            └───────┬───────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
┌───┴───┐     ┌─────┴─────┐   ┌─────┴─────┐
│  RAM  │     │Southbridge│   │  PCI-E    │
└───────┘     └─────┬─────┘   └───────────┘
                    │
              ┌─────┴─────┐
              │USB, SATA..│
              └───────────┘
```

#### NUMA 아키텍처 (AMD Opteron, Intel CSI)
```
┌─────────┐       ┌─────────┐
│  CPU 1  │──────│  CPU 2  │
│  + RAM  │       │  + RAM  │
└────┬────┘       └────┬────┘
     │                 │
     └────────┬────────┘
              │ Interconnect
     ┌────────┴────────┐
     │                 │
┌────┴────┐       ┌────┴────┐
│  CPU 3  │──────│  CPU 4  │
│  + RAM  │       │  + RAM  │
└─────────┘       └─────────┘
```
- 로컬 메모리: 빠름
- 원격 메모리: 느림 (NUMA Factor)

### RAM 종류

#### SRAM (Static RAM) vs DRAM (Dynamic RAM)

| 특성 | SRAM | DRAM |
|------|------|------|
| 구조 | 6개 트랜지스터 | 1개 트랜지스터 + 1개 커패시터 |
| 속도 | 빠름 | 느림 |
| 비용 | 비쌈 | 저렴 |
| 리프레시 | 불필요 | 64ms마다 필요 |
| 용도 | CPU 캐시 | 메인 메모리 |

#### DRAM 접근 방식
```
주소 = Row Address + Column Address

1. RAS (Row Address Strobe): 행 선택
2. tRCD 대기 (RAS-to-CAS Delay)
3. CAS (Column Address Strobe): 열 선택  
4. CL 대기 (CAS Latency)
5. 데이터 전송
```

#### DDR 세대 발전
| 세대 | 셀 배열 | I/O 버퍼 | 버스 | 특징 |
|------|---------|----------|------|------|
| SDR | f | - | f | 단일 데이터 레이트 |
| DDR1 | f | 2bit | 2f | 양쪽 엣지 전송 |
| DDR2 | f | 4bit | 2f | 버스 주파수 2배 |
| DDR3 | f | 8bit | 4f | 저전압 (1.5V) |

### CPU 캐시 구조

#### 캐시 계층
```
┌────────────┐
│  CPU Core  │
├────────────┤
│    L1d     │ ← 데이터 캐시 (~32KB, ~3 cycles)
│    L1i     │ ← 명령어 캐시 (~32KB)
├────────────┤
│     L2     │ ← 통합 캐시 (~256KB-1MB, ~14 cycles)
├────────────┤
│     L3     │ ← 공유 캐시 (~4-8MB)
├────────────┤
│ Main Memory│ ← ~200-300 cycles
└────────────┘
```

#### 접근 시간 (Pentium M 기준)
| 위치 | 사이클 수 |
|------|----------|
| 레지스터 | ≤ 1 |
| L1d | ~3 |
| L2 | ~14 |
| 메인 메모리 | ~240 |

#### 캐시 라인 (Cache Line)
- 크기: 보통 64 bytes
- 주소 구조: `[Tag | Set Index | Offset]`
```
32-bit 주소 예시:
┌──────────┬──────────┬────────┐
│   Tag    │   Set    │ Offset │
│  T bits  │  S bits  │ O bits │
└──────────┴──────────┴────────┘
```

### 캐시 연관성 (Associativity)

| 유형 | 설명 | 장단점 |
|------|------|--------|
| **Direct Mapped** | 주소 → 정확히 1개 위치 | 빠름, 충돌 多 |
| **Fully Associative** | 주소 → 어디든 가능 | 충돌 無, 비쌈 |
| **N-way Set Associative** | 주소 → N개 위치 중 1개 | 균형잡힌 선택 |

#### 연관성 증가 효과 (L2 캐시, CL=32)
| 캐시 크기 | Direct | 2-way | 4-way | 8-way |
|----------|--------|-------|-------|-------|
| 512KB | 27.8M | 25.2M | 24.1M | 23.7M |
| 4MB | 7.7M | 4.7M | 3.8M | 3.4M |

### 실험 결과 분석

#### Sequential vs Random 접근
```
Sequential: ~9 cycles/element (프리페치 효과)
Random: ~450+ cycles/element (프리페치 무효화)
```

#### 데이터 구조 크기의 영향
```c
struct l {
    struct l *n;      // 다음 포인터
    long int pad[NPAD]; // 페이로드
};
```
- NPAD=0 (8 bytes): 캐시 라인 공유 → 빠름
- NPAD=7 (64 bytes): 요소당 1 캐시 라인 → L2까지는 괜찮음
- NPAD=15+ (128+ bytes): 프리페치 효과 감소 + TLB 미스 증가

#### TLB (Translation Lookaside Buffer) 영향
- TLB: 가상→물리 주소 변환 캐시 (64 엔트리 예시)
- TLB 미스 시: 수백 사이클 추가 비용
- 페이지 경계 넘기: 하드웨어 프리페처 무력화

### 캐시 쓰기 정책

| 정책 | 동작 | 특징 |
|------|------|------|
| **Write-through** | 즉시 메모리에 쓰기 | 단순, 느림 |
| **Write-back** | 캐시에만 쓰고 나중에 동기화 | 복잡, 빠름 |
| **Write-combining** | 여러 쓰기를 모아서 전송 | 그래픽 카드용 |
| **Uncacheable** | 캐시 안 함 | 디바이스 메모리용 |

### MESI 프로토콜 (캐시 일관성)

| 상태 | 의미 | 로컬 읽기 | 로컬 쓰기 | 원격 읽기 | 원격 쓰기 |
|------|------|----------|----------|----------|----------|
| **M** (Modified) | 수정됨, 유일한 복사본 | Hit | Hit | 공유+Flush | Invalid |
| **E** (Exclusive) | 깨끗함, 유일한 복사본 | Hit | →M | →S | Invalid |
| **S** (Shared) | 깨끗함, 여러 복사본 | Hit | →M, 타 무효화 | Hit | Invalid |
| **I** (Invalid) | 무효 | Miss | Miss | - | - |

### 프로그래머를 위한 최적화 가이드

#### 1. 데이터 지역성 (Locality)
```python
# 나쁜 예: 열 우선 접근 (캐시 미스 多)
for j in range(N):
    for i in range(N):
        matrix[i][j] += 1

# 좋은 예: 행 우선 접근 (캐시 친화적)
for i in range(N):
    for j in range(N):
        matrix[i][j] += 1
```

#### 2. 데이터 구조 정렬
```c
// 캐시 라인 크기에 맞춤 (64 bytes)
struct __attribute__((aligned(64))) data {
    int frequently_used;  // 같은 캐시 라인에
    int also_frequent;    // 함께 배치
    char padding[56];     // 다른 데이터와 분리
};
```

#### 3. 프리페칭 활용
```c
// 명시적 프리페치 (GCC)
__builtin_prefetch(&data[i + PREFETCH_DISTANCE], 0, 3);
```

#### 4. False Sharing 방지 (멀티스레드)
```c
// 나쁜 예: 같은 캐시 라인의 다른 변수 수정
int counter1;  // Thread 1이 수정
int counter2;  // Thread 2가 수정 → 캐시 라인 핑퐁

// 좋은 예: 패딩으로 분리
int counter1;
char padding[60];
int counter2;
```

---

## 내가 얻은 인사이트

1. **메모리가 새로운 디스크다**: CPU-메모리 속도 격차가 과거 메모리-디스크 격차와 유사. 캐시를 "메모리의 메모리"로 이해하면 최적화 전략이 명확해짐

2. **숫자로 보는 현실**: L1d 3 cycles vs 메인 메모리 240 cycles = 80배 차이. 이 격차가 캐시 최적화가 중요한 이유

3. **프리페칭의 양날의 검**: Sequential 접근은 9 cycles, Random은 450+ cycles. 프리페처가 예측 가능한 패턴에서만 작동하기 때문. Random 접근 시 오히려 불필요한 데이터를 미리 로드해서 성능 저하

4. **TLB(Translation Lookaside Buffer)를 잊지 말 것**: 가상 메모리 변환 비용이 은근 큼. 대용량 데이터 처리 시 Huge Pages 사용 고려

5. **멀티스레드 주의점**: False sharing은 보이지 않는 성능 저하. 스레드별 데이터는 최소 64바이트 간격으로 배치

6. **NUMA 시대의 도래**: 멀티소켓 서버에서는 메모리 위치가 성능에 직접 영향. `numactl`, `taskset` 같은 도구의 필요성

7. **하드웨어 이해의 가치**: 이 논문이 2007년 것이지만 기본 원리는 여전히 유효. L1/L2/L3 크기와 latency 숫자만 업데이트하면 현대 시스템에도 적용 가능

8. **벤치마크의 함정**: Working set이 캐시에 들어가는지 여부로 성능이 극적으로 변함. 작은 데이터셋 벤치마크가 실제 성능을 대표하지 못하는 이유
