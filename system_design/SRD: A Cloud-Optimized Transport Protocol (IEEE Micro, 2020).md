# SRD: A Cloud-Optimized Transport Protocol (IEEE Micro, 2020)

## 출처
**링크** https://assets.amazon.science/a6/34/41496f64421faafa1cbe301c007c/a-cloud-optimized-transport-protocol-for-elastic-and-scalable-hpc.pdf

---

## AI 요약

### 1.1 문제 정의: 왜 TCP/RoCE가 안 되는가?

**TCP의 한계:**
```
- 데이터센터 best-case RTT: ~25ms
- 혼잡 시 tail latency: 50ms ~ 수 초
- 원인: OS 딜레이로 인해 retransmission timeout을 높게 설정해야 함
```

**RoCE (RDMA over Converged Ethernet) 한계:**
```
- Priority Flow Control (PFC) 필요
- PFC 문제: head-of-line blocking, congestion spreading, deadlock
- AWS 데이터센터 규모에서 PFC 불가능
```

**ECMP (Equal-Cost Multi-Path) 문제:**
```
- 정적 flow hashing → 경로별 부하 불균형
- Hash collision → hotspot → 패킷 드롭, throughput 감소, tail latency 증가
- 무관한 애플리케이션도 영향 받음
```

### 1.2 SRD 핵심 설계 원칙

**3가지 핵심 선택:**

| 설계 결정 | 선택 | 이유 |
|----------|------|------|
| 패킷 순서 | **Out-of-order 허용** | Head-of-line blocking 제거, 다중 경로 활용 |
| 구현 위치 | **Nitro Card (하드웨어)** | OS/hypervisor 노이즈 제거, 빠른 congestion 대응 |
| 경로 선택 | **Sender-controlled multipath** | RTT 기반 동적 경로 회피 |

### 1.3 Multipath Load Balancing

```
기존 ECMP:
  Flow A → Hash → 경로 1 (고정)
  Flow B → Hash → 경로 1 (충돌!) → Hotspot

SRD:
  Flow A → 패킷 1 → 경로 1
         → 패킷 2 → 경로 2  (RTT 기반 동적 선택)
         → 패킷 3 → 경로 3
```

**동작 방식:**
- 단일 flow도 여러 경로로 분산 (spray)
- 각 경로의 RTT 수집 → 느린 경로 회피
- 링크 장애 시 network routing 수렴(2-3 order of magnitude 느림) 기다리지 않고 즉시 다른 경로로 retransmit

### 1.4 Out-of-Order Delivery

**전통적 접근 vs SRD:**
```
TCP/InfiniBand RC:
  패킷 1, 3, 4 도착 (2 손실)
  → 1만 전달, 3,4 버퍼링
  → 2 재전송 대기 (head-of-line blocking)
  → 평균 latency 증가

SRD:
  패킷 1, 3, 4 도착 (2 손실)
  → 1, 3, 4 즉시 전달
  → 상위 레이어가 재조립
  → 손실된 2만 재전송
```

**왜 가능한가:**
- Message-based semantics (TCP의 byte stream 아님)
- 순서 복원 책임을 상위 레이어(libfabric)로 이동
- MPI tagged message는 같은 tag일 때만 순서 필요 → 애플리케이션이 더 잘 알고 있음

### 1.5 Congestion Control

**목표:**
```
"최소한의 in-flight bytes로 공정한 대역폭 확보,
 패킷 드롭에 의존하지 않고 큐 빌드업 방지"
```

**BBR 유사 알고리즘:**
- Per-connection dynamic rate limit + inflight limit
- ACK 타이밍으로 rate 추정
- RTT 증가 감지 → 혼잡 판단 → rate 감소

**Incast 대응:**
```
Incast: 다수 sender → 단일 receiver (last-hop switch 병목)

일반적 multipath spraying의 문제:
  - 같은 sender의 burst가 여러 경로로 동시 도착
  - Incast 악화 가능

SRD 해결:
  - Aggregate queueing 최소화
  - 경로별 독립적 혼잡 처리 (rerouting)
  - Connection-wide 혼잡은 rate limit으로 처리
```

### 1.6 EFA (Elastic Fabric Adapter) 인터페이스

**스택 구조:**
```
┌─────────────────────────────────┐
│    HPC/ML Application           │
│    (OpenMPI, Intel MPI, NCCL)   │
├─────────────────────────────────┤
│    libfabric provider           │  ← 패킷 재정렬, MPI tag matching
├─────────────────────────────────┤
│    User-space driver            │  ← OS bypass
├─────────────────────────────────┤
│    Nitro Card (EFA/SRD)         │  ← Reliability, Multipath, Congestion Control
└─────────────────────────────────┘
```

**EFA SRD Transport 특성:**
- InfiniBand Reliable Datagram (RD) 유사하지만 다름
- RD와 달리 순서 보장 안 함, segmentation 안 함
- Head-of-line blocking 없음 → 여러 flow 다중화 가능

### 1.7 성능 평가

**실험 1: 48-flow Incast (Bursty)**
```
설정: 4서버 × 12프로세스 → 단일 receiver
     Barrier 동기화 후 동시 전송

결과 (2MB 전송):
- SRD: 이상적 FCT에 근접, 매우 낮은 jitter
- TCP: 최대 FCT가 이상적의 3~20배
- TCP 50ms+ tail: retransmit timeout 반영
```

**실험 2: Persistent Incast Throughput**
```
100 Gb/s 총 대역폭, 기대 fair share: ~2 Gb/s/flow

- SRD: 모든 flow가 일정하고 이상적에 근접
- TCP: 각 flow가 심하게 oscillation, 일부 flow는 평균보다 훨씬 낮음
```

**실험 3: ECMP Imbalance (비혼잡 상황)**
```
설정: 8서버 → 8서버, full-bisection network
     TOR uplink 50% 활용, downlink 혼잡 없음

- TCP: 이상적 load balancing이면 혼잡 없어야 하지만
       ECMP 불균형으로 실제 혼잡 발생
       median latency 50% 높음, tail 1-2 order 높음
- SRD: median FCT 15% 높음 (이상적 대비)
       max SRD FCT < average TCP FCT
```

**EBS와의 연결:**
```
EBS io2 Block Express:
  - EC2 ↔ EBS 스토리지 노드 간 통신에 SRD 사용
  - 단일 TCP 연결 한계(25Gbps) 돌파
  - Tail latency 85% 감소 (re:Invent 2022 발표)
```

**설계 철학:**
1. **"Prevention over cure"**: 패킷 드롭 후 복구보다 드롭 자체를 방지
2. **"Move ordering up the stack"**: 네트워크 카드가 순서 보장 안 함 → 상위 레이어가 필요할 때만 처리
3. **"Hardware-software co-design"**: Nitro 카드에서 congestion control → μs 단위 반응
