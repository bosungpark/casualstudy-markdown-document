# Virtual Router Internals — 패킷이 어떻게 흐르나

> **VR이 부팅하면서 무엇을 하고, 게스트망 패킷이 어떻게 라우팅/NAT 되는지.**

OpenStack의 OVN/L3 agent 가 분산 처리한다면, CloudStack은 **각 게스트망마다 작은 Linux VM 1개**가 모든 일을 한다.

> 출처: [Admin Guide — Virtual Router](https://docs.cloudstack.apache.org/en/latest/adminguide/virtual_machines/virtual_router.html) · [소스](https://github.com/apache/cloudstack/tree/main/systemvm).

---

## 1. VR이란 정확히 무엇인가

```
[VR Linux Box (Debian 기반 SystemVM Template)]
   ├─ kernel + minimal userland
   ├─ dnsmasq            (DHCP, DNS forward)
   ├─ iptables           (SNAT, Port Forward, Firewall, Static NAT)
   ├─ HAProxy            (Load Balancer)
   ├─ keepalived         (Redundant VR — VRRP)
   ├─ strongSwan         (IPsec for Site-to-Site VPN)
   ├─ Apache             (User Data 서빙)
   └─ Cloudstack scripts (MS 명령 받아 적용)
       /opt/cloud/bin/
```

→ **하나의 게스트망이 만들어지면 자동으로 부팅**.

---

## 2. VR 부팅 흐름

```
[Network 생성] (사용자가 createNetwork 호출)
    ▼
[MS]: 이 Network에 VR이 필요한가?  (Network Offering의 Service 보고)
    ▼ Yes
[NetworkOrchestrator]:
    ├─ DB: domain_router 행 생성 (state=Allocated)
    ├─ DeploymentPlanner: 어느 호스트?
    ├─ Primary 결정
    └─ 부팅 명령 → Agent
    ▼
[Agent]: libvirt VM 정의 → 부팅
    ├─ rootfs = SystemVM template clone
    └─ NICs:
       eth0 → guest network bridge
       eth1 → public network bridge (있으면)
       eth2 → management bridge (MS와 통신)
    ▼
[VR 부팅 후]:
    ├─ /opt/cloud/bin/cs_init  실행 (initial config)
    ├─ MS와 management network로 핸드셰이크
    └─ MS가 services config push (DHCP/iptables/HAProxy)
    ▼
[VR Running] → state=Running
```

---

## 3. NIC 구성 — Isolated Network 케이스

```
VR:
  eth0  ─ Guest Network    10.1.1.1/24    (게스트망 게이트웨이)
  eth1  ─ Public Network   203.0.113.10/24 (인터넷 출구)
  eth2  ─ Management       192.168.0.5/24 (MS와 통신)
```

각 NIC은 호스트의 **bridge** 에 연결 (`cloudbr0`, `cloudbrPub` 등).

---

## 4. 게스트망 패킷 흐름 — Outbound (인터넷 가기)

```
[VM 10.1.1.5]
    │ default GW: 10.1.1.1 (= VR eth0)
    ▼
[VR eth0]
    │
    ▼ iptables: -t nat POSTROUTING -o eth1 -j SNAT --to 203.0.113.10
    │
[VR eth1]
    │
    ▼ libvirt bridge → 물리 NIC → 인터넷
```

iptables 규칙 (실제 형태):

```bash
# VR 안에서
$ iptables -t nat -L POSTROUTING -n -v
Chain POSTROUTING (policy ACCEPT)
target     prot opt source       destination
SNAT       all  --  10.1.1.0/24  0.0.0.0/0   to:203.0.113.10
```

→ **모든 게스트망 outbound 가 VR의 Public IP로 마스커레이드**.

---

## 5. Inbound — Port Forwarding

```
외부 → 203.0.113.10:80 (VR eth1)
    ▼ iptables -t nat PREROUTING -p tcp --dport 80 -j DNAT --to 10.1.1.5:80
    ▼ FORWARD chain
[VR eth0]
    ▼
[VM 10.1.1.5:80]
```

PF 규칙은 사용자가 `cmk create portforwardingrule` → MS가 VR에 push.

---

## 6. Static NAT — 1:1

```
외부 ↔ 203.0.113.20 ↔ VR ↔ 10.1.1.5
```

iptables:
```
PREROUTING:  -d 203.0.113.20 -j DNAT --to 10.1.1.5
POSTROUTING: -s 10.1.1.5 -j SNAT --to 203.0.113.20
```

VM이 외부에 1:1 노출. AWS Elastic IP와 의미 같음.

---

## 7. Load Balancer — HAProxy

VR 안에 HAProxy 데몬:

```
$ cat /etc/haproxy/haproxy.cfg
frontend lb-frontend
    bind 203.0.113.30:80
    default_backend lb-backend

backend lb-backend
    balance roundrobin
    server vm1 10.1.1.5:80 check
    server vm2 10.1.1.6:80 check
```

→ Public IP `203.0.113.30:80` 으로 들어오면 두 VM에 분산.

LB 룰 추가/제거 시 MS가 cfg 재생성 후 HAProxy reload.

---

## 8. DHCP / DNS — dnsmasq

```
$ cat /etc/dnsmasq.d/cloud.conf
dhcp-range=10.1.1.50,10.1.1.250,12h
dhcp-option=option:router,10.1.1.1
dhcp-option=option:dns-server,10.1.1.1
dhcp-host=02:00:00:00:00:01,10.1.1.5,vm1   # VR이 MS에서 받아 적은 정적 매핑

# DNS forward
server=8.8.8.8
local=/cs.internal/
```

→ **VR이 자기 게스트망의 DHCP 서버이자 DNS 캐시**.

---

## 9. User Data — 169.254.169.254

```
[VM 10.1.1.5]
   │ HTTP GET http://169.254.169.254/latest/user-data
   ▼
[VR (route to 169.254.169.254)]
   │
   ▼
[VR의 Apache]: /opt/cloud/bin/userdata 에서 응답
```

→ AWS의 IMDS 와 같은 의미. cloud-init 이 사용.

VR이 169.254.169.254 IP를 자기 인터페이스 별칭으로 갖고 있음.

---

## 10. Redundant VR — VRRP

> [Redundant Virtual Routers](https://docs.cloudstack.apache.org/en/latest/adminguide/virtual_machines/virtual_router.html#redundant-virtual-router).

```
[VR-Master (Active)]   ←  VRRP keepalive packets  →  [VR-Backup (Standby)]
        │ 10.1.1.1 (VIP)                                  │ 10.1.1.2
        ▼                                                 ▼
   게스트망 ─────────────────────────────────────────────
```

- VRRP advertisement 매 1초
- Master 죽음 → 3초 안에 Backup이 VIP 인수
- iptables 룰은 **conntrackd** 로 동기화 (옵션)

```
keepalived.conf (VR 안):
vrrp_instance V_1 {
    state MASTER
    interface eth0
    virtual_router_id 1
    priority 100
    authentication { ... }
    virtual_ipaddress {
        10.1.1.1
    }
}
```

---

## 11. VPC Router 의 차이

```
[VPC Router]
   eth0 (없음 — 단일 게스트 인터페이스 X)
   eth1 → Public
   eth2 → Management
   eth3 → Tier-1 (10.0.1.0/24)   ← VPC의 Tier마다 NIC 추가
   eth4 → Tier-2 (10.0.2.0/24)
   eth5 → Tier-3 (10.0.3.0/24)
```

- 한 라우터가 **여러 Tier** 의 게이트웨이
- Tier 간 직접 라우팅 (Public IP 안 거침)
- Network ACL 적용 (per-Tier iptables FORWARD chain)

---

## 12. MS ↔ VR 명령 채널

```
[MS]
   │ TLS RPC (8250)
   ▼
[Agent on Hypervisor Host]
   │ libvirt console / SSH (10.1.1.x)
   ▼
[VR's /opt/cloud/bin/* scripts]
   │
   ▼
iptables / dnsmasq / haproxy 재구성
```

VR은 MS와 직접 TCP/IP 통신하지 않는다. **Agent가 매개**:
- Agent가 host에서 VR의 콘솔에 connect
- 또는 management network 위 SSH

```bash
# MS의 SSH 키
$ ls /var/lib/cloudstack/management/.ssh/
id_rsa.cloud   id_rsa.cloud.pub
```

이 키로 Agent가 VR에 SSH 후 cfg 파일 푸시 + 데몬 reload.

---

## 13. VR 디버깅

```bash
# VR 목록
$ cmk list routers

# VR에 직접 SSH (MS의 SSH key 사용)
$ ssh -i /var/lib/cloudstack/management/.ssh/id_rsa.cloud root@<VR-IP>

# 안에서:
$ ip a
$ iptables -t nat -L -n -v
$ cat /etc/dnsmasq.d/cloud.conf
$ cat /etc/haproxy/haproxy.cfg
$ tail -f /var/log/cloud.log
$ tail -f /var/log/messages
```

⚠️ VR에 직접 변경하면 **다음 cfg push 시 덮어쓰임**. 운영 변경은 MS의 API/Network Offering 통해서.

---

## 14. 자주 밟는 지뢰

- **VR 죽으면 그 게스트망 마비** → Redundant VR 또는 빠른 자동 재기동.
- **conntrackd 미설정 → failover 시 기존 connection 끊김** → "Auto-failover with stateful Redundant" 옵션.
- **iptables NAT 풀 한계** → 고부하 게스트망에서 conntrack table size 늘리기.
- **VR 재기동 시 게스트 DHCP lease 분실** → 짧은 lease 시간으로 빠르게 재할당.

---

## 15. OpenStack OVN과 비교

| | CloudStack VR | OpenStack OVN |
|---|---|---|
| 위치 | 게스트망마다 VM 1개 (집중) | compute 노드마다 ovn-controller (분산) |
| 라우팅 | iptables in VM | OpenFlow rules in OVS |
| DHCP | dnsmasq in VM | OVN-managed flows |
| LB | HAProxy in VM | Octavia (별도 VM) 또는 OVN LB |
| HA | keepalived (VRRP) | OVN의 distributed gateway |
| 디버깅 | VR에 SSH | ovn-trace, ovn-sbctl |
| 부하 한계 | VR VM의 CPU/RAM | OVS flow table size |

→ **단순함 vs 분산**. CloudStack은 VR이 단일 장애점이지만 디버깅이 쉽다.

---

## 16. 한 줄 요약

```
VR = "게스트망마다 1대 떠있는 작은 Linux 어플라이언스"
   = "iptables + dnsmasq + HAProxy + keepalived 조합"
   = "MS가 cfg 푸시 → 데몬 reload"
   = "OpenStack OVN의 분산 흐름과 정반대의 집중 모델"
```

---

## 다음

→ [api-auth-flow.md](./api-auth-flow.md): VR이 받는 명령은 어떻게 인증되었나.
→ [scheduler-allocator-internals.md](./scheduler-allocator-internals.md): VR도 결국 호스트에 배치되는 VM.
→ [../02-advanced-services/system-vms.md](../02-advanced-services/system-vms.md): SSVM/CPVM과의 비교.

---

## 공식 문서 레퍼런스

- [Admin Guide — Virtual Router](https://docs.cloudstack.apache.org/en/latest/adminguide/virtual_machines/virtual_router.html)
- [Redundant Virtual Routers](https://docs.cloudstack.apache.org/en/latest/adminguide/virtual_machines/virtual_router.html#redundant-virtual-router)
- [Networking — VPC](https://docs.cloudstack.apache.org/en/latest/adminguide/networking/vpc.html)
- [GitHub — apache/cloudstack/systemvm](https://github.com/apache/cloudstack/tree/main/systemvm)
