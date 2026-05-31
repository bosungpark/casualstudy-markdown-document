# NFS 마운트 Hang 대응 - 서비스 멈춤 진단과 복구 가이드

## 출처
- **아티클**: NFS Hang Troubleshooting Guide
- **저자/출처**: warlord0blog (Stuff I'm Up To)
- **링크**: https://warlord0blog.wordpress.com/2025/06/22/nfs-hang-troubleshooting-guide/
- **보조 출처**:
  - Linux Journal — [How-To: Release Stuck NFS Mounts without a Reboot](https://www.linuxjournal.com/content/how-release-stuck-nfs-mounts-without-reboot)
  - Red Hat — [RHEL mount hangs: nfs: server not responding](https://access.redhat.com/solutions/28211)

---

## AI 요약

### 1. NFS Hang 문제란?

NFS(Network File System)는 네트워크 너머의 디스크를 마치 로컬 디스크처럼 마운트해서 쓰는 프로토콜이다. 문제는 **로컬 디스크와 달리 네트워크가 끊기거나 서버가 죽을 수 있다는 점**이다. 이때 NFS 클라이언트가 어떻게 동작하느냐에 따라 서비스 운명이 갈린다.

| 항목 | 로컬 디스크 | NFS 마운트 |
| --- | --- | --- |
| 실패 모드 | I/O 에러 즉시 반환 | **무한 대기 가능** (hard mount 기본값) |
| 프로세스 상태 | `R`, `S` | **`D` (uninterruptible sleep)** |
| `kill -9` | 동작함 | **동작 안 함** |
| 복구 | 디스크 교체 | umount / 네트워크 복구 / 재부팅 |

핵심 원인은 한 줄로 요약된다 — **"hard 마운트 옵션은 NFS 서버가 응답할 때까지 영원히 기다린다."**

### 2. 증상: 서비스가 hang 걸렸다는 신호

서버에 SSH 접속은 되지만 이런 증상이 보이면 NFS hang을 의심해야 한다.

```
┌─────────────────────────────────────────────────────┐
│  증상 체크리스트                                       │
├─────────────────────────────────────────────────────┤
│  □ ps aux 가 끝나지 않고 멈춤                          │
│  □ df 가 응답 없음                                    │
│  □ lsof 가 hang 걸림                                  │
│  □ 프로세스가 D 상태 (uninterruptible sleep)           │
│  □ kill -9 로도 프로세스가 안 죽음                     │
│  □ dmesg 에 "hung task timeout" 반복                 │
│  □ syslog 에 "nfs: server X not responding"          │
│  □ load average 가 비정상적으로 상승 (D 상태도 카운트)   │
└─────────────────────────────────────────────────────┘
```

특히 `load average` 가 폭증하는 게 인상적이다. CPU는 놀고 있는데 load가 100 넘게 찍히는 경우 — D 상태 프로세스가 쌓이고 있다는 신호다.

### 3. 왜 멈추는가? — Hard vs Soft Mount

NFS hang의 본질은 **마운트 옵션 선택**에 있다.

```
[hard mount] (기본값)
────────────────────────────────────────
App ──read()──> NFS Client ──RPC──> NFS Server (DOWN)
                    │
                    ├── 응답 없음
                    ├── 타임아웃 후 재시도
                    ├── 또 재시도
                    └── 무한 반복 (영원히)

  → App은 D 상태로 대기, kill 안 됨


[soft mount]
────────────────────────────────────────
App ──read()──> NFS Client ──RPC──> NFS Server (DOWN)
                    │
                    ├── timeo=30 (3초) 대기
                    ├── retrans=2 (2회 재시도)
                    └── EIO 에러 반환

  → App은 에러 받고 정상 종료/재시도 가능
```

| 옵션 | 동작 | 장점 | 단점 |
| --- | --- | --- | --- |
| **hard** (기본) | 무한 재시도 | 데이터 무결성 보장 | 서버 죽으면 서비스 hang |
| **soft** | 타임아웃 후 EIO | 서비스 살릴 수 있음 | 쓰기 중이면 데이터 손상 위험 |
| **hard + intr** | 무한 재시도 but Ctrl+C 가능 | 절충안 | 최신 커널에선 무시됨 |

> **실무 팁**: 읽기 전용(read-only) 마운트는 `soft`가 안전. 쓰기가 있는 마운트는 `hard` + 짧은 timeout + 모니터링이 정석.

#### 깊이 보기 ① — Hard mount는 stateless 설계의 논리적 귀결이다

Hard mount가 "기본값"이 된 이유는 보수성이 아니라, **stateless 서버 + 멱등성 RPC라는 설계 결정에서 자동 도출되는 결론**이기 때문이다.

NFSv2/v3는 "서버는 클라이언트 상태를 기억하지 않는다"는 원칙으로 설계됐다. 서버 재시작이 클라이언트에 투명해지는 대신, 클라이언트는 서버 무응답 시 그 요청이 도달했는지 알 수 없다. 이를 안전하게 처리하기 위해 모든 RPC를 **멱등(idempotent)** 으로 정의했다 — 같은 요청을 100번 보내도 결과가 1번 보낸 것과 동일하다 (`write`에 offset 명시, `append` 같은 비멱등 연산 부재 등).

멱등성이 보장되면, 응답 없는 요청에 대한 클라이언트의 합리적 선택은 두 가지로 좁혀진다:

| 선택지 | 의미 | 결과 |
| --- | --- | --- |
| 포기하고 EIO 반환 | 앱이 재시도 책임을 짐 | 멱등성 보장 활용 못함, 앱 복잡도↑ |
| **무한 재전송 (= hard)** | 커널이 끝까지 도달 보장 | 데이터 무결성 완벽, 단 서버 영구 다운 시 hang |

커널은 후자를 골랐다. **Hard mount의 hang은 버그가 아니라 "재시도가 안전한 작업에 한해 끝까지 책임진다"는 약속의 부작용**이다. 즉 "hard mount는 앱 개발자를 위한 안전망"을 한 겹 더 풀면, 정확히는 **"stateless 설계를 깨지 않으면서 데이터 무결성을 지키는 유일한 방법이 무한 대기였다"** 가 된다.

#### 깊이 보기 ② — D state는 왜 kill되지 않는가

`kill -9`가 D state 프로세스에 통하지 않는 이유는 시그널이 전달되지 않아서가 아니다. 시그널은 `task_struct`에 정상적으로 펜딩되지만, 프로세스가 **커널 자료구조의 락(VFS 락, inode 락, 페이지 캐시 락 등)을 잡은 상태**라 그대로 깨우면 락이 영구히 남아 시스템이 망가지기 때문이다.

Linux 커널의 sleep 상태는 세 가지다:

| 상태 | 표시 | 시그널 처리 | 사용처 |
| --- | --- | --- | --- |
| `TASK_INTERRUPTIBLE` | `S` | 전부 OK | 일반 read/select/poll |
| `TASK_UNINTERRUPTIBLE` | `D` | **전부 차단** | 커널 락 보유 중, 디스크 I/O 한가운데 |
| `TASK_KILLABLE` | `D` (구분 안 됨) | **SIGKILL만 OK** | NFS RPC 대기 등 (2008~, 커널 2.6.25) |

`TASK_KILLABLE`은 "락은 안 잡고 단순히 응답만 기다리는 구간"에 한해 SIGKILL을 받아들이도록 한 절충안이다. NFS 클라이언트도 이를 채택했지만, 실제 NFS read/write 흐름은 **KILLABLE 구간과 UNINTERRUPTIBLE 구간을 빠르게 오간다**:

```
NFS read() 내부 흐름:
  1. VFS 진입, 락 잡음        ← TASK_UNINTERRUPTIBLE
  2. RPC 패킷 큐잉            ← TASK_KILLABLE (여기서 kill -9 통함)
  3. 응답 받아 페이지 캐시 갱신  ← TASK_UNINTERRUPTIBLE
```

사용자가 `kill -9`를 친 그 순간이 어느 구간이냐에 따라 통하기도, 안 통하기도 한다. 서버가 영구 다운된 케이스에선 재시도 사이클이 락 잡는 구간을 자주 들락거리므로 잡기 어렵다.

> 본문이 언급한 "최신 커널에서 `intr` 옵션이 무시된다"는 정확히는 **"이제 기본이 KILLABLE이라 `intr`을 명시할 필요가 없다"** 는 뜻에 가깝다.

### 4. 진단: hang인지 어떻게 확인하나

서비스가 멈춘 것 같을 때 **NFS가 범인인지** 빠르게 분리해야 한다.

```bash
# (1) D 상태 프로세스 확인 — 여기 NFS 워커가 있으면 거의 확정
ps aux | awk '$8 ~ /D/ { print }'

# (2) 어떤 마운트인지 확인 (이 자체도 hang 가능)
mount | grep nfs

# (3) 네트워크 도달성 — 빠른 체크
ping -c 3 <nfs-server>
nc -zv <nfs-server> 2049    # NFS 포트

# (4) showmount 는 hang 위험 — 반드시 timeout
timeout 10 showmount -e <nfs-server>

# (5) 마운트 포인트 접근 테스트 — 반드시 timeout
timeout 5 ls /mnt/nfs-share

# (6) 어떤 프로세스가 hang 걸렸나
sudo lsof -n 2>/dev/null | grep /mnt/nfs-share
```

**중요 원칙**: NFS hang을 진단할 땐 **모든 명령에 `timeout`을 씌워라**. 진단하려고 친 명령이 hang 걸려서 터미널 하나 더 날리는 게 가장 흔한 실수다.

### 5. 복구: Reboot 없이 살리기

복구는 **순서가 중요하다**. 위에서부터 시도하고, 실패하면 다음 단계로.

```
┌──────────────────────────────────────────────────────┐
│ Step 1: NFS 서버 살릴 수 있나? (네트워크/서버 복구)      │
│         → 가능하면 가장 깨끗한 해결                    │
└──────────────────────────────────────────────────────┘
                       ↓ (서버 복구 불가)
┌──────────────────────────────────────────────────────┐
│ Step 2: systemd automount 정지                       │
│    sudo systemctl stop <mount>.automount             │
└──────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│ Step 3: Force umount                                 │
│    sudo umount -f /mnt/nfs-share                     │
└──────────────────────────────────────────────────────┘
                       ↓ (실패)
┌──────────────────────────────────────────────────────┐
│ Step 4: Lazy umount                                  │
│    sudo umount -l /mnt/nfs-share                     │
│    → 마운트 포인트만 분리, 진행 중 I/O는 백그라운드로     │
└──────────────────────────────────────────────────────┘
                       ↓ (그래도 D 상태 프로세스 남음)
┌──────────────────────────────────────────────────────┐
│ Step 5: 가짜 NFS 서버 트릭 (Linux Journal)             │
│    동일 IP를 다른 머신에 부여 → RST 응답 → hang 해제      │
└──────────────────────────────────────────────────────┘
                       ↓ (그래도 안 풀림)
┌──────────────────────────────────────────────────────┐
│ Step 6: Reboot — D 상태 프로세스는 kill 불가             │
└──────────────────────────────────────────────────────┘
```

**핵심 차이**: `umount -f` vs `umount -l`

| 명령 | 동작 | 언제 |
| --- | --- | --- |
| `umount -f` | 강제 언마운트, 진행 중 I/O에 EIO 반환 시도 | 서버가 진짜로 죽어서 응답 0% |
| `umount -l` (lazy) | 마운트 트리에서 즉시 분리, 참조 중인 fd는 그대로 | 새 프로세스 보호가 우선일 때 |

> **주의**: `umount -l`은 **새로운 접근을 차단할 뿐**, 이미 D 상태인 프로세스를 살려주진 않는다. 새 요청이 더 쌓이는 것을 막는 응급 조치다.

#### 깊이 보기 ③ — `umount -f`와 `-l`은 서로 다른 레이어에서 동작한다

위 표에 "강제 vs lazy"로 짧게 정리된 두 명령은 **건드리는 레이어 자체가 다르다.**

Linux의 마운트는 두 층으로 분리되어 있다:

- **Namespace 레이어**: `/mnt/nfs`라는 경로가 어떤 superblock을 가리키는지의 매핑
- **Superblock 레이어**: 실제 NFS 클라이언트 인스턴스 — RPC 연결, 캐시, 열린 fd. **Refcount가 0이 될 때까지 살아있다.**

```
  ┌──────────────────────────────────┐
  │ namespace                        │
  │   /mnt/nfs   ──→ ┐               │
  └──────────────────┼───────────────┘
                     ↓
                 [Superblock for NFS]
                     ├─ NFS client state (RPC, 캐시)
                     ├─ inode 들
                     ├─ open fd 들 (D state 프로세스가 보유)
                     └─ refcount: 마운트 + 열린 fd 수
```

이 분리를 알고 보면 두 명령의 차이가 명확해진다:

| 명령 | 커널 플래그 | 동작 레이어 | RPC 큐 청소 | D state 해제 |
| --- | --- | --- | --- | --- |
| `umount -f` | `MNT_FORCE` | **NFS 드라이버** (`nfs_umount_begin`) | ✓ `rpc_killall_tasks` 호출 | ✓ (깨울 수 있는 것만) |
| `umount -l` | `MNT_DETACH` | **VFS namespace만** | ✗ | ✗ |

`umount -l`은 namespace 트리에서만 마운트 항목을 제거할 뿐 **NFS 클라이언트에는 아무 말도 걸지 않는다.** D state 프로세스는 여전히 superblock 위의 RPC 큐에 매달려 있고, 그 superblock은 refcount > 0인 한 살아있다. 그래서 `umount -l`은 "새 접근 차단"일 뿐 "기존 hang 해소"가 아니다.

`umount -f`만이 NFS 드라이버를 거쳐 `rpc_killall_tasks()`를 호출하고, 대기 중인 RPC 작업에 `RPC_TASK_KILLED`를 표시한 뒤 `wake_up_process`로 D state를 풀어낸다. 단, RPC 작업이 "응답 대기" 단계가 아니라 "TCP 재전송 중" 같은 더 깊은 단계에 있으면 `-f`로도 깨우지 못한다 — 그 경우가 바로 다음 항목의 무대다.

#### 깊이 보기 ④ — 가짜 NFS 서버 트릭의 본질은 TCP 레이어다

Step 5의 "동일 IP를 다른 머신에 부여" 트릭(Linux Journal)은 NFS 프로토콜을 흉내내는 게 아니다. **TCP의 정상 동작(모르는 연결에 RST를 보내는 것)을 활용해 위층(RPC → NFS → 프로세스)을 일제히 깨우는 기법**이다.

먼저 hang의 진짜 원인을 짚어보면 — 서버 머신이 갑자기 전원을 잃거나 방화벽이 트래픽을 차단한 경우, 클라이언트의 TCP 소켓은 `ESTABLISHED` 상태로 굳는다. 패킷을 재전송해도 ACK도 RST도 오지 않는다. Linux의 기본 `tcp_retries2`는 15회로 약 13~30분 후 ETIMEDOUT이 나지만, NFS hard mount는 그걸 받자마자 **새 연결을 만들어 또 RPC를 보낸다.** 즉 hang의 본질은 "TCP가 죽은 연결을 죽었다고 확신할 신호를 받지 못함"이다.

가짜 서버는 이 신호를 만들어준다:

```
[원인 상태]
  클라 TCP: ESTABLISHED, src=client:54321, dst=server:2049
  ↓ retransmit
  패킷이 어둠 속으로 사라짐 → 영원히 반복

[트릭 적용 후]
  같은 IP의 가짜 머신이 LAN에 등장 (ip addr add + arping)
  ↓
  클라의 재전송 패킷이 가짜 머신에 도착
  ↓
  가짜 머신 TCP 스택: "이 src/dst 조합, 내 conntrack에 없음"
  ↓
  RST 자동 응답 (커널 기본 동작)
  ↓
  클라 TCP 소켓: ESTABLISHED → CLOSED 즉시 전환
  ↓
  RPC 클라이언트: 소켓 죽음 감지 → 대기 task 전부에 EIO + wake_up
  ↓
  D state 프로세스 깨어남, read()가 -1 EIO 반환
```

주목할 점 세 가지:

1. **가짜 머신에 nfsd가 떠있을 필요가 없다.** TCP 스택만 살아있으면 "모르는 연결에 RST"는 커널이 자동으로 한다. 단, OUTPUT 체인에서 RST를 막는 iptables 룰이 있으면 무력화된다.
2. **UDP NFS에는 통하지 않는다.** UDP는 stateless라 "이 연결 모름"이라는 개념 자체가 없다 — RST 같은 명시적 종료 신호가 나오지 않는다.
3. **본질은 레이어를 한 칸 더 내려간 것이다.** NFS 레이어에서 풀려고 하면 어려운 hang을, TCP 레이어의 RST 한 방으로 끊어낸다.

> 가짜 서버는 "응답하는 척"이 아니라 **"죽은 서버가 마지막으로 했어야 할 일(연결 정리)을 대신 해주는 것"** 이다. 분산 시스템 디자인에서 "프로토콜 레이어를 거꾸로 활용한" 대표 사례.

#### 깊이 보기 ⑤ — 종합: 레이어별 탈출 전략

지금까지의 복구 단계를 레이어 관점으로 다시 정리하면, NFS hang 대응은 **"위 레이어에서 풀어보고, 안 되면 한 칸 아래로 내려간다"** 는 원칙으로 압축된다.

```
[Layer 5] 앱            : 재시도, 백오프  (soft mount일 때만 가능)
   ↓ 안 풀리면
[Layer 4] VFS namespace : umount -l       (새 접근만 차단, hang 해소 X)
   ↓
[Layer 3] NFS 드라이버  : umount -f       (rpc_killall_tasks → EIO)
   ↓
[Layer 2] TCP           : 가짜 서버 RST   (소켓 자체를 끊음)
   ↓
[Layer 1] OS            : Reboot          (최종 카드)
```

각 단계는 위 단계보다 **더 강력하지만 더 둔탁하다.** 위에서부터 시도하는 게 원칙이고, NFSv4 환경이라도 lease/delegation 회수가 막힌 케이스에선 결국 이 사다리를 타고 내려가게 된다.

### 6. NFS 프로토콜의 진화 — NFSv4가 hang을 어떻게 바꿨나

NFSv4(2003)는 NFSv2/v3의 stateless 원칙을 폐기하고 **lease 기반 stateful 설계**로 전환했다. 동기는 (1) NLM 별도 프로토콜 없이 락 통합, (2) close-to-open 일관성을 위한 GETATTR 폭증 해소, (3) 단일 포트(2049/tcp)로 방화벽 친화성 확보였다. 이 결정이 hang 문제에 미친 영향은 양면적이다.

**Hang이 줄어든 측면**

| 메커니즘 | 효과 |
| --- | --- |
| **Lease + RENEW heartbeat** | 클라가 hang 걸려 lease(보통 60초)간 RENEW가 없으면 서버가 그 클라의 락/state 자동 해제 → 다른 클라가 영향받지 않음 |
| **Delegation** | 서버가 단독 사용 중인 클라에 권한 위임 → 클라가 로컬 캐시로 read/write 처리, RPC 자체가 발생하지 않음 |
| **단일 포트(2049/tcp)** | 옛 NLM, rpcbind, mountd 등 다중 데몬 의존 제거 → 장애 표면 축소 |

**Hang의 새 입구**

| 시나리오 | 메커니즘 |
| --- | --- |
| **CLOSE hang** | v3의 `close()`는 로컬 작업, v4는 CLOSE RPC 필요 → `lsof` 등 진단 도구도 hang 위험 증가 |
| **Delegation 회수 hang** | 클라 A가 delegation 보유 중 B가 접근 → 서버가 A에게 회수 요청 → A의 네트워크 단절 시 A의 D state로 B까지 묶임 |
| **Grace period 대기** | 서버 재부팅 후 ~90초간 옛 클라의 state reclaim만 허용, 새 락 요청은 `NFS4ERR_GRACE` 받고 대기 |

**구조적 변화**

Stateless의 "구조적 멱등성"은 NFSv4.1의 **세션 + slot/sequence number** 메커니즘으로 대체됐다. 모든 RPC에 시퀀스 번호를 붙이고, 서버는 같은 시퀀스를 보면 재실행하지 않고 캐시된 응답을 반환한다. Hard mount의 "무한 재전송 안전성"이 다른 방식으로 재구성된 것이다.

> v4는 **hang을 없앤 게 아니라 분포를 바꿨다.** 영향 범위는 좁아졌지만(lease로 클라 간 격리), 새 stateful 연산이 새 hang 입구가 됐다. NFS의 30년 진화는 "네트워크가 죽었는지 느린지 끝까지 알 수 없다"는 본질적 한계를 점점 더 정교한 안전망으로 감싸온 역사다.

### 7. 예방: fstab 옵션 설계

대응보다 예방이 항상 낫다. 권장 fstab 옵션은 다음과 같다.

```bash
# 권장 설정 (서비스 가용성 우선)
<server>:/export  /mnt/nfs  nfs  \
    rw,\
    soft,\                          # 무한 대기 금지
    timeo=30,\                      # 3초 타임아웃 (단위: 0.1초)
    retrans=2,\                     # 2회 재시도
    bg,\                            # 부팅 시 마운트 실패해도 백그라운드
    _netdev,\                       # 네트워크 준비 후 마운트
    nofail,\                        # 마운트 실패해도 부팅 진행
    x-systemd.automount,\           # 접근 시점에 마운트 (lazy)
    x-systemd.mount-timeout=30      # systemd 단위 타임아웃
    0 0
```

| 옵션 | 효과 | 권장 이유 |
| --- | --- | --- |
| `soft` | hang 회피 | 서비스 가용성 |
| `timeo=30` | 빠른 실패 감지 | 기본값(600=60초)은 너무 김 |
| `retrans=2` | 빠른 포기 | 일시적 깜빡임은 재시도, 영구 장애는 빠른 포기 |
| `bg` | 부팅 봉인 방지 | mount 실패로 부팅 멈추는 사고 방지 |
| `_netdev` | 의존성 명시 | network-online.target 이후 마운트 |
| `nofail` | 부팅 봉인 방지 | NFS 서버 다운 시에도 OS 부팅 |
| `x-systemd.automount` | 지연 마운트 | 접근 안 하면 마운트 자체를 안 함 |

### 8. 운영 관점: 모니터링과 알림

NFS hang은 **터지면 늦다**. 미리 감지하는 게 핵심이다.

```bash
# 모니터링 항목
─────────────────────────────────────────────────
1. D 상태 프로세스 카운트
   ps -eo stat | grep -c '^D'

2. NFS 마운트 응답시간 (timeout 0.5초 체크)
   timeout 0.5 stat /mnt/nfs-share/.healthcheck

3. nfsstat 의 retrans 비율
   nfsstat -c | grep retrans

4. dmesg 의 "nfs: server X not responding"
   journalctl -k | grep -i "not responding"

5. NFS 서버 측 nfsd 스레드 상태
   ps aux | grep nfsd
```

---

## 내가 얻은 인사이트

### 분산 시스템 설계 관점

1. **"투명한 네트워크 디스크"는 환상이다**
   - NFS는 로컬 디스크인 척하지만, 네트워크의 모든 실패 모드를 그대로 떠안는다. POSIX API(`read`/`write`)는 네트워크 에러를 표현할 어휘가 빈약하다 — 그래서 NFS는 "영원히 기다림" 또는 "EIO" 둘 중 하나로 떨어뜨릴 수밖에 없다.
   - 추상화의 누수(leaky abstraction)가 가장 비싸게 새는 지점이다.

2. **Hard mount는 "데이터 안전 > 가용성"의 정치적 선택**
   - 기본값이 hard인 이유는 RPC의 멱등성 가정 때문이다. 쓰기 중에 클라이언트가 EIO를 받으면 "다시 보낼까 말까" 결정을 앱이 해야 하는데, 대부분의 앱은 그런 로직이 없다. 그래서 커널이 대신 "끝까지 보낸다"고 결정해버린 게 hard mount.
   - 즉, **hard mount는 앱 개발자를 위한 안전망**이지 운영자를 위한 게 아니다.

### SRE/운영 관점

3. **D 상태는 "kill 불가" 라기보다 "scheduler가 못 깨움"**
   - `kill -9`가 안 통하는 건 시그널 자체가 안 가는 게 아니라, 프로세스가 커널 I/O 대기 큐에서 빠지지 않기 때문이다. 빠지려면 NFS 클라이언트가 응답을 받거나 타임아웃해야 하는데, hard mount는 타임아웃이 없다.
   - 그래서 **유일한 깨우는 방법이 "NFS 서버가 응답하는 척" 시키는 것**(Linux Journal의 가짜 IP 트릭). 발상이 흥미롭다.

4. **fstab의 `_netdev`와 `nofail`은 "부팅 봉인" 방지의 핵심**
   - NFS 서버가 다운된 상태에서 클라이언트를 재부팅했더니 부팅이 안 되는 사고 — 이게 가장 흔한 2차 재해다. `nofail` 한 줄이 새벽 3시의 출동을 막아준다.
   - 운영 fstab을 짤 때 "정상 케이스가 잘 도는가"보다 "장애 케이스에 OS가 살아남는가"를 먼저 본다.

5. **`timeout` 명령은 SRE의 친구**
   - 진단 도구가 진단 대상에 hang 걸리는 건 운영의 가장 큰 함정. `timeout 5 ls /mnt/...` 패턴을 몸에 익혀야 한다.
   - 같은 맥락에서 헬스체크 스크립트에 `timeout`이 없으면 그 헬스체크가 hang 걸려 알람이 안 울리는 시나리오가 발생한다.

### 아키텍처 관점

6. **NFS는 "가능하면 안 쓰는" 게 가장 안전하다**
   - 컨테이너/쿠버네티스 시대에는 PV/PVC, S3 mount, ReadWriteOnce 블록 스토리지 등 대안이 많다. NFS의 ReadWriteMany 매력 때문에 쓰지만, **"누가 NFS 서버를 운영하는가"가 항상 SPOF 후보**다.
   - 굳이 쓴다면 (a) 읽기 전용 + soft mount, (b) 쓰기 필요 시 짧은 timeout + 앱 레벨 재시도, 둘 중 하나로 가둬야 한다.

7. **"hang"은 가장 진단하기 어려운 장애 유형**
   - 크래시는 로그를 남기고, 느림은 메트릭이 잡지만, hang은 **메트릭 수집 자체가 hang 걸린다**. 그래서 hang을 다루는 시스템은 항상 "외부 관찰자(external observer)"가 필요하다 — pingdom, blackbox exporter, 별도 헬스체크 노드 등.
   - 모니터링 시스템을 모니터링 대상과 같은 NFS에 올려두는 실수만 안 해도 절반은 산다.

> **한 줄 통찰**: NFS hang은 단일 버그가 아니라 **stateless 설계 → 무한 재시도 → 커널 락 안전성 → VFS/NFS/TCP 레이어 분리**가 한 줄로 꿰어진 구조다. 본문의 운영 가이드를 외우기보다, 어느 레이어에서 무슨 일이 일어나는지 그림이 그려져야 — 새로운 상황에서도 어느 사다리 칸을 내려갈지 판단할 수 있다.
