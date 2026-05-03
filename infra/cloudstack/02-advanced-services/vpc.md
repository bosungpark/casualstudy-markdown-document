# VPC — Multi-Tier 가상 사설망

> **AWS VPC와 같은 의미: 여러 Tier(서브넷) + 단일 Router + ACL**

CloudStack의 VPC는 Isolated Network을 한 단계 발전시킨 것. **여러 사설망을 묶고, 라우팅과 ACL을 추가**.

> 출처: [Admin Guide — VPC](https://docs.cloudstack.apache.org/en/latest/adminguide/networking/vpc.html).

---

## 1. 한 컷 차이 — Isolated Network vs VPC

```
[Isolated Network]
   ─ 사설망 1개
   ─ VR 1개 (그 사설망 전용)
   ─ 다른 사설망과 통신하려면 Public IP 거쳐야

[VPC]
   ─ 여러 Tier(사설망)
   ─ VPC Router 1개 (모든 Tier의 게이트웨이)
   ─ Tier 간 통신은 VPC Router 안에서 직접 (인터넷 거치지 않음)
   ─ Tier 간 통신은 Network ACL로 통제
```

```
┌──────────────── VPC: 10.0.0.0/16 ────────────────┐
│                                                   │
│  Tier "web"   10.0.1.0/24    [VM-W1] [VM-W2]      │
│      │                                            │
│      ▼                                            │
│  ┌────────────┐                                   │
│  │ VPC Router │   ← 단일 라우터, 모든 Tier 연결  │
│  │  + ACLs    │                                   │
│  └─────┬──────┘                                   │
│        │                                          │
│  ▲     ▼                                          │
│  │  Tier "app"  10.0.2.0/24   [VM-A1] [VM-A2]     │
│  │     │                                          │
│  │     ▼                                          │
│  │  Tier "db"   10.0.3.0/24   [VM-D1]             │
│  └─────────                                        │
│                                                   │
└──────────┬────────────────────────────────────────┘
           │ Public IP (VPC Router)
           ▼
       [Internet]
```

---

## 2. 객체 지도

| 객체 | 의미 |
|---|---|
| **VPC** | 가상 사설망 (`10.0.0.0/16` 같은 큰 CIDR) |
| **Tier** (Network) | VPC 안의 서브넷 (`10.0.1.0/24`) |
| **VPC Router** | VPC의 단일 게이트웨이 + NAT + LB (System VM) |
| **Network ACL** | Tier 사이 또는 외부와의 ACL (stateless) |
| **Static Route** | VPC 내 사용자 정의 라우트 |
| **Site-to-Site VPN** | 외부 데이터센터와 IPsec 연결 |
| **Private Gateway** | 다른 VPC 또는 Physical 네트워크 연결 |

---

## 3. Network ACL — Tier 단위 방화벽

> [Network ACLs](https://docs.cloudstack.apache.org/en/latest/adminguide/networking/vpc.html#configuring-network-access-control-list).

AWS와 같은 의미. **Stateless**. (Security Group 은 Stateful)

```
ACL "web-acl":
  ingress:
    1: allow tcp 0.0.0.0/0 → 80
    2: allow tcp 0.0.0.0/0 → 443
    99: deny  all
  egress:
    1: allow tcp 10.0.2.0/24 → 8080      (app tier로만)
    99: deny  all
```

→ Tier별로 ACL을 매핑.

```bash
$ cmk create networkacllist name=web-acl vpcid=<...>

$ cmk create networkacl \
    aclid=<web-acl-id> \
    protocol=tcp startport=80 endport=80 \
    cidrlist=0.0.0.0/0 \
    action=allow \
    traffictype=Ingress \
    number=1

$ cmk create network ... aclid=<web-acl-id>   # Tier에 ACL 연결
```

---

## 4. VPC Router의 추가 능력

Isolated Network의 VR 능력에 더해:

| 추가 기능 | 설명 |
|---|---|
| **Inter-Tier 라우팅** | Tier 간 직접 라우팅 (Public IP 안 거침) |
| **Network ACL 적용** | Tier 단위 방화벽 |
| **Static Route** | 운영자 정의 경로 |
| **Site-to-Site VPN** | IPsec으로 원격 DC 연결 |
| **Private Gateway** | 다른 VPC와 직접 연결 |

→ **하나의 VPC Router가 모든 Tier의 게이트웨이**. AWS의 VPC + IGW + NAT GW + VGW를 한 어플라이언스로.

---

## 5. 실습 — 3-Tier VPC

```bash
# 1. VPC 생성
$ cmk create vpc \
    name=app-vpc \
    cidr=10.0.0.0/16 \
    vpcofferingid=<...> \
    zoneid=<...>

# 2. Tier 생성 (= Network in VPC)
$ cmk create network \
    name=web-tier \
    networkofferingid=<vpc-tier-offering-id> \
    vpcid=<vpc-id> \
    zoneid=<...> \
    gateway=10.0.1.1 netmask=255.255.255.0

$ cmk create network ... name=app-tier ... gateway=10.0.2.1
$ cmk create network ... name=db-tier  ... gateway=10.0.3.1

# 3. ACL: web ← 인터넷 80/443
$ cmk create networkacllist name=web-acl vpcid=<vpc-id>
$ cmk create networkacl aclid=<web-acl> protocol=tcp \
    startport=80 endport=80 cidrlist=0.0.0.0/0 \
    action=allow traffictype=Ingress number=1
# ... ACL 더 추가

# 4. Tier에 ACL 적용
$ cmk update network id=<web-tier-id> aclid=<web-acl>

# 5. Public IP + Port Forward
$ cmk associate ipaddress vpcid=<vpc-id>
$ cmk create portforwardingrule \
    ipaddressid=<...> publicport=80 privateport=80 \
    protocol=tcp virtualmachineid=<web-vm-id>

# 6. VM 배포
$ cmk deploy virtualmachine \
    serviceofferingid=<...> templateid=<...> \
    networkids=<web-tier-id>
```

---

## 6. Site-to-Site VPN

> [Site-to-Site VPN](https://docs.cloudstack.apache.org/en/latest/adminguide/networking/site_to_site_vpn.html).

```
[CloudStack VPC]
   10.0.0.0/16
       │
       └── VPC Router (Public IP)
              │
              │  IPsec (strongSwan)
              ▼
       [원격 DC Router]
              │
       192.168.0.0/16
```

```bash
# Customer Gateway 정의
$ cmk create vpncustomergateway \
    name=remote-dc \
    gateway=203.0.113.50 \
    cidrlist=192.168.0.0/16 \
    ipsecpsk=<shared-secret> \
    esppolicy=aes128-sha1 \
    ikepolicy=aes128-sha1

# VPC Gateway 활성화
$ cmk create vpngateway vpcid=<...>

# 연결
$ cmk create vpnconnection \
    s2scustomergatewayid=<...> \
    s2svpngatewayid=<...>
```

---

## 7. Private Gateway — VPC 간 / Physical 연결

VPC를 다른 VPC 또는 미리 정의된 물리망에 직접 연결. AWS의 VPC Peering / Transit Gateway 역할.

```bash
$ cmk create privategateway \
    vpcid=<...> \
    physicalnetworkid=<...> \
    gateway=10.99.0.1 \
    netmask=255.255.255.0 \
    ipaddress=10.99.0.10 \
    vlan=999
```

---

## 8. 자주 밟는 지뢰

- **Tier 간 통신 안 됨** → 기본 ACL이 Deny. 명시적 Allow 추가.
- **VPC Router 부하 한계** → System VM Offering 키우기. 또는 VPC당 트래픽 분산 어려우니 큰 VPC를 분할.
- **ACL 변경 후 즉시 적용 안 됨** → VR이 iptables 룰 다시 적용해야. `cmk replace networkacllist` 후 `restart network`.
- **Site-to-Site VPN 협상 실패** → IKE/ESP 정책 양측 동일 확인. `journalctl` (VR에 SSH 가능 시).
- **VPC 안 LB가 외부에서 접근 안 됨** → LB는 VPC Router가 처리. Public IP 할당 + LB 룰 + ACL.

---

## 9. OpenStack/AWS 매핑

| AWS | OpenStack | CloudStack |
|---|---|---|
| VPC | Neutron Project Network 묶음 | VPC |
| Subnet | Subnet | Tier (Network) |
| Internet Gateway | Router 의 외부 GW | VPC Router (자동) |
| NAT Gateway | (Router의 SNAT) | VPC Router (자동) |
| VPC Peering | (Provider) | Private Gateway |
| Network ACL | (없음) | Network ACL |
| Security Group | Security Group | Network ACL + Security Group |
| Site-to-Site VPN | VPNaaS | Site-to-Site VPN (VR 안 strongSwan) |

---

## 다음

→ [system-vms.md](./system-vms.md): VPC Router도 결국 System VM.
→ [projects.md](./projects.md): VPC를 Project 단위로 공유.

---

## 공식 문서 레퍼런스

- [Admin Guide — VPC](https://docs.cloudstack.apache.org/en/latest/adminguide/networking/vpc.html)
- [Network ACLs](https://docs.cloudstack.apache.org/en/latest/adminguide/networking/vpc.html#configuring-network-access-control-list)
- [Site-to-Site VPN](https://docs.cloudstack.apache.org/en/latest/adminguide/networking/site_to_site_vpn.html)
- [Private Gateway](https://docs.cloudstack.apache.org/en/latest/adminguide/networking/vpc.html#adding-a-private-gateway-to-a-vpc)
