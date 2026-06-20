# CUDA vs OpenCL - GPGPU 프로그래밍 모델 비교와 vendor lock-in

## 출처

- **아티클/논문**: A Comprehensive Performance Comparison of CUDA and OpenCL
- **저자/출처**: Jianbin Fang, Ana Lucia Varbanescu, Henk Sips (Delft University of Technology) / ICPP'11
- **링크**: [https://ieeexplore.ieee.org/document/6047190/](https://ieeexplore.ieee.org/document/6047190/)

> 16개 벤치마크(합성 + 실제 애플리케이션)로 CUDA와 OpenCL을 정량 비교하고, 성능 격차의 원인을 프로그래밍 모델/최적화/아키텍처/컴파일러 네 차원으로 분해한 GPGPU 비교 분야의 표준 인용 논문.

---

## AI 요약

### 1. CUDA vs OpenCL 개념

| 항목 | CUDA | OpenCL |
|------|------|--------|
| 주체 | NVIDIA (proprietary, 독점) | Khronos Group (open standard) |
| 대상 하드웨어 | NVIDIA GPU 전용 | CPU/GPU/FPGA/DSP, 멀티 벤더 |
| 라이선스 | NVIDIA 종속 | royalty-free, cross-vendor |
| 추상화 수준 | 저수준 제어 강함, HW 밀착 | 이식성 우선, HW 차이 흡수 |
| 실행 모델 | SIMT | 동일 SIMT 기반 |

두 모델 모두 **계층적 데이터 병렬(hierarchical data-parallel)** 모델로, GPU 커널 함수를 다수 스레드에서 실행하는 구조가 본질적으로 같다. 그래서 한쪽을 다른 쪽으로 거의 기계적으로 변환할 수 있을 만큼 개념이 1:1 대응된다.

### 2. 용어 매핑

| 개념 | CUDA | OpenCL |
|------|------|--------|
| 가장 작은 실행 단위 | thread | work-item |
| 스레드 묶음 | block (thread block) | work-group |
| 전체 실행 공간 | grid | NDRange |
| 빠른 온칩 공유 메모리 | shared memory | local memory |
| 스레드 로컬 메모리 | local / registers | private memory |
| 전역 메모리 | global memory | global memory |
| 하드웨어 연산 유닛 | SM (Streaming Multiprocessor) | CU (Compute Unit) |
| 전역 인덱스 | `blockIdx*blockDim+threadIdx` | `get_global_id()` |
| 동기화 | `__syncthreads()` | `barrier(CLK_LOCAL_MEM_FENCE)` |

차이점: CUDA는 thread hierarchy를 **개발자가 더 저수준으로 직접 제어**하고, OpenCL은 work-item을 가용 하드웨어 자원에 **런타임이 자동 매핑**하는 경향.

### 3. 커널 문법 차이

**CUDA 커널 (벡터 덧셈)**
```cuda
__global__ void vecAdd(float* a, float* b, float* c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) c[i] = a[i] + b[i];
}
// 호스트 측 실행
vecAdd<<<gridDim, blockDim>>>(d_a, d_b, d_c, n);  // <<< >>> 실행 구문
```

**OpenCL 커널 (동일 연산)**
```c
__kernel void vecAdd(__global float* a, __global float* b,
                     __global float* c, int n) {
    int i = get_global_id(0);
    if (i < n) c[i] = a[i] + b[i];
}
// 호스트 측: clEnqueueNDRangeKernel(queue, kernel, ...) 로 실행
```

- `__global__` ↔ `__kernel`, 포인터마다 `__global`/`__local` 주소공간 한정자를 명시(OpenCL).
- 인덱스 직접 계산(CUDA) ↔ `get_global_id()` 내장 함수(OpenCL).
- CUDA는 `<<<...>>>` 전용 문법, OpenCL은 표준 C API(`clEnqueueNDRangeKernel`) → OpenCL은 boilerplate(플랫폼/디바이스 조회, 컨텍스트·큐 생성, 런타임 컴파일)가 훨씬 많아 개발 편의성이 낮음.
- CUDA는 컴파일 타임(nvcc) 빌드, OpenCL은 보통 **런타임 컴파일**(이식성의 대가).

### 4. 비교 차원 정리

| 차원 | CUDA | OpenCL |
|------|------|--------|
| **이식성** | 낮음 — NVIDIA GPU 고정 | 높음 — 멀티 벤더/디바이스 |
| **성능** | 실제 앱에서 보통 우위 | 공정 비교 시 동등 |
| **성능 격차** | 일부 앱에서 최대 ~30% 우위 | "불공정 비교" 탓 — 공정 비교 시 유사 |
| **생태계/라이브러리** | cuDNN, cuBLAS, cuFFT, Thrust, NCCL 압도적 | 상대적으로 빈약 |
| **개발 편의성** | 높음 (간결 문법, Nsight 등 풍부한 툴) | 낮음 (장황한 호스트 코드, 런타임 컴파일) |
| **하드웨어 지원** | NVIDIA 전용 | NVIDIA/AMD/Intel GPU·CPU, ARM Mali, 모바일/임베디드 |

**논문의 핵심 발견**: 합성 벤치마크(peak 측정)에서는 두 모델이 거의 동등하지만, 실제 애플리케이션에서는 CUDA가 더 나아 보인다. 그 격차는 ① 프로그래밍 모델 차이, ② 적용된 최적화 정도, ③ 아키텍처 세부, ④ 컴파일러 차이에서 비롯된다. 이 넷을 정렬해 **"공정 비교(fair comparison)"**를 하면 OpenCL도 CUDA에 준하는 성능을 낸다. 즉 **OpenCL 성능 열위는 언어 본질이 아니라 측정/튜닝의 비대칭** 때문이라는 것이 결론.

### 5. 현대 대안

- **SYCL / Intel oneAPI**: 단일 소스 C++ 기반 이식성 모델. OpenCL의 장황함을 C++로 해소, 멀티 벤더 지향.
- **AMD ROCm / HIP**: CUDA와 거의 동일한 API(소스 호환). `hipify`로 CUDA→HIP 변환, NVIDIA·AMD 양쪽 타깃 → "CUDA lock-in 탈출" 경로.
- OpenCL은 여전히 모바일/임베디드/FPGA에서 강세지만, HPC/딥러닝에서는 SYCL·HIP로 무게가 옮겨가는 추세.

---

## 내가 얻은 인사이트

### 기술 선택 관점

1. **성능보다 생태계가 lock-in을 만들었다.**
   - 공정 비교 시 OpenCL은 CUDA 대비 성능 격차가 미미하다. 그럼에도 업계가 CUDA로 수렴한 진짜 이유는 커널 성능이 아니라 cuDNN·cuBLAS·Nsight 같은 **고수준 라이브러리/툴체인 생태계**와 개발 편의성. "30% 빠르다"는 통념은 과장이며 락인의 원인은 다른 곳에 있다.

2. **벤치마크 결과를 액면 그대로 믿지 말 것.**
   - 같은 알고리즘이라도 한쪽만 튜닝하면 30% 차이가 나지만, 양쪽에 동일 최적화·동일 컴파일 단계를 적용하면 거의 사라진다.
   - "CUDA가 빠르다"는 주장을 받을 때는 비교가 **공정(fair)했는지**(같은 최적화 수준, 같은 데이터 전송 측정 방식)부터 검증해야 한다.

### 전략/비용 관점

3. **Vendor lock-in의 트레이드오프는 명확하다.**
   - CUDA를 택하면 최고의 생산성·툴·라이브러리를 얻는 대신 NVIDIA 하드웨어에 묶이고 GPU 조달 협상력·비용 통제력을 잃는다. 클라우드 GPU 비용이 폭등하는 환경에서 장기 리스크.

4. **이식성이 필요할 때 OpenCL/SYCL을 택하라.**
   - 모바일·임베디드·FPGA, 또는 AMD/Intel GPU를 함께 타깃하거나 단일 벤더 의존을 전략적으로 피하려는 경우 합리적. 이식성 자체는 논문이 보였듯 성능을 근본적으로 희생시키지 않는다.

5. **신규 프로젝트라면 HIP/SYCL을 진지하게 검토하라.**
   - 순정 OpenCL의 장황함은 싫고 CUDA 락인도 피하고 싶다면, CUDA와 소스 호환되는 ROCm-HIP나 단일 소스 C++인 SYCL/oneAPI가 현실적 절충점.
   - 특히 HIP는 기존 CUDA 코드를 `hipify`로 변환해 NVIDIA·AMD 양쪽을 커버할 수 있어 **점진적 탈락인** 전략에 적합하다.
