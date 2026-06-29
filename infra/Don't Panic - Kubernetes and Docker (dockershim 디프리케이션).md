# Don't Panic - Kubernetes and Docker (dockershim 디프리케이션)

## 출처
- **아티클**: Don't Panic: Kubernetes and Docker
- **저자/출처**: Kubernetes Blog (공식)
- **게재**: 2020-12-02
- **링크**: https://kubernetes.io/blog/2020/12/02/dont-panic-kubernetes-and-docker/

---

## AI 요약

### 1. 무엇이 디프리케이션되는가 — Docker가 아니라 dockershim

2020년 "쿠버네티스가 Docker 지원을 중단한다"는 소식에 큰 혼란이 있었습니다. 이 글의 핵심 메시지:

> **버려지는 것은 "런타임으로서의 Docker"(정확히는 dockershim)이지, "Docker 이미지"나 "개발 도구 Docker"가 아니다.**

- v1.20부터 **컨테이너 런타임으로서의 Docker**가 디프리케이션 → **dockershim**은 v1.24에서 제거
- **`docker build`로 만든 이미지는 모든 CRI 런타임에서 그대로 동작** (변하지 않음)

### 2. "Docker"는 하나가 아니다 — 개발 도구 vs 런타임

혼란의 근원: **"Docker"는 단일 제품이 아니라 전체 기술 스택**입니다. 그 안에 이미 `containerd`라는 고수준 런타임이 들어 있습니다.

```
┌───────────────────── "Docker" 라는 기술 스택 ─────────────────────┐
│                                                                  │
│   docker CLI  ──▶  Docker daemon (dockerd)                       │
│   (개발 도구)         │                                            │
│   build/run         ├──▶  이미지 빌드, 네트워크, 볼륨 관리 등         │
│   ✅ 계속 사용 가능     │                                            │
│                     └──▶  containerd  ──▶  runc  ──▶  컨테이너      │
│                          (고수준 런타임)   (OCI)                    │
│                          ▲                                        │
│                          └─ 쿠버네티스가 진짜로 필요한 부분            │
└──────────────────────────────────────────────────────────────────┘
```

| Docker의 측면 | 상태 | 설명 |
|---------------|------|------|
| **개발 도구** (`docker build`/`docker run`) | ✅ 계속 지원 | Dockerfile로 이미지 빌드는 여전히 표준 |
| **런타임으로서의 Docker** | ⚠️ 디프리케이션 | 쿠버네티스 노드 안에서 이미지를 실행하는 부분 |

핵심: **Docker는 쿠버네티스 안에 박혀 돌도록 설계된 적이 없다.** 그리고 **Docker는 CRI 비호환**이다.

### 3. dockershim이란? 왜 부담인가

**dockershim = 쿠버네티스와 Docker 사이의 번역 어댑터**입니다.

```
[ Docker 런타임을 쓸 때 — 불필요한 우회 ]

  kubelet ──CRI──▶ dockershim ──▶ Docker(dockerd) ──▶ containerd ──▶ runc
                   ▲                                     ▲
                   │ Docker가 CRI 비호환이라              │ 정작 필요한 건
                   │ 끼워넣은 번역 계층                    │ 이 containerd
                   └─ "유지보수해야 하고, 깨질 수 있는 또 하나의 것"

[ containerd를 직접 쓸 때 — 우회 제거 ]

  kubelet ──CRI──▶ containerd ──▶ runc      ← shim도 dockerd도 불필요
```

dockershim이 부담인 이유:
- Docker가 CRI를 따랐다면 shim 자체가 필요 없었음 ("If it were CRI-compliant, we wouldn't need the shim")
- **유지보수해야 하고 고장날 수 있는 또 하나의 컴포넌트** → 불필요한 복잡성
- 제거하면 쿠버네티스 아키텍처가 단순해짐 (비표준 통합점 제거)

### 4. 왜 Docker 이미지는 계속 동작하나 — OCI 표준

`docker build`로 만든 이미지는 사실 **OCI(Open Container Initiative) 이미지**라는 표준 포맷입니다.

```
   docker build  ──▶  OCI 이미지 (표준 포맷, 런타임에 종속 X)
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   containerd           CRI-O            (모든 CRI 런타임)
   이미지 pull/run 가능   pull/run 가능     pull/run 가능
```

- 이미지(산출물)는 런타임과 분리된 **이식 가능한 표준** → 디프리케이션이 덜 파괴적인 이유

### 5. containerd와 CRI-O

Docker 런타임을 대체하는 **CRI 호환 런타임들**:

| 런타임 | 특징 |
|--------|------|
| **containerd** | 원래 Docker 스택의 일부. 이미 CRI 호환 → shim 없이 kubelet이 직접 사용 |
| **CRI-O** | 쿠버네티스 전용으로 설계된 경량 런타임 |

관계: Docker는 내부적으로 containerd를 쓴다. dockershim 제거 = Docker라는 껍데기를 건너뛰고 **containerd를 직접** 쓰는 것.

### 6. 사용자를 위한 실무 조언

| 대상 | 해야 할 일 |
|------|-----------|
| **일반 사용자** | 대부분 즉시 바뀌는 것 없음. `docker build` 계속 사용 |
| **관리형 K8s (EKS/GKE/AKS)** | 워커 노드가 지원되는 CRI 런타임을 쓰는지 제공자와 확인 |
| **자체 관리 클러스터** | v1.20에서 Docker 디프리케이션 경고 → containerd/CRI-O로 마이그레이션 계획 |

⚠️ **주의할 패턴 — "Docker in Docker"**: Pod 안에서 `/var/run/docker.sock`(Docker 소켓)에 의존해 이미지를 빌드하던 워크플로우는 영향을 받음. 대안:
- **Kaniko**, **img**, **Buildah** 등으로 전환

> **결론**: 이것은 **런타임 구현 세부사항의 변경**일 뿐, Docker나 Docker 이미지의 죽음이 아니다. 오히려 비표준 통합점(dockershim)을 없애 아키텍처를 개선한 것.

---

## 내가 얻은 인사이트

### 개념 정리 관점
1. **"Docker = 하나의 제품"이라는 착각이 모든 혼란의 원인이었다**
   - Docker는 CLI + daemon + containerd + runc로 이어지는 **스택**이다. "런타임으로서의 Docker"와 "개발 도구로서의 Docker"를 분리하는 순간 디프리케이션이 전혀 무섭지 않다. 용어를 정확히 쪼개는 것이 곧 이해다.

2. **이미지(OCI)와 런타임(CRI)의 분리가 이식성의 핵심**
   - "빌드는 Docker로, 실행은 containerd로"가 가능한 이유는 OCI라는 표준 이미지 포맷 덕분이다. 산출물 표준화 vs 실행 표준화를 분리한 설계.

### 아키텍처 관점
3. **dockershim 제거는 "추상화 계층 줄이기"의 교과서적 사례**
   - kubelet→dockershim→dockerd→containerd→runc 라는 5단 우회를, kubelet→containerd→runc로 줄였다. 불필요한 번역 계층은 유지보수 비용이자 장애 지점이다. "중간 어댑터는 표준이 정착하면 제거 대상"이라는 교훈.

### 실무 관점
4. **CI/CD의 "Docker in Docker"가 진짜 영향권이었다**
   - 클러스터 안에서 이미지를 빌드하던 파이프라인은 docker.sock 의존을 버리고 Kaniko/Buildah로 가야 한다. 디프리케이션의 실질적 충격은 런타임이 아니라 빌드 워크플로우에 있었다는 점이 흥미롭다.
