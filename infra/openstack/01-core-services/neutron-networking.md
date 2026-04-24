# Neutron — 가상 네트워크의 모든 것

> **VPC + 서브넷 + 라우터 + 방화벽 + 공인IP를 전부 혼자 함.**

AWS에서 네트워크 기능은 VPC, Subnet, Route Table, Security Group, Elastic IP 등으로 흩어져 있다. OpenStack은 **전부 Neutron 하나**에 몰아넣었다.

---

## 한 줄 요약

물리 네트워크 위에 **가상 네트워크를 소프트웨어로 그린다.** VM은 진짜 랜선이 아니라 Neutron이 그려준 가상 포트에 꽂힌다.

```
 물리 세계: 스위치 1대, 랜선, 방화벽 박스
    ↓ Neutron이 위에 덮어씀
 가상 세계: 사용자마다 "내 전용 VPC" 수백 개
```

---

## 핵심 객체

| 객체 | 한 줄 |
|---|---|
| **Network** | 사설망 한 개 (VLAN/VXLAN 기반) |
| **Subnet** | 네트워크 안의 IP 대역 (예: 192.168.1.0/24) |
| **Port** | VM이 꽂히는 가상 포트 (MAC/IP 부여) |
| **Router** | 서로 다른 사설망 연결 + 외부 인터넷 연결 |
| **Security Group** | 포트 단위 방화벽 (stateful) |
| **Floating IP** | VM에 붙이는 공인 IP (1:1 DNAT) |

---

## 머릿속 그림

```
  [외부 인터넷]
       │
       ▼
  [Router] ◄── Floating IP (예: 203.0.113.5) → VM에 맵핑
       │
       ├─ Subnet A (192.168.1.0/24)
       │    ├─ Port → VM1 (192.168.1.10)
       │    └─ Port → VM2 (192.168.1.11)
       │
       └─ Subnet B (10.0.0.0/24)
            └─ Port → VM3 (10.0.0.5)
```

VM은 Port에 연결 → Port는 Subnet의 IP를 받음 → Router가 Subnet끼리 + 외부로 연결.

---

## 내부 구성

```
[neutron-server]      REST API (컨트롤 노드)
      │
      ▼ RabbitMQ
      │
[L2 agent]            Compute 노드에서 VM 포트 ↔ VLAN/VXLAN 연결
[L3 agent]            가상 라우터 (네트워크 노드)
[DHCP agent]          사설망에 DHCP 서버 자동 제공
[Metadata agent]      VM이 169.254.169.254로 자기 정보 조회할 때 중계
```

**L2 agent 구현체**: OVS(Open vSwitch), Linux Bridge, **OVN**(최근 표준).

---

## OVS vs OVN — 최근 트렌드

옛날 방식(ML2 + OVS + L3 agent):
- L3 agent가 네트워크 노드에 몰려 있음 → 병목, SPOF
- 라우터 트래픽 전부 네트워크 노드 거쳐감

새 방식(OVN):
- 모든 논리(라우터/ACL/로드밸런서)를 OVN이 **선언적으로** 관리
- 각 Compute 노드가 **직접** L3 처리 (분산)
- L3 agent / DHCP agent 불필요

> 신규 설치는 거의 OVN으로 간다. 기존 OVS 환경도 OVN으로 마이그레이션 진행 중.

---

## Security Group vs 방화벽 규칙

```
Security Group "web"
 ├─ ingress: 0.0.0.0/0 → TCP 80
 ├─ ingress: 0.0.0.0/0 → TCP 443
 └─ egress:  all
```

- **Stateful**: 들어온 연결의 응답은 자동 허용
- **포트 단위로 적용**: VM 포트에 SG 붙이면 끝
- **여러 개 중첩 가능**: `web` + `ssh-from-office` 같이

AWS Security Group과 개념 동일.

---

## Floating IP

- 공인 IP를 풀(pool)에 쌓아둠
- VM에 **1:1로 맵핑** → 외부에서 접근 가능
- VM 교체해도 IP 유지 가능 (AWS의 Elastic IP와 동일)

```bash
# 공인IP 하나 받기
$ openstack floating ip create public-net

# VM에 붙이기
$ openstack server add floating ip my-vm 203.0.113.5
```

---

## 손으로 해보기

```bash
# 사설망 생성
$ openstack network create private-net
$ openstack subnet create --network private-net \
    --subnet-range 192.168.1.0/24 private-subnet

# 라우터 만들고 외부망 / 사설망 연결
$ openstack router create my-router
$ openstack router set --external-gateway public-net my-router
$ openstack router add subnet my-router private-subnet

# Security Group 만들기
$ openstack security group create web
$ openstack security group rule create --proto tcp --dst-port 80 web

# 포트 목록
$ openstack port list
```

---

## 자주 밟는 지뢰

- **VM이 IP를 못 받음** → DHCP agent 죽었거나, Subnet에 DHCP enabled=false
- **외부 ping 안 됨** → 라우터에 external gateway 안 붙음 / Floating IP 안 붙음
- **VM끼리 통신 안 됨** → Security Group에서 자기 자신(또는 상대 SG) 허용 필요
- **MTU 문제** → VXLAN은 오버헤드 50bytes. `--mtu 1450` 설정 잊지 말기
- **Metadata 안 옴** → `169.254.169.254` 라우팅 / metadata agent 확인

---

## AWS 매핑

| AWS | Neutron |
|---|---|
| VPC | Network |
| Subnet | Subnet |
| Route Table + IGW | Router + external gateway |
| Security Group | Security Group |
| Elastic IP | Floating IP |
| Network ACL | (FWaaS 또는 OVN ACL) |
| NAT Gateway | Router의 SNAT |

---

## 다음

→ [nova-compute.md](./nova-compute.md) 에서 VM이 Neutron 포트에 어떻게 꽂히는지.  
→ 고급 주제: Octavia(LoadBalancer), FWaaS, VPNaaS → [../02-advanced-services/](../02-advanced-services/)
