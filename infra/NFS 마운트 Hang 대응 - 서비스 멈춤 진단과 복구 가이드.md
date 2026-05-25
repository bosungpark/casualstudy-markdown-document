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

### 6. 예방: fstab 옵션 설계

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

### 7. 운영 관점: 모니터링과 알림

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
