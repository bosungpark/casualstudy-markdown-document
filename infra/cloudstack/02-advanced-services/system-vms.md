# System VMs — SSVM / CPVM / Virtual Router

> **CloudStack 인프라의 "보이지 않는 일꾼들". Zone 만들면 자동으로 떠서, 게스트망/콘솔/Secondary I/O 를 처리한다.**

OpenStack의 "Neutron L3 agent / DHCP agent / Octavia VM / noVNC proxy / Glance worker" 가 **3종의 작은 VM** 으로 통합된 셈.

> 출처: [Admin Guide — System VMs](https://docs.cloudstack.apache.org/en/latest/adminguide/systemvm.html) · [Virtual Router](https://docs.cloudstack.apache.org/en/latest/adminguide/virtual_machines/virtual_router.html).

---

## 1. 3종 한 컷

| System VM | 역할 | 개수 (Zone당) | 죽으면? |
|---|---|---|---|
| **Secondary Storage VM (SSVM)** | Secondary Storage I/O 매개 | 1 (보통) | 템플릿 다운로드/스냅샷 막힘 |
| **Console Proxy VM (CPVM)** | 웹 콘솔(noVNC) 프록시 | 1~N (콘솔 부하 따라) | UI에서 콘솔 못 봄 |
| **Virtual Router (VR)** | 게스트망의 라우터/DHCP/DNS/SNAT/PF/LB | **네트워크당 1** (Redundant 시 2) | 그 게스트망 통신 마비 |

→ **Zone이 살아있는 것 = SSVM/CPVM이 살아있는 것**.

---

## 2. SystemVM Template — 모든 System VM의 OS

3종 모두 같은 **systemvm template** (Debian 기반, 약 100MB) 을 OS로 쓴다.

```bash
$ cmk list templates templatefilter=featured
+--------------------------+----+
| name                     | id |
+--------------------------+----+
| systemvm-kvm-x86_64      | .. |
| systemvm-kvm-aarch64     | .. |   ← ARM (Apple Silicon)
+--------------------------+----+
```

→ **새 Zone 생성 시 가장 먼저 등록할 것**. SystemVM template 없으면 모든 게 막힘.

다운로드 위치: [download.cloudstack.org/systemvm/](http://download.cloudstack.org/systemvm/)

---

## 3. Secondary Storage VM (SSVM)

### 무엇을 하나

```
[Hypervisor Host]                  [SSVM]                    [Secondary]
       │                              │                          │
       │  "이 템플릿 줘"               │                          │
       │ ────────────────────────────►│                          │
       │                              │  NFS/S3 마운트            │
       │                              │ ────────────────────────►│
       │                              │  파일 다운로드            │
       │                              │ ◄────────────────────────│
       │  "Primary로 복사 완료"        │                          │
       │ ◄────────────────────────────│                          │
```

| SSVM이 매개하는 작업 |
|---|
| 템플릿 다운로드 (Secondary → Primary) |
| ISO 다운로드 |
| Volume 스냅샷 업로드 (Primary → Secondary) |
| Volume 복원 (Secondary → Primary) |
| Template 등록 시 URL 다운로드 |

### NIC 구성

```
SSVM:
  eth0  ─ Management Network (MS와 통신)
  eth1  ─ Public  (선택: 외부 URL 접근용)
  eth2  ─ Storage (Secondary 마운트)
```

### 안 죽으면 안 보이는 친구

```bash
$ cmk list systemvms
+----------+--------+--------+
| name     | type   | state  |
+----------+--------+--------+
| s-1-VM   | SSVM   | Running|
| v-2-VM   | CPVM   | Running|
+----------+--------+--------+

# 죽었으면
$ cmk stop systemvm id=<...>
$ cmk start systemvm id=<...>

# 또는 강제 재기동 (반드시 새 SSVM이 부팅됨)
$ cmk destroy systemvm id=<...>   # 자동 재생성
```

→ **SSVM은 disposable**. 죽으면 새 거 부팅. 메타데이터는 Secondary에 영속.

---

## 4. Console Proxy VM (CPVM)

### 무엇을 하나

```
[브라우저] ─HTTPS/WebSocket─► [CPVM] ─VNC/SPICE─► [Hypervisor Host의 VM 콘솔]
```

UI의 "Console" 버튼을 누르면:
1. MS가 CPVM URL을 발급 (서명된 1회용 URL)
2. 브라우저가 CPVM에 WebSocket 연결
3. CPVM이 실제 Host의 libvirt VNC 포트로 프록시

### 왜 프록시가 필요?

- Hypervisor Host의 VNC 포트는 보통 외부 노출 X (보안)
- VNC 포트 번호도 동적 (libvirt가 자동 할당)
- CPVM이 **단일 진입점 + 인증** 역할

### 부하 분산

콘솔 동시 사용자 많으면 **CPVM 추가 가능**:

```
Global Setting: consoleproxy.session.max = 10  (한 CPVM의 동시 세션)
                                                 → 초과 시 자동으로 추가 CPVM 부팅
```

---

## 5. Virtual Router (VR) — 게스트망의 만능 어플라이언스

### 어디 떠 있나

```
한 Isolated Network 또는 VPC 마다 → VR 1개 (Redundant 시 2개)

[Network-A]    [Network-B]    [VPC-X]
    │              │              │
   [VR-A]        [VR-B]        [VR-X]
```

→ 게스트망 100개면 VR 100개. **System VM이 가장 많이 떠 있는 종류**.

### 내부 서비스

```
[VR Linux Box]
    │
    ├─ dnsmasq        → DHCP, DNS forward
    ├─ iptables       → SNAT, Port Forward, Firewall, Static NAT
    ├─ HAProxy        → Load Balancer
    ├─ keepalived     → Redundant VR HA (VRRP)
    ├─ strongSwan     → Site-to-Site VPN
    ├─ Apache         → User Data 서빙 (169.254.169.254)
    └─ password server → cloud-init 비번 주입
```

→ 한 VM이 5~7개 서비스를 다 호스팅.

### NIC

```
VR (Isolated Network 케이스):
  eth0  ─ Guest    (게스트망 게이트웨이)
  eth1  ─ Public   (Source NAT, Public IP들)
  eth2  ─ Management (MS와 통신)
```

VPC의 경우 eth0이 여러 개 (각 Tier 마다).

### Redundant VR

> [Redundant Virtual Routers](https://docs.cloudstack.apache.org/en/latest/adminguide/virtual_machines/virtual_router.html#redundant-virtual-router).

```
[VR-Master] ── VRRP keepalive ── [VR-Backup]
    │ (active)                       │ (standby)
    └──────────► VIP (게스트망 GW) ◄────────┘

Master 죽으면 → Backup이 VIP 인수 → 1~3초 다운타임
```

Network Offering에서 "Redundant VR" 옵션 활성화로 켠다.

### 자주 쓰는 명령

```bash
# VR 목록
$ cmk list routers

# 재시작 (게스트망에 잠깐 영향)
$ cmk reboot router id=<...>

# 특정 게스트망의 VR 강제 재기동
$ cmk destroy router id=<...>
# → Network 재시작 시 자동 재생성

# Network 재시작 (cleanup=true)
$ cmk restart network id=<...> cleanup=true
```

---

## 6. System VM 부팅 흐름

```
[Zone 처음 활성화 / Network 처음 사용]
    │
    ▼
MS: SystemVM template 캐시 있나?
    │
    ├─ No: SSVM 생성에 SSVM 자체가 필요한데... 닭과 달걀!
    │   → Hypervisor Host가 직접 NFS Secondary 마운트해서 부트스트랩
    │
    ▼
SystemVM Offering 으로 VM 정의 (system_vm 테이블)
    │
    ▼
StoragePoolAllocator → Primary 결정
    │
    ▼
HostAllocator → Hypervisor Host 결정
    │
    ▼
Agent → libvirt: VR/SSVM/CPVM 부팅
    │
    ▼
System VM 부팅 → MS와 management network 연결 확인 → "Up"
```

---

## 7. 자주 밟는 지뢰

- **Zone 만들었는데 SSVM/CPVM 영원히 "Starting"** → SystemVM template 미등록 또는 잘못된 아키텍처(ARM에 x86 template). `cmk list templates templatefilter=featured` 확인.
- **VR이 Down → 게스트망 안 됨** → `cmk reboot router id=<...>`. 또는 Redundant VR 구성.
- **콘솔 클릭하면 흰 화면** → CPVM Down 또는 브라우저가 self-signed 인증서 차단. 인증서 trust 또는 CPVM 재기동.
- **Secondary Storage 마운트 실패** → SSVM이 NFS 서버에 접근 못 함. 보통 Network 분리 잘못됨. SSVM 콘솔에서 `mount`, `ping <NFS-IP>` 진단.
- **System VM이 부팅 시 메모리 부족** → SystemVM Offering이 너무 작음. `system.vm.serviceoffering` 글로벌 설정 또는 운영 환경에서 큰 offering 사용.

---

## 8. OpenStack 매핑

| OpenStack | CloudStack |
|---|---|
| Glance worker | SSVM |
| Nova noVNC proxy | CPVM |
| Neutron L3 agent | VR (라우팅, NAT) |
| Neutron DHCP agent | VR (dnsmasq) |
| Neutron metadata agent | VR (User Data 서빙) |
| Octavia VM | VR (LB Service 켜진 경우) |
| (분산) — 컨트롤 노드의 데몬들 | (집중) — Network 마다 VR VM |

흥미로운 차이: OpenStack OVN 시대에는 L3 agent가 분산(compute 노드마다)됐지만, CloudStack VR은 **여전히 네트워크당 1개의 VM**. 단순함이 강점.

---

## 다음

→ [vpc.md](./vpc.md): VR이 더 진화한 형태인 VPC.
→ [../05-deep-dives/virtual-router-internals.md](../05-deep-dives/virtual-router-internals.md): VR 내부 패킷 흐름.
→ [../04-operations/troubleshooting.md](../04-operations/troubleshooting.md): System VM 장애 진단.

---

## 공식 문서 레퍼런스

- [Admin Guide — System Virtual Machines](https://docs.cloudstack.apache.org/en/latest/adminguide/systemvm.html)
- [Virtual Router](https://docs.cloudstack.apache.org/en/latest/adminguide/virtual_machines/virtual_router.html)
- [Console Proxy](https://docs.cloudstack.apache.org/en/latest/adminguide/systemvm.html#console-proxy)
- [Secondary Storage VM](https://docs.cloudstack.apache.org/en/latest/adminguide/systemvm.html#secondary-storage-vm)
