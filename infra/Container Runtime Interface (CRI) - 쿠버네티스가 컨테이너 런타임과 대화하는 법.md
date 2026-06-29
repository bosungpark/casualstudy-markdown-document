# Container Runtime Interface (CRI) - 쿠버네티스가 컨테이너 런타임과 대화하는 법

## 출처
- **아티클**: Introducing Container Runtime Interface (CRI) in Kubernetes
- **저자/출처**: Kubernetes Blog (공식, Yu-Ju Hong 외)
- **게재**: 2016-12-19 (Kubernetes 1.5에서 Alpha 도입)
- **링크**: https://kubernetes.io/blog/2016/12/container-runtime-interface-cri-in-kubernetes/

---

## AI 요약

### 1. CRI란? 그리고 왜 필요했나

**CRI(Container Runtime Interface)** 는 kubelet이 **재컴파일 없이** 다양한 컨테이너 런타임을 쓸 수 있게 해주는 **플러그인 인터페이스**입니다. Kubernetes 1.5에서 도입되었습니다.

**도입 전의 문제**: 컨테이너 런타임(Docker, rkt)이 kubelet **소스코드 안에** 내부적이고 불안정한 인터페이스로 깊게 박혀 있었습니다.

```
[ CRI 이전: 강결합 ]                    [ CRI 이후: 플러그인 ]

  ┌───────────────────────┐            ┌───────────────────────┐
  │       kubelet         │            │       kubelet         │
  │  ┌─────────────────┐  │            │   (gRPC Client)       │
  │  │ Docker 통합 코드  │  │            └───────────┬───────────┘
  │  │ rkt 통합 코드     │  │                        │ CRI (gRPC)
  │  │ (하드코딩)        │  │                        │ over Unix socket
  │  └─────────────────┘  │            ┌───────────▼───────────┐
  └───────────────────────┘            │  CRI Shim / Runtime   │
   새 런타임 = kubelet 수정              │ (containerd, CRI-O…)  │
   + 재컴파일 + 내부 이해 필요           └───────────────────────┘
                                        새 런타임 = gRPC 서버만 구현
```

| 측면 | CRI 이전 | CRI 이후 |
|------|----------|----------|
| 통합 방식 | kubelet에 하드코딩 | 플러그인 인터페이스 |
| 새 런타임 추가 | kubelet 재컴파일 필요 | 불필요 |
| 유지보수 부담 | 쿠버네티스 커뮤니티 | 런타임 개발자 |
| 진입 장벽 | kubelet 내부 지식 필요 | gRPC API만 구현 |

### 2. 아키텍처 — gRPC + Protocol Buffers + 두 개의 서비스

- **프레임워크**: gRPC (RPC), **직렬화**: Protocol Buffers, **전송**: Unix socket
- kubelet은 gRPC **클라이언트**, 런타임은 gRPC **서버**
- 설정 플래그: `--container-runtime-endpoint`, `--image-service-endpoint`

```
┌─────────────────────── kubelet (gRPC Client) ───────────────────────┐
└─────────────────────────────┬───────────────────────────────────────┘
                              │ Unix socket / gRPC
┌─────────────────────────────▼───────────────────────────────────────┐
│                     CRI Shim / Container Runtime                     │
│                                                                      │
│   ┌──────────────────────┐         ┌──────────────────────────────┐ │
│   │     ImageService     │         │        RuntimeService        │ │
│   │  - PullImage         │         │  - RunPodSandbox             │ │
│   │  - ImageStatus       │         │  - CreateContainer           │ │
│   │  - ListImages        │         │  - StartContainer            │ │
│   │  - RemoveImage       │         │  - StopContainer / Remove…   │ │
│   └──────────────────────┘         │  - Exec / Attach / PortForward│ │
│                                    └──────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

**두 핵심 서비스**:
- **ImageService**: 이미지 관리 (`PullImage`, `ImageStatus`, `ListImages`, `RemoveImage`)
- **RuntimeService**: Pod/컨테이너 생명주기 + 상호작용

### 3. Pod는 CRI로 어떻게 생성되는가 — PodSandbox 개념

CRI의 핵심 추상은 **PodSandbox**입니다. 컨테이너 그룹이 공유하는 격리 환경(네트워크/IPC NS, 호스트명 등)을 먼저 만들고, 그 안에 컨테이너를 채웁니다. (Docker 런타임에서는 이 Sandbox가 곧 **pause 컨테이너**로 구현됩니다 → 4편 참고)

```
   ① RunPodSandbox()        Pod 격리 환경(네트워크 NS 등) 생성
          │                 → podSandboxId 반환
          ▼
   ② CreateContainer()      Sandbox 안에 앱 컨테이너 생성
          │  (podSandboxId, image, command, mounts, resources…)
          │                 → containerId 반환
          ▼
   ③ StartContainer()       컨테이너 실행 시작
          │                 → (containerId)
          ▼
   ④ (컨테이너마다 ②~③ 반복)

   ───────────────  결과: 격리 환경 + 실행 중인 컨테이너들  ───────────────

   [ 종료 흐름 ]
   StopContainer → RemoveContainer → StopPodSandbox → RemovePodSandbox
```

> 💡 **"Pod = Sandbox(공유 격리 환경) + 그 안의 컨테이너들"** 이라는 구조가 CRI 레벨에서 명시적으로 드러난다. 쿠버네티스의 Pod 추상이 런타임까지 일관되게 내려가는 지점.

### 4. 스트리밍 API — exec / attach / port-forward

`kubectl exec`, `kubectl attach`, `kubectl port-forward`를 지원하기 위한 양방향 스트리밍 RPC입니다.

| RPC | 용도 | kubectl 명령 |
|-----|------|-------------|
| `Exec` | 실행 중 컨테이너에서 명령 실행 | `kubectl exec` |
| `Attach` | 컨테이너 stdin/stdout/stderr 연결 | `kubectl attach` |
| `PortForward` | 로컬 포트 → 컨테이너 포트 터널링 | `kubectl port-forward` |

**구현 디테일**: 이 RPC들은 데이터를 직접 스트리밍하지 않고 **스트리밍 서버의 URL을 반환**합니다. kubelet이 스트리밍을 별도 컴포넌트에 위임 → 네트워크 설정과 멀티플렉싱을 유연하게 제어.

### 5. CRI를 구현하는 런타임들

```
                    kubelet
                       │ CRI (gRPC)
        ┌──────────────┼───────────────┬────────────────┐
        ▼              ▼               ▼                ▼
   dockershim*    containerd        CRI-O          (기타 CRI 호환)
   → Docker       (+ CRI plugin)   (K8s 전용)
   *1.24에서 제거    → runc          → runc
                       ▼               ▼
                    runc (OCI 런타임) → 실제 컨테이너 (namespace/cgroup)
```

- **dockershim**: 최초의 CRI 구현체. Docker는 CRI 비호환이라 kubelet 내부에 번역 계층으로 존재 → **K8s 1.24에서 제거** (3편 참고)
- **containerd**: CRI plugin 내장, 현재 가장 널리 쓰임
- **CRI-O**: 쿠버네티스 전용으로 만든 경량 런타임
- 최종적으로 모두 **runc** 같은 OCI 런타임을 호출해 실제 컨테이너 생성

> 전체 흐름: **kubelet → (CRI) → containerd → (OCI) → runc → namespace/cgroup으로 컨테이너 생성**
> 강의에서 말하는 "쿠버네티스 흐름으로 이해하는 컨테이너"의 바로 그 호출 사슬.

---

## 내가 얻은 인사이트

### 아키텍처 관점
1. **CRI는 "관심사의 분리"를 인터페이스로 못 박은 사례다**
   - kubelet은 "Pod를 어떻게 띄울지"의 정책만, 런타임은 "실제로 어떻게 컨테이너를 만들지"의 메커니즘만 책임진다. 표준 인터페이스 하나로 생태계가 폭발적으로 다양해졌다(containerd, CRI-O, Kata, gVisor…).

2. **PodSandbox가 Pod 추상의 런타임 구현체다**
   - 쿠버네티스 API의 "Pod"가 CRI에선 "Sandbox + 컨테이너들"로 1:1 매핑된다. 추상이 위(API)에서 아래(런타임)까지 일관되게 관통하는 좋은 설계. pause 컨테이너의 정체도 여기서 설명된다.

### 운영 관점
3. **"Docker 없이도 쿠버네티스가 돈다"의 기술적 근거가 CRI다**
   - dockershim 제거 논란(2020)을 이해하려면 CRI를 먼저 알아야 한다. Docker가 CRI 비호환이라 번역 계층(shim)이 필요했고, 그 부담을 없앤 것이 핵심.

### 트레이드오프 관점
4. **스트리밍을 URL 위임으로 푼 설계의 영리함**
   - exec/attach를 kubelet이 직접 중계하면 병목이 된다. "스트리밍 서버 URL만 돌려주고 위임"함으로써 kubelet을 가볍게 유지. 인터페이스 설계에서 "직접 처리 vs 위임"의 좋은 예시.
