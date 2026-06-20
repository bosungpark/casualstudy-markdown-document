# GPU 서버 소프트웨어 스택 - NVIDIA 드라이버·CUDA·cuDNN 설치와 CUDA 프로그래밍

## 출처

- **아티클**: An Even Easier Introduction to CUDA (Updated)
- **저자/출처**: Mark Harris, NVIDIA Technical Blog
- **링크**: [https://developer.nvidia.com/blog/even-easier-introduction-cuda/](https://developer.nvidia.com/blog/even-easier-introduction-cuda/)

---

## AI 요약

### 1. GPU 소프트웨어 스택 계층 구조

GPU 연산은 여러 소프트웨어 계층이 쌓여 동작하며, 각 계층은 바로 아래 계층에만 의존한다. 위에서 아래로 갈수록 하드웨어에 가까워진다.

```
┌─────────────────────────────────────────────────────────┐
│  Framework / 응용  (PyTorch, TensorFlow, JAX)            │  ← 사용자 모델 코드
├─────────────────────────────────────────────────────────┤
│  cuDNN / cuBLAS / NCCL (수학·DNN 라이브러리)             │  ← conv, GEMM 최적화 커널
├─────────────────────────────────────────────────────────┤
│  CUDA Toolkit                                            │
│   - Runtime API (libcudart, cudaMalloc/cudaMemcpy ...)   │  ← 고수준 C++ API
│   - nvcc (CUDA C++ 컴파일러)                              │  ← .cu → PTX/SASS
│   - Driver API (libcuda, cuLaunchKernel ...)             │  ← 저수준 API
├─────────────────────────────────────────────────────────┤
│  NVIDIA Driver (kernel module: nvidia.ko)               │  ← OS 커널 ↔ GPU 통신
├─────────────────────────────────────────────────────────┤
│  GPU 하드웨어 (SM, CUDA core, VRAM)                       │  ← 물리 연산 장치
└─────────────────────────────────────────────────────────┘
```

| 계층 | 역할 | 핵심 구성요소 |
|------|------|---------------|
| GPU 하드웨어 | 실제 병렬 연산. 수천 CUDA 코어가 SM 단위로 묶임 | SM, CUDA core, VRAM |
| NVIDIA Driver | 커널 모듈로 OS↔GPU 중개. **Driver API(libcuda) 노출** | `nvidia.ko`, `libcuda.so`, `nvidia-smi` |
| CUDA Toolkit | GPU 프로그램 컴파일/실행. **Runtime API + nvcc 제공** | `nvcc`, `libcudart.so`, 헤더 |
| cuDNN | DNN 연산(conv, pooling, RNN, softmax)의 GPU 최적화 구현 | `libcudnn.so` |
| Framework | 사용자 모델 코드. 내부적으로 cuDNN/cuBLAS 호출 | PyTorch, TensorFlow |

### 2. 버전 호환성 (driver ↔ CUDA ↔ cuDNN)

핵심 규칙은 **하위 계층이 상위 계층보다 같거나 새것이어야 한다(forward compatibility)**.

- **Driver ≥ CUDA Toolkit**: 새 드라이버는 자신보다 낮은 CUDA Toolkit을 모두 지원. 즉 `nvidia-smi`가 보여주는 CUDA 버전(드라이버 지원 최대치) ≥ `nvcc --version`(설치된 Toolkit)이어야 한다.
- **cuDNN ↔ CUDA**: cuDNN은 빌드된 CUDA major(예: cuDNN for CUDA 12.x)와 맞춰야 한다.
- **Framework ↔ CUDA + cuDNN**: 프레임워크는 특정 조합으로 빌드되므로 둘 다 동시에 맞아야 한다.

### 3. 설치 순서/방법 (Ubuntu 기준)

설치는 항상 **아래 계층부터 위로**: Driver → CUDA Toolkit → cuDNN → Framework.

**(1) NVIDIA 드라이버**
```bash
sudo apt install ubuntu-drivers-common
sudo ubuntu-drivers devices          # 권장 드라이버 확인
sudo apt install nvidia-driver-535   # 또는 ubuntu-drivers autoinstall
sudo reboot
nvidia-smi                           # 드라이버 + 지원 CUDA 최대 버전 확인
```

**(2) CUDA Toolkit (apt 저장소 방식 — 권장)**
```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get -y install cuda-toolkit-12-2   # 드라이버까지 원하면 'cuda'
```
환경 변수(`~/.bashrc`):
```bash
export PATH=/usr/local/cuda/bin${PATH:+:${PATH}}
export LD_LIBRARY_PATH=/usr/local/cuda/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}
```
> **runfile 방식**: `sudo sh cuda_12.x.x_*_linux.run` — 단일 파일 설치, 드라이버 설치 여부를 체크박스로 선택. apt가 깔끔하지만 runfile은 특정 버전 고정에 유리.

**(3) cuDNN**
```bash
sudo apt-get install libcudnn8 libcudnn8-dev   # CUDA 버전에 맞춘 패키지
```

**(4) 검증**
```bash
nvidia-smi          # 드라이버/지원 CUDA 최대 버전
nvcc --version      # 설치된 Toolkit 버전
python -c "import torch; print(torch.cuda.is_available())"
```

### 4. `nvidia-smi` vs `nvcc --version` — 핵심 차이

| | `nvidia-smi` | `nvcc --version` |
|---|---|---|
| 출처 계층 | NVIDIA Driver | CUDA Toolkit |
| 보고하는 것 | **Driver API** 기준, 드라이버가 지원하는 **최대** CUDA | **Runtime API** 기준, 실제 설치된 Toolkit |
| 라이브러리 | `libcuda.so` | `libcudart.so` |

두 값이 다른 것은 **정상이며 의도된 설계**다(예: nvidia-smi=12.2, nvcc=11.8). 규칙은 `nvcc ≤ nvidia-smi`.

- **Driver API (`libcuda`, `cu*`)**: 저수준. 컨텍스트/모듈 명시 관리, PTX 직접 로드. 드라이버에 포함.
- **Runtime API (`libcudart`, `cuda*`)**: 고수준. `cudaMalloc`, `cudaMemcpy`, `<<<>>>` 런치 등 대부분 앱이 사용. Toolkit에 포함, 내부적으로 Driver API 호출.

### 5. CUDA 프로그래밍 모델

**Host / Device 구분**
- **Host** = CPU + 시스템 메모리 (일반 C++ 코드)
- **Device** = GPU + VRAM (`__global__`/`__device__` 커널 함수)

**Grid / Block / Thread 계층**
```
Grid  ── 여러 Block 으로 구성 (gridDim.x = block 개수)
 └─ Block ── 여러 Thread 로 구성 (blockDim.x = thread 개수, 최대 보통 1024)
     └─ Thread ── 최소 실행 단위 (실제로 32개씩 'warp' 단위 SIMT 실행)
```
- `threadIdx.x`(block 내 인덱스), `blockIdx.x`(grid 내 block 인덱스), `blockDim.x`, `gridDim.x`
- **전역 thread 인덱스**: `blockIdx.x * blockDim.x + threadIdx.x`
- **grid-stride loop**: 전체 스레드 수보다 큰 배열 처리 관용 패턴 (`stride = blockDim.x * gridDim.x`)

**메모리 계층 (빠름 → 느림)**

| 종류 | 범위 | 속도 | 비고 |
|---|---|---|---|
| Register | thread 1개 | 가장 빠름 | 컴파일러 자동 할당 |
| Shared memory | block 내 공유 | 빠름(on-chip) | `__shared__`, 타일링 |
| Local memory | thread 1개 | 느림 | 레지스터 스필 시 |
| Global memory (VRAM) | 전체 + host | 느림(off-chip) | `cudaMalloc` |

**메모리 관리 API**: `cudaMalloc`/`cudaFree`(명시 할당), `cudaMemcpy`(host↔device 복사), `cudaMallocManaged`(Unified Memory, 페이지 자동 마이그레이션), `cudaDeviceSynchronize`(커널 비동기 완료 대기).

**Vector Add 전체 예제 (Unified Memory)**
```cuda
#include <iostream>
#include <math.h>

__global__
void add(int n, float *x, float *y)
{
  int index  = blockIdx.x * blockDim.x + threadIdx.x;  // 전역 thread 인덱스
  int stride = blockDim.x * gridDim.x;                 // grid-stride
  for (int i = index; i < n; i += stride)
    y[i] = x[i] + y[i];
}

int main(void)
{
  int N = 1<<20;                            // 약 100만 원소
  float *x, *y;
  cudaMallocManaged(&x, N*sizeof(float));   // host/device 공유 메모리
  cudaMallocManaged(&y, N*sizeof(float));

  for (int i = 0; i < N; i++) { x[i] = 1.0f; y[i] = 2.0f; }

  int blockSize = 256;
  int numBlocks = (N + blockSize - 1) / blockSize;   // 올림 나눗셈
  add<<<numBlocks, blockSize>>>(N, x, y);            // 커널 런치(비동기)

  cudaDeviceSynchronize();                  // GPU 완료 대기

  float maxError = 0.0f;
  for (int i = 0; i < N; i++) maxError = fmax(maxError, fabs(y[i]-3.0f));
  std::cout << "Max error: " << maxError << std::endl;  // 0 이면 성공

  cudaFree(x); cudaFree(y);
  return 0;
}
```
> 컴파일/실행: `nvcc add.cu -o add && ./add`. 전통 패턴은 host 버퍼 → `cudaMalloc` → `cudaMemcpy(H2D)` → 커널 → `cudaMemcpy(D2H)` → `cudaFree`.

---

## 내가 얻은 인사이트

### 환경 구축 관점

1. **"버전 지옥"은 컨테이너로 우회하라.**
   - 호스트에는 NVIDIA 드라이버만 깔고, CUDA Toolkit·cuDNN은 컨테이너 이미지(NGC `nvidia/cuda`, `pytorch/pytorch`)에 가두는 것이 사실상 표준.
   - nvidia-container-toolkit(구 nvidia-docker)이 호스트 드라이버를 컨테이너에 주입하므로, 드라이버만 forward-compatible하면 한 머신에서 CUDA 11.8과 12.2 프로젝트를 충돌 없이 동시 운용 가능. 호스트에 Toolkit을 안 까는 것이 가장 깔끔하다.

2. **nvidia-smi의 CUDA 버전 ≠ Toolkit 버전인 이유를 알면 디버깅이 빨라진다.**
   - nvidia-smi는 "드라이버가 지원하는 최대 CUDA"(Driver API), nvcc는 "실제 설치된 Toolkit"(Runtime API). 둘이 달라도 정상.
   - 빌드/런타임에 실제 쓰이는 건 `nvcc`·`libcudart`. nvidia-smi만 보고 "CUDA 12.2가 깔렸다"고 오해해 빌드가 깨지는 일이 흔하다. 규칙: `nvcc ≤ nvidia-smi`만 지키면 된다.

3. **드라이버는 절대 다운그레이드하지 말고, Toolkit으로 맞춰라.**
   - forward compatibility 덕분에 드라이버는 최신 유지하고 그 아래 Toolkit 버전만 골라 쓰는 게 안전. 드라이버를 낮추면 다른 워크로드가 깨진다.

### 개발 관점

4. **pip로 깐 PyTorch는 시스템 CUDA를 거의 안 쓴다.**
   - `pip install torch` 휠은 자체 CUDA 런타임과 cuDNN을 동봉하므로 시스템 Toolkit/cuDNN 없이도 동작.
   - 시스템 CUDA가 꼭 필요한 경우는 커스텀 `.cu` 확장 컴파일(예: flash-attention 빌드)뿐. 불필요한 시스템 설치를 줄일 수 있다.

5. **성능의 80%는 메모리 계층에서 갈린다.**
   - global memory는 느리고 register/shared memory는 빠르다. 단순 vector add는 메모리 대역폭에 묶이지만, 행렬곱은 shared memory 타일링·coalesced 접근·warp(32) 단위 정합으로 수십 배 차이.
   - block 크기를 256처럼 warp(32)의 배수로 잡는 것도 같은 이유. 커널을 짤 때 "어느 메모리에 무엇이 있는가"를 먼저 설계해야 한다.
