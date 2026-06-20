# GPU 서버란 무엇이고 왜 필요한가 - CPU와 다른 처리량 중심 아키텍처

## 출처

- **아티클**: GPU Performance Background User's Guide
- **저자/출처**: NVIDIA (Deep Learning Performance Documentation, DU-09798-001)
- **링크**: [https://docs.nvidia.com/deeplearning/performance/dl-performance-gpu-background/index.html](https://docs.nvidia.com/deeplearning/performance/dl-performance-gpu-background/index.html)

---

## AI 요약

### 1. GPU 서버란?

GPU 서버는 **수천 개의 단순 연산 코어를 가진 GPU**를 1~8장(또는 그 이상) 탑재하고, 이들을 고속 인터커넥트(NVLink)와 대용량 고대역폭 메모리(HBM)로 묶어 **대량의 행렬·벡터 연산을 병렬로 쏟아내는(throughput-oriented)** 전용 연산 머신이다.

CPU 서버가 "소수의 강력한 코어로 한 작업을 빨리 끝내는(latency-oriented)" 구조라면, GPU 서버는 "수천 개의 약한 코어로 엄청난 양의 작업을 동시에 처리"하는 구조다.

| 구분 | CPU | GPU |
|---|---|---|
| 최적화 목표 | 지연(latency) — 단일 작업을 빨리 | 처리량(throughput) — 단위 시간당 총 연산량 |
| 코어 수 | 적음(수~수십) · 강력 | 많음(수천) · 단순 |
| 칩 면적 배분 | 대형 캐시 + 분기예측 + OoO 등 제어 로직 | 대부분 ALU(연산 유닛) |
| 지연 숨기는 법 | 캐시로 지연 감소 | 다른 스레드로 갈아타며 지연 은닉(latency hiding) |

### 2. GPU vs CPU 아키텍처 — 칩 면적의 철학

```
   CPU (latency 최적화)            GPU (throughput 최적화)
 ┌─────────────────────┐        ┌───────────────────────────┐
 │  Control  │ Control │        │ ALU ALU ALU ALU ALU ALU ... │
 │ ┌───┐ ┌───┐         │        │ ALU ALU ALU ALU ALU ALU ... │
 │ │ALU│ │ALU│  Cache  │        │ ALU ALU ALU ALU ALU ALU ... │ ← 면적 대부분이 ALU
 │ └───┘ └───┘ (대형)  │        │ ALU ALU ALU ALU ALU ALU ... │
 │ ┌───┐ ┌───┐         │        │ ───────────────────────── │
 │ │ALU│ │ALU│         │        │   작은 Cache / 작은 Control │
 │ └───┘ └───┘         │        └───────────────────────────┘
 └─────────────────────┘         코어 多 · 약함 · 동시 실행
  코어 少 · 강함 · 빠른 단일실행
```

문서의 핵심 메커니즘:

> "GPUs hide dependent instruction latency by switching to the execution of other threads."

GPU는 어떤 스레드가 메모리를 기다리며 멈추면 **즉시 다른 스레드로 갈아타 실행**하며 그 지연을 "숨긴다". CPU처럼 캐시로 지연을 줄이는 게 아니라, **일감을 과잉 공급(oversubscription)** 해서 빈 시간을 채운다. 그래서 GPU를 제대로 쓰려면 코어 수보다 **훨씬 많은 스레드**를 던져 넣어야 한다.

### 3. SIMT 실행 모델과 스레드 계층 (왜 병렬에 강한가)

GPU는 **SIMT (Single Instruction, Multiple Threads)** 모델로 동작한다.

- **Warp(워프)** = 32개 스레드가 묶여 **같은 명령어를 서로 다른 데이터에 동시에** 실행한다. 행렬 연산처럼 "같은 계산을 데이터만 바꿔 반복"하는 작업에 완벽히 들어맞는다.

```
Grid ──┬── Thread Block 0 ──┬── Warp 0 (32 threads, 같은 명령 동시 실행)
       │                    ├── Warp 1
       │                    └── ...
       ├── Thread Block 1 ── ...
       └── Thread Block N ── ...   (블록들이 여러 SM에 분배되어 동시 실행)
```

**딥러닝/HPC가 GPU에 맞는 이유**: 신경망 학습·추론, 과학 시뮬레이션은 연산의 80~90%가 **행렬 곱(matmul)**이다. 행렬 곱은 "수많은 곱셈-누산(multiply-add)을 서로 독립적으로 동시에" 하는 작업 → 수천 코어 + SIMT 구조와 정확히 일치한다. CPU의 소수 강력 코어로는 이 막대한 병렬도를 채울 수 없다.

### 4. GPU 서버 핵심 용어

| 용어 | 의미 |
|---|---|
| **SM (Streaming Multiprocessor)** | GPU의 기본 연산 블록. 스케줄러 + 실행 파이프라인 + CUDA/Tensor core를 품음. A100 = 108개 SM |
| **CUDA Core** | 범용 부동소수점/정수 연산 코어. FP32/FP16/INT8 등 일반 연산 |
| **Tensor Core** | 행렬 곱-누산(MMA) 전용 유닛. 작은 행렬 블록을 한 클럭에 곱-누산 |
| **L2 Cache** | 온칩 공유 캐시. A100 = 40MB |
| **VRAM / HBM** | 오프칩 고대역폭 메모리. A100 = 80GB HBM2, ~2039 GB/s |
| **NVLink** | GPU↔GPU 직결 인터커넥트. A100 600GB/s, H100 900GB/s (PCIe의 ~7배) |
| **PCIe** | GPU↔CPU/시스템 연결 버스. Gen5 x16 ≈ 128 GB/s |
| **FP16/BF16/TF32/FP8** | 저정밀 데이터 타입. 정밀도를 낮춰 메모리·연산량 절감, 처리량 향상 |
| **throughput vs latency** | GPU는 처리량, CPU는 지연을 최적화 |

GPU 메모리 계층 (코어에 가까울수록 빠르고 작음):

```
  [ SM 내부 레지스터 / 공유메모리 ]  ← 가장 빠름, 가장 작음
                │
            [ L2 Cache ]  (A100 40MB)
                │
        [ HBM DRAM / VRAM ]  (A100 80GB, ~2039 GB/s)
                │
   ── PCIe ──  [ CPU / 시스템 RAM ]   ← 가장 느린 경계
   ── NVLink ── [ 다른 GPU ]          ← GPU간 고속 직결
```

### 5. Tensor Core와 혼합 정밀도

> "Tensor Cores can compute and accumulate products in higher precision than the inputs. For example, during training with FP16 inputs, Tensor Cores can compute products without loss of precision and accumulate in FP32."

- Tensor Core는 입력은 저정밀(FP16/BF16/FP8)로 받되 **누산은 FP32**로 처리해 정확도를 지키면서 처리량을 끌어올린다.
- 행렬로 표현되지 않는 연산(element-wise 덧셈 등)은 Tensor Core가 아니라 일반 **CUDA core**가 처리한다.
- 정밀도가 낮을수록(FP32→TF32→FP16/BF16→FP8) 처리량은 오르고 메모리 사용량은 준다.

### 6. Arithmetic Intensity — "이 작업이 GPU를 제대로 쓰는가?"

이 문서의 가장 실무적인 개념. **산술 강도(arithmetic intensity)** = 연산 수 ÷ 접근 바이트 수 (FLOPS/Byte).

> 작업이 **math-limited(연산 한계)**: `#ops / #bytes > BW_math / BW_mem`
> 그렇지 않으면 **memory-limited(메모리 한계)** = 코어는 놀고 메모리 대역폭이 병목.

각 GPU는 고유한 **ops:byte 비율**(peak 연산속도 ÷ 메모리 대역폭)을 갖는다. V100 ≈ 40~139, A100은 더 높다.

| 연산 | 산술 강도 | 병목 |
|---|---|---|
| Linear layer (batch 512) | 315 FLOPS/B | 연산-한계 → GPU 잘 활용 |
| Linear layer (batch 1) | 1 FLOPS/B | 메모리-한계 → GPU 낭비 |
| Max pooling 3×3 | 2.25 FLOPS/B | 메모리-한계 |
| ReLU | 0.25 FLOPS/B | 메모리-한계 |
| Layer normalization | <10 FLOPS/B | 메모리-한계 |

→ **배치가 크고 행렬 곱 위주**일 때 GPU가 진가를 발휘하고, batch 1 추론·ReLU·정규화처럼 산술 강도가 낮은 연산은 메모리 대역폭에 묶여 코어가 논다.

---

## 내가 얻은 인사이트

### 성능 엔지니어링 관점

1. **GPU가 필요한 순간은 "산술 강도가 높은 대량 병렬 연산"일 때다.**
   - "AI니까 GPU"가 아니라, 작업의 ops:byte 비율이 GPU의 ops:byte 비율을 넘어야 코어가 포화된다.
   - 대형 batch의 행렬 곱(학습, 대량 배치 추론)은 연산 한계라 GPU가 빛나지만, batch 1 실시간 추론·element-wise·정규화·풀링은 메모리 한계라 비싼 코어가 논다. batch 1짜리 가벼운 서빙에 최고급 GPU를 붙이는 건 낭비일 수 있다.

2. **GPU 서버의 진짜 병목은 대개 "연산력"이 아니라 "메모리"다.**
   - **용량 병목**: 가중치+활성값+옵티마이저 상태가 VRAM에 안 들어가면 학습 자체 불가 → 멀티 GPU 분산이 강제된다.
   - **대역폭 병목**: 산술 강도가 낮은 연산은 HBM 대역폭에 묶인다. 실무 최적화는 코어 더 굴리기보다 **연산 융합(fusion)·데이터 재사용·batch 키우기**로 산술 강도를 끌어올려 메모리 한계를 연산 한계로 옮기는 작업이 핵심이다.

### 비용/설계 관점

3. **"GPU 효율 = 충분한 병렬도 공급"이라는 점이 카운터인튜이티브하다.**
   - GPU는 지연을 캐시가 아니라 "다른 스레드로 갈아타며" 숨기므로 일감(thread block)을 SM 수의 여러 배로 과잉 공급해야 한다(A100=108 SM).
   - 일감이 적으면(작은 batch·작은 텐서) 코어 대부분이 idle → 작은 모델·작은 입력에는 GPU가 오히려 CPU보다 비효율적일 수 있다.

4. **정밀도(precision)는 공짜 성능 레버다 — 단 트레이드오프 관리 필요.**
   - FP32→TF32→FP16/BF16→FP8로 내릴수록 처리량은 오르고(A100: TF32 156 → FP16 312 TFLOPS) VRAM·대역폭 부담도 준다.
   - 단 BF16/FP8는 표현 범위·정밀도가 달라 loss scaling·수치 안정성 검증이 실무 과제로 따라온다.

5. **멀티 GPU에서는 인터커넥트(NVLink vs PCIe)가 스케일링 효율을 가른다.**
   - 분산 학습은 GPU 간 gradient·파라미터 교환이 빈번한데, PCIe로 묶인 서버는 통신이 병목이 되어 GPU를 늘려도 선형 확장이 안 된다.
   - "GPU 몇 장이냐"만큼 **"GPU들이 어떻게 연결됐냐(NVLink/NVSwitch 유무)"**가 서버 선택의 핵심 기준이다.
