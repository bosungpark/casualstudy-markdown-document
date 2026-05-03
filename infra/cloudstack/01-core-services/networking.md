# Networking — Basic Zone vs Advanced Zone, Network Offering, VPC

> **CloudStack 네트워킹은 Zone 생성 시점에 두 갈래로 나뉘고, 한 번 정하면 못 바꾼다.**

OpenStack의 Neutron이 ML2 plugin 으로 가시성을 추상화한다면, CloudStack은 **"Network Offering" 이라는 정책 객체**로 네트워크를 정의한다.

> 출처: [Admin Guide — Networking](https://docs.cloudstack.apache.org/en/latest/adminguide/networking.html) · [Networking and Traffic](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#networking-and-traffic).

---

## 1. 두 가지 Zone 모델

| | Basic Zone | Advanced Zone |
|---|---|---|
| 격리 메커니즘 | **Security Group** (L3/L4 규칙) | **VLAN / VXLAN / GRE / STT** |
| 게스트 IP | Pod 단위 평면 Subnet | Network 단위 Subnet (테넌트 사설망) |
| Public IP | Pod 안에서 같이 씀 (or 직접 할당) | Source NAT / Static NAT |
| L3 라우터 | 없음 (필요 시 외부) | **Virtual Router (System VM)** |
| 적합 시나리오 | AWS-classic 같은 단순 멀티테넌트 / 호스팅 | VPC가 필요한 사설/엔터프라이즈 |
| 변경 가능? | ❌ Zone 생성 시 결정, 변경 불가 | ❌ 동일 |

→ 학습/실습은 **Advanced Zone** 이 표준. Basic Zone은 단순한 호스팅 사업자용.

---

## 2. Traffic Type — 물리 네트워크 4종

> [Traffic Types](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#networking-and-traffic).

CloudStack은 **물리 네트워크에 4가지 트래픽 타입**을 매핑한다:

| Traffic | 용도 | 누가 씀 |
|---|---|---|
| **Management** | MS ↔ Hypervisor Agent / MS ↔ MySQL | 컨트롤 플레인 |
| **Public** | 인터넷 출구, Source NAT, Floating IP | VR, VM |
| **Guest** | VM 간 / 같은 게스트망 안 트래픽 | VR, VM |
| **Storage** | Primary Storage iSCSI/NFS/RBD | Host (옵션, Management과 합쳐도 됨) |

물리적으로는 NIC/VLAN을 분리해서 매핑. 학습용 단일 노드에서는 한 NIC에 다 묶기도 한다.

---

## 3. Network Offering — 네트워크의 메뉴판

OpenStack에는 없는 개념. **네트워크가 어떤 서비스를 제공하는지** 미리 패키지화.

```
[Network Offering: "Default Isolated"]
   └─ 제공 서비스:
       ├─ DHCP        → VR (dnsmasq)
       ├─ DNS         → VR (dnsmasq)
       ├─ Source NAT  → VR (iptables)
       ├─ Static NAT  → VR (iptables)
       ├─ Port Forward→ VR (iptables)
       ├─ Firewall    → VR (iptables)
       ├─ Load Balancer → VR (HAProxy)
       └─ User Data   → VR (169.254.169.254)

[Network Offering: "L2-only"]
   └─ 제공 서비스: (없음. 그냥 L2만)

[Network Offering: "VPC Tier"]
   └─ 제공 서비스: VPC Router 안에서 동작
```

→ "**이 네트워크에 들어오면 어떤 기능을 누리나**"가 Offering 으로 정해진다. 같은 Offering을 쓰는 모든 네트워크는 같은 기능 셋을 받는다.

---

## 4. Network 종류 — Advanced Zone

> [Networking Guide — Network Types](https://docs.cloudstack.apache.org/en/latest/adminguide/networking.html).

### Isolated Network (테넌트 사설망)

```
[VM-A] [VM-B] [VM-C]    ← 한 테넌트의 사설망
     \  |  /
      [VR] ← Source NAT, DHCP, DNS, Port Forward, LB
       │
       ▼
   [Public Network] ← 인터넷
```

- 테넌트당 자기만의 네트워크
- VLAN/VXLAN 으로 다른 테넌트와 격리
- VR이 게이트웨이 역할

### Shared Network

```
[Tenant-A's VM] [Tenant-B's VM] [Tenant-C's VM]
        \              |              /
                  [같은 Subnet]
```

- 여러 테넌트가 공유 (예: 회사 공용 사내망)
- IP는 풀에서 할당, 격리는 Security Group/방화벽 따로

### L2 Network

- IP/DHCP/라우팅 없음
- 그냥 L2 broadcast 도메인만 제공
- 테넌트가 자체 라우터를 띄울 때 유용

### VPC

- 여러 Tier(Subnet) + ACL + 단일 VPC Router
- AWS VPC와 의미가 같음
- 자세한 내용: [../02-advanced-services/vpc.md](../02-advanced-services/vpc.md)

---

## 5. Virtual Router (VR) — 게스트망의 만능 어플라이언스

> [Virtual Router](https://docs.cloudstack.apache.org/en/latest/adminguide/virtual_machines/virtual_router.html).

VR은 **CloudStack이 자동으로 부팅하는 System VM** (보통 ARM/x86용 작은 Linux 어플라이언스).

```
[VM] ─► [VR (eth0=guest, eth1=public, eth2=management)] ─► 인터넷
                │
                ├─ dnsmasq        (DHCP, DNS)
                ├─ iptables       (SNAT, Port Forward, Firewall)
                ├─ HAProxy        (LB)
                ├─ keepalived     (Redundant VR HA)
                └─ password server (cloud-init password 주입)
```

| 서비스 | 도구 |
|---|---|
| DHCP/DNS | dnsmasq |
| SNAT/PF/Firewall | iptables |
| LB | HAProxy |
| Site-to-site VPN | strongSwan |
| Redundant HA | keepalived (VRRP) |

→ "**OpenStack의 dhcp-agent + l3-agent + Octavia VM** 가 VR 1개로 합쳐진" 셈.

---

## 6. Public IP / Source NAT / Static NAT / Port Forward

```
[게스트 사설 IP: 10.1.1.5]
          │
          ▼
       [VR (Public IP: 203.0.113.10)]
          │
   ─ Source NAT:  outbound 시 모든 VM이 203.0.113.10 으로 나감
   ─ Static NAT:  하나의 VM ↔ 하나의 Public IP 1:1
   ─ Port Fwd:    203.0.113.11:80 → 10.1.1.5:80
   ─ LB:          203.0.113.12:80 → [VM-A:80, VM-B:80, ...]
```

Public IP는 **Network/VPC에 할당** → VR이 받음 → 위 4가지 기능 중 선택.

---

## 7. Security Group (Basic Zone)

Advanced Zone에선 SG 사용이 제한됨. **Basic Zone에서 격리의 핵심**.

```bash
$ cmk create securitygroup name=web
$ cmk authorize securitygroupingress \
    securitygroupname=web \
    protocol=tcp \
    startport=80 endport=80 \
    cidrlist=0.0.0.0/0
```

AWS Security Group과 같은 의미.

---

## 8. 손으로 해보기

```bash
# 사용 가능한 Network Offering
$ cmk list networkofferings state=Enabled

# Isolated Network 생성
$ cmk create network \
    zoneid=<...> \
    networkofferingid=<DefaultIsolatedNetworkOfferingWithSourceNatService> \
    name=tenant-net \
    displaytext="Tenant Net" \
    gateway=10.1.1.1 \
    netmask=255.255.255.0

# Public IP 할당
$ cmk associate ipaddress zoneid=<...> networkid=<...>

# Static NAT 설정
$ cmk enable staticnat virtualmachineid=<vmid> ipaddressid=<ipid>

# Port Forward
$ cmk create portforwardingrule \
    ipaddressid=<ipid> \
    privateport=22 publicport=22 \
    protocol=tcp \
    virtualmachineid=<vmid>
```

---

## 9. 자주 밟는 지뢰

- **VR이 안 떠서 네트워크 생성 후 VM이 IP 못 받음** → SSVM/CPVM/VR template 등록 안 됨. `Templates` UI 또는 [System VM 문서](../02-advanced-services/system-vms.md) 참고.
- **Source NAT 안 됨** → Public IP가 Network에 안 붙어 있음. `cmk list publicipaddresses` 로 확인.
- **VR 죽어 게스트망 마비** → `cmk restart router id=<vr-id>`. 또는 Redundant VR 구성.
- **Basic vs Advanced 변경하려 함** → ❌ 불가능. Zone을 새로 만들어야 함.
- **VLAN 풀 소진** → Advanced Zone에서 격리 VLAN ID 풀(`guestcidraddress` 등)을 미리 충분히 잡아두기.

---

## 10. OpenStack 매핑

| OpenStack | CloudStack |
|---|---|
| Neutron Network | Network |
| Subnet | Network 의 gateway/netmask 필드 |
| Router | Virtual Router (System VM) |
| Floating IP | Public IP + Static NAT |
| Security Group | Security Group (Basic Zone에서) / NetworkACL (VPC) |
| Octavia (LB) | Network Offering 의 LB Service (VR 안의 HAProxy) |
| OVN/OVS | Linux bridge / OVS (Network Offering이 정함) |
| ML2 plugin | Network Offering + Provider 조합 |

---

## 다음

→ [storage-primary-secondary.md](./storage-primary-secondary.md): VM의 디스크는 어떻게 모습되는지.
→ [../02-advanced-services/system-vms.md](../02-advanced-services/system-vms.md): VR/SSVM/CPVM 의 자세한 동작.
→ [../05-deep-dives/virtual-router-internals.md](../05-deep-dives/virtual-router-internals.md): VR 내부 패킷 흐름.

---

## 공식 문서 레퍼런스

- [Networking Concepts](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#networking-and-traffic)
- [Admin Guide — Networking](https://docs.cloudstack.apache.org/en/latest/adminguide/networking.html)
- [Network Offerings](https://docs.cloudstack.apache.org/en/latest/adminguide/networking.html#about-network-offerings)
- [Virtual Router](https://docs.cloudstack.apache.org/en/latest/adminguide/virtual_machines/virtual_router.html)
- [VPC](https://docs.cloudstack.apache.org/en/latest/adminguide/networking/vpc.html)
