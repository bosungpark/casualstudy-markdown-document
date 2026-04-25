# Neutron OVN Internals — 가상 네트워크는 실제로 어떻게 그려지나

> **VM 포트 하나가 만들어질 때 OVN 안에서 일어나는 일.** Northbound DB → Southbound DB → ovn-controller → OVS 흐름.

[01-core-services/neutron-networking.md](../01-core-services/neutron-networking.md) 가 "사용자 관점"이라면, 이 문서는 **OVN이 패킷을 어떻게 라우팅하는지** 까지 파고든다.

---

## 1. 왜 OVN인가 — 옛날 ML2+OVS와의 차이

### 옛날 방식 (ML2 + OVS + L3 agent)

```
[neutron-server] 
    ▼ RPC
[L2 agent on compute] : VM 포트를 OVS bridge에 연결
[L3 agent on network-node] : 가상 라우터 구현 (병목)
[DHCP agent] : DHCP 서버 띄움
[Metadata agent] : 169.254.169.254 중계
```

**문제**: L3/DHCP/Metadata 에이전트가 네트워크 노드에 몰림 → 병목 + SPOF.

### OVN 방식

```
[neutron-server + OVN ML2 driver]
    ▼ (OVSDB protocol, 메시지 큐 안 씀)
[OVN Northbound DB] (논리 토폴로지)
    ▼
[ovn-northd] (논리 → 물리 변환)
    ▼
[OVN Southbound DB] (실행 가능한 흐름 룰)
    ▼ (각 노드의 ovn-controller가 Pull)
[Compute 노드의 ovn-controller] : OVS에 OpenFlow 룰 설치
[Compute 노드의 OVS] : 패킷 처리 (자체 분산)
```

**핵심 변화**:
- 라우팅이 **각 compute 노드**에서 분산 처리 (Distributed Virtual Router)
- DHCP/Metadata도 OVS flow rule로 구현 (에이전트 프로세스 없음)
- 모든 의사소통이 OVSDB 프로토콜 — RabbitMQ 안 씀

---

## 2. OVN의 4계층 구조

```
┌─────────────────────────────────────────────────┐
│  Layer 1: Neutron API (사용자 인터페이스)      │
│  openstack network create ...                   │
└─────────────────────────────────────────────────┘
                    │ networking-ovn ML2 driver
                    ▼
┌─────────────────────────────────────────────────┐
│  Layer 2: OVN Northbound DB (논리적 모델)       │
│  Logical_Switch, Logical_Router, ACL, ...       │
└─────────────────────────────────────────────────┘
                    │ ovn-northd 변환
                    ▼
┌─────────────────────────────────────────────────┐
│  Layer 3: OVN Southbound DB (물리 매핑)         │
│  Logical_Flow, Chassis, Port_Binding            │
└─────────────────────────────────────────────────┘
                    │ ovn-controller (각 compute에)
                    ▼
┌─────────────────────────────────────────────────┐
│  Layer 4: OpenFlow / OVS (실제 데이터플레인)   │
│  br-int, br-ex 의 flow rules                    │
└─────────────────────────────────────────────────┘
```

위에서 아래로 갈수록 **물리에 가까워진다**.

---

## 3. 포트 하나가 생기는 흐름 — 끝까지 추적

### Step 1: 사용자 요청

```bash
$ openstack server create --network private ... my-vm
```

Nova가 Neutron에 **port 생성** 요청.

### Step 2: Neutron API → OVN NB DB

```
neutron-server (OVN ML2 driver):
  ├─ DB에 Neutron Port 레코드
  └─ OVN NB DB에 Logical_Switch_Port 추가

OVN NB:
  Logical_Switch "neutron-<network-uuid>"
    └── Logical_Switch_Port "neutron-<port-uuid>"
          ├─ addresses: ["fa:16:3e:aa:bb:cc 192.168.1.10"]
          └─ type: ""
```

이 시점에 VM은 아직 안 떴다. **논리 토폴로지만** 등록됨.

### Step 3: ovn-northd 가 SB DB로 변환

```
ovn-northd (NB 변경 감지):
  ├─ Logical_Switch_Port → Port_Binding 행 생성
  ├─ Logical_Flow 룰 생성 (DHCP, ARP, MAC learning, ACL)
  └─ SB DB에 INSERT

OVN SB:
  Port_Binding "neutron-<port-uuid>" (chassis = NULL — 아직 어디에도 연결 안 됨)
  Logical_Flow:
    table=0, match=inport=<port>, action=...
    table=1, match=eth.dst=<mac>, action=output:<port>
    ... 수십 개 룰
```

### Step 4: Nova-compute 가 VM 부팅

```
nova-compute → libvirt: VM 시작
libvirt: tap 디바이스 생성 (예: tapXXXXX)
        ↓
nova-compute → 기존 patch: ovs-vsctl add-port br-int tapXXXXX
                          external_ids:iface-id=<port-uuid>
```

이 줄이 핵심: **OVS interface에 `iface-id`를 박는다** = "이 OVS 포트는 OVN의 어느 logical port인가" 를 자기 자신이 선언.

### Step 5: 로컬 ovn-controller 가 인지

```
ovn-controller (해당 compute에서 돌고 있음):
  ├─ OVS DB watch → 새 interface 감지 (iface-id=<port-uuid>)
  ├─ SB DB에 Port_Binding 업데이트:
  │     chassis = <이 노드의 chassis-uuid>
  ├─ SB DB에서 Logical_Flow 다운로드
  └─ OVS에 OpenFlow 룰 설치 (br-int)
```

### Step 6: 트래픽이 흐른다

```
VM이 ARP request 송신
  ↓
br-int (OVS)
  ↓ OpenFlow table 0
  ↓ "이 포트의 패킷이군"
  ↓ table 1, 2, ... 통과
  ↓ "ARP는 OVN이 직접 응답"
  ↓ ARP reply 만들어서 VM에 회신
```

DHCP, ARP, ICMPv6 NDP 같은 것들이 **에이전트 없이 OVN flow rule로 처리**됨.

---

## 4. Geneve 터널 — Compute 간 통신

다른 compute에 있는 VM과 통신하려면?

```
compute-01: VM-A (192.168.1.10)
compute-02: VM-B (192.168.1.20)

VM-A → VM-B 패킷:
  [eth: A→B][ip: 192.168.1.10→192.168.1.20]
        ↓
  br-int (compute-01)
        ↓ Logical Flow 통과
        ↓ "VM-B는 다른 chassis(compute-02)에 있군"
        ↓ Geneve 캡슐화
        ↓
  외부 패킷:
  [outer eth][outer ip: compute-01→compute-02]
  [Geneve 헤더: VNI=<network-id>, metadata=...]
  [원래 패킷 그대로]
        ↓
  underlay 네트워크 (물리 NIC)
        ↓
  compute-02
        ↓ Geneve 디캡슐화
        ↓ br-int → VM-B
```

**Geneve** (Generic Network Virtualization Encapsulation)은 VXLAN보다 헤더 확장이 자유로워서 OVN이 채택. 8 bytes overhead + 가변 옵션.

> ⚠️ **MTU 함정**: Geneve 오버헤드 ~50 bytes. underlay MTU 1500이면 VM에는 1450 줘야. `openstack network set --mtu 1450 ...` 또는 underlay에 jumbo frame.

---

## 5. Distributed Virtual Router — L3가 분산되는 마법

옛날엔 라우터가 네트워크 노드에 몰려있었다. OVN은 어떻게 분산?

```
시나리오:
  사설망 A (10.0.0.0/24) ↔ 라우터 ↔ 사설망 B (10.0.1.0/24)

  compute-01에 VM-A (10.0.0.10) 있음
  compute-02에 VM-B (10.0.1.20) 있음

VM-A → VM-B 패킷:
  ① VM-A가 자기 게이트웨이(10.0.0.1)로 보냄
  ② compute-01의 ovn-controller가 받은 OpenFlow 룰:
       "L3 라우팅 직접 처리하라"
  ③ TTL -1, MAC 재작성 (라우터 MAC)
  ④ Geneve로 compute-02에 전송
  ⑤ compute-02 br-int → VM-B
```

**라우터 함수가 모든 compute 노드에 복사돼있다**. 패킷이 네트워크 노드를 안 거침.

### 단, Floating IP 와 외부망 (SNAT) 은 예외

```
VM → 외부 인터넷 (SNAT)
   → Gateway Chassis (지정된 노드 1대 또는 HA로 N대)
   → 거기서만 SNAT 변환 후 외부로
```

이건 **상태(connection tracking) 가 한 곳에 있어야** 해서 분산 못 함. 그래서 OVN에서도 외부 출입구는 몇 대로 한정.

---

## 6. Security Group — ACL로 구현

Security Group은 OVN에서 **ACL 테이블**로 표현된다.

```
NB DB:
  ACL:
    direction: from-lport
    match: outport == "<port>" && tcp.dst == 80
    action: allow-related   ← stateful
```

`allow-related` = conntrack 사용 → 들어온 연결의 응답은 자동 허용.

OVS 안에서는 conntrack 모듈로 처리. Linux iptables 안 거침 (예전 ML2+OVS는 hybrid plug 필요했음).

---

## 7. DHCP / Metadata — 에이전트 없이

### DHCP

NB DB의 `DHCP_Options` 테이블 → northd가 SB Logical_Flow로 변환:

```
match: inport == "<port>" && udp.src == 68 && udp.dst == 67
action: 자동 응답 생성 (옵션 채워서)
```

OVS가 DHCPDISCOVER 받으면 **자기가 직접 OFFER 응답**. dnsmasq/dhcpd 같은 데몬 없음.

### Metadata (169.254.169.254)

각 compute 노드에 가벼운 **ovn-metadata-agent**가 떠있음. 네임스페이스 안에 작은 HTTP proxy:

```
VM → 169.254.169.254:80 GET /latest/meta-data/
    ↓ OVS (이 IP는 metadata 네임스페이스로)
    ↓ HAProxy in netns → nova-metadata-api
```

**옛 metadata agent와 차이**: 노드별로 자기 네임스페이스. 중앙 집중 안 함.

---

## 8. 디버깅 기본기

### NB DB / SB DB 들여다보기

```bash
$ ovn-nbctl show
switch f6...  (neutron-<network-uuid>) 
    port abc...
        addresses: ["fa:16:3e:aa:bb:cc 192.168.1.10"]
    port def...

$ ovn-sbctl show
Chassis "compute-01-uuid"
    hostname: compute-01
    Encap geneve ip="10.10.0.1"
    Port_Binding abc...
```

### OVS flow rule 보기

```bash
$ sudo ovs-ofctl dump-flows br-int | grep <port-uuid 일부>
```

### 패킷 추적 (OVN datapath simulator)

```bash
$ ovn-trace --detailed <network> 'inport=="<port>" && eth.dst==...'
```

→ 패킷이 어느 OpenFlow table을 거쳐 어디로 가는지 시뮬레이션. **금손 도구**.

### tcpdump on Geneve

```bash
$ sudo tcpdump -i <underlay-iface> -nn 'udp port 6081'
# Geneve 패킷 흐름 관찰
```

---

## 9. HA 토폴로지

```
Northbound DB / Southbound DB:
  ovsdb-server-active 1대 + standby 2대 (Raft로 leader 선출)

ovn-northd:
  보통 active 1대, standby N대 (lock 기반)

ovn-controller:
  각 compute/network 노드에 1개씩 (분산 가정)

Gateway chassis (외부 통로):
  HA priority로 N대 지정 → primary 죽으면 자동 fail-over (BFD 감지)
```

---

## 10. 코드 위치 (참고)

| 컴포넌트 | 코드/패키지 |
|---|---|
| Neutron OVN ML2 driver | `networking-ovn` (옛) → `neutron/plugins/ml2/drivers/ovn/` (현재) |
| OVN core (NB/SB schema, northd) | `openvswitch/ovn` 별도 프로젝트 |
| ovn-controller | OVN 프로젝트 안 |
| OVS | `openvswitch/ovs` |

---

## 11. 핵심 요약

```
1. Neutron API → NB DB에 논리 토폴로지 (스위치/라우터/포트/ACL)
2. ovn-northd: NB → SB 변환 (Logical_Flow + Port_Binding)
3. 각 compute의 ovn-controller: SB → OpenFlow 룰을 OVS에 설치
4. OVS가 자체적으로 패킷 처리 (DHCP/ARP/L3까지)
5. compute 간은 Geneve 터널로 캡슐화
6. 라우터/SG/DHCP/Metadata 모두 분산 → 옛날 L3/DHCP agent 사라짐
```

> 💡 **OVN이 빛나는 순간**: VM 100개가 동시에 ARP 요청을 쏠 때, 옛 ML2+OVS는 네트워크 노드가 끙끙댔지만 OVN은 각 compute가 독립적으로 응답한다. 수평 확장이 진짜로 일어남.

---

## 다음

→ [nova-scheduler-internals.md](./nova-scheduler-internals.md): 어느 compute에 VM을 보낼지 결정 (포트 생성 직전의 단계)  
→ [keystone-token-flow.md](./keystone-token-flow.md): 모든 OVN 호출의 출입증
