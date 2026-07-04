# The Almighty Pause Container - Pod는 어떻게 구현되는가

> 📌 강의 "쿠버네티스 흐름으로 이해하는 컨테이너"를 위한 고전 아티클 정리 (4/4)
> Pod라는 추상이 리눅스 위에서 **실제로 어떻게 구현되는가** — 보이지 않는 `pause` 컨테이너의 정체를 파헤칩니다.
> (1편의 namespace/cgroup, 2편의 PodSandbox 개념을 리눅스 레벨에서 잇는 마지막 퍼즐)

## 출처
- **아티클**: The Almighty Pause Container
- **저자/출처**: Ian Lewis (Google, Developer Advocate)
- **게재**: 2017-10-10
- **링크**: https://www.ianlewis.org/en/almighty-pause-container

---

## AI 요약

### 1. pause 컨테이너란? 어디서 보이나

쿠버네티스 노드에서 `docker ps`를 해보면, 내가 띄운 적 없는 `pause` 컨테이너들이 보입니다.

```
CONTAINER ID    IMAGE                                      COMMAND
3b45e983c859    gcr.io/google_containers/pause-amd64:3.0   "/pause"
dbfc35b00062    gcr.io/google_containers/pause-amd64:3.0   "/pause"
```

**Pod마다 하나씩** 존재하며, 그 Pod의 모든 컨테이너의 **"부모 컨테이너(parent container)"** 역할을 합니다. (2편의 CRI에서 본 **PodSandbox**의 Docker 런타임 구현체가 바로 이 pause 컨테이너)

### 2. 리눅스 네임스페이스 기초 — 공유의 메커니즘

pause 컨테이너를 이해하려면 namespace 공유 방식을 알아야 합니다.

- 리눅스에서 프로세스는 **부모로부터 namespace를 상속**받는다
- 새 namespace를 만들려면 `unshare`로 부모와 **분리(unshare)**:
  ```bash
  sudo unshare --pid --uts --ipc --mount -f chroot rootfs /bin/sh
  ```
- 이미 namespace 안에 있는 프로세스에 **합류**하려면 `setns` 시스템 콜 사용
- → 이 "합류" 메커니즘으로 한 Pod 안의 컨테이너들이 **namespace를 공유**한다

```
        ┌──────────────── Pod ────────────────┐
        │                                      │
        │   ┌─────────────┐  ← 먼저 생성        │
        │   │   pause     │     네트워크 NS,     │
        │   │  컨테이너    │     IPC NS 등을 "소유"│
        │   └──────┬──────┘                    │
        │          │ setns (namespace 합류)     │
        │     ┌────┴─────┬──────────┐          │
        │     ▼          ▼          ▼          │
        │ ┌───────┐  ┌───────┐  ┌───────┐      │
        │ │ nginx │  │ app   │  │ ...   │      │
        │ └───────┘  └───────┘  └───────┘      │
        │  모두 pause의 네트워크 NS 공유          │
        │  → 서로 localhost 로 통신             │
        └──────────────────────────────────────┘
```

### 3. pause 컨테이너의 두 가지 책임

**① namespace 공유의 기반 (앵커 역할)**
- pause가 **먼저** 네트워크 namespace를 만들고 잡아둔다. 다른 컨테이너들은 그 namespace에 합류한다.
- 직접 재현해보면:
  ```bash
  # pause가 네트워크/IPC namespace를 소유 (포트도 pause가 점유)
  docker run -d --name pause -p 8080:80 gcr.io/google_containers/pause-amd64:3.0

  # nginx가 pause의 namespace에 합류
  docker run -d --name nginx \
    --net=container:pause \
    --ipc=container:pause \
    --pid=container:pause nginx

  # ghost 앱도 같은 namespace에 합류 → nginx와 localhost:2368로 통신
  docker run -d --name ghost \
    --net=container:pause --ipc=container:pause \
    --pid=container:pause ghost
  ```
- **핵심**: 앱 컨테이너가 죽고 재시작해도 namespace(와 Pod IP)는 **pause가 계속 잡고 있어** 유지된다. namespace의 수명을 앱 컨테이너와 분리하는 안정적 앵커.

**② PID 1로서 좀비 프로세스 수확(reaping)**
- PID namespace 공유가 켜지면 pause가 그 Pod의 **PID 1**이 된다.
- 리눅스에서 PID 1은 고아가 된 자식 프로세스(좀비)를 거둬들일 책임이 있다. pause가 이를 대신한다.

### 4. pause 컨테이너의 실제 소스코드

놀랍도록 단순합니다. 하는 일은 "잠자며 신호만 처리"하는 것:

```c
static void sigreap(int signo) {
  // 좀비 프로세스를 모두 거둬들임 (non-blocking)
  while (waitpid(-1, NULL, WNOHANG) > 0);
}

static void sigdown(int signo) {
  psignal(signo, "Shutting down, got signal");
  exit(0);
}

int main() {
  // SIGCHLD가 오면 sigreap으로 좀비 수확
  if (sigaction(SIGCHLD, &(struct sigaction){.sa_handler = sigreap,
                                             .sa_flags = SA_NOCLDSTOP},
                NULL) < 0)
    return 3;
  for (;;)
    pause();   // 신호가 올 때까지 무한히 잠듦 (CPU 거의 0)
}
```

| 구성요소 | 역할 |
|----------|------|
| `pause()` 무한 루프 | 신호가 올 때까지 영원히 sleep → 자원 소모 거의 없음 |
| `sigreap` (SIGCHLD) | 자식이 종료될 때 `waitpid`로 좀비 수확 |
| `sigdown` (SIGTERM 등) | 종료 신호 시 깔끔하게 exit |

> 💡 이름 그대로 **"pause"** — 아무 일도 안 하고 잠들어 있는 것이 핵심 기능. 가볍고 안정적이어서 namespace의 영속적 앵커로 완벽하다.

### 5. 종합 — Pod가 리눅스 위에서 구현되는 방식

```
  쿠버네티스 API의 "Pod"
        │
        ▼  (kubelet → CRI → containerd)
  ① pause 컨테이너 생성  → 네트워크/IPC namespace 확보, Pod IP 점유
        │
        ▼
  ② 앱 컨테이너들이 setns로 pause의 namespace에 합류
        │
        ▼
  결과: 같은 IP/네트워크/IPC를 공유, localhost 통신,
        앱 컨테이너 재시작에도 namespace는 pause가 유지
```

---

## 내가 얻은 인사이트

### 구현 원리 관점
1. **"Pod는 추상이고, pause는 그 추상의 물리적 구현체다"**
   - 1편(Borg 논문)에서 Pod를 개념으로, 2편(CRI)에서 PodSandbox를 인터페이스로 배웠다면, pause 컨테이너는 그것이 **리눅스 위에서 실제로 어떻게 존재하는지**를 보여준다. "Pod가 네트워크를 공유한다"는 말의 실체가 바로 이 namespace 앵커다.

2. **수명 분리(lifecycle decoupling)가 안정성의 핵심**
   - 앱 컨테이너가 죽어도 Pod IP가 유지되는 이유: namespace를 앱이 아니라 **pause가 소유**하기 때문. "변하는 것(앱)과 변하지 않아야 하는 것(네트워크 정체성)을 분리"하는 설계는 어디서나 통하는 원칙이다.

### 리눅스 시스템 관점
3. **PID 1의 책임(좀비 수확)을 아무도 안 하면 생기는 문제**
   - 컨테이너 안에서 앱을 PID 1로 그냥 띄우면 좀비가 쌓일 수 있다. pause가 PID 1을 맡아 `waitpid`로 거둬들이는 것은, 일반 컨테이너에서 `tini`/`dumb-init` 같은 init이 필요한 이유와 정확히 같은 문제다.

### 설계 철학 관점
4. **"가장 단순한 것이 가장 강력하다"의 표본**
   - 수십 줄짜리 C 코드가 쿠버네티스 Pod의 토대다. 복잡한 기능 대신 "잠들어 namespace를 잡고, 좀비만 거둔다"는 단일 책임. 인프라 컴포넌트일수록 단순함이 곧 신뢰성임을 보여준다.
