# OpenStack 한 장 요약 — 스터디 공유용

> 10분 안에 핵심을 잡고, 함께 토론할 수 있는 분량.

---

## 30초: 한 줄로

> **내 데이터센터를 AWS처럼 쓰게 해주는 오픈소스 IaaS 프레임워크.**

VM·베어메탈·컨테이너를 멀티테넌트로 쪼개주는 도구.

---

## 1분: 왜 존재하나

| 문제 | OpenStack의 답 |
|---|---|
| AWS에 데이터 못 올림 (규제·주권) | 내 하드웨어에 직접 깐다 |
| 서버 100대, 사용자 1000명 분배 | API 한 줄로 셀프서비스 |
| 여러 팀·고객이 안전하게 나눠 씀 | Project/Domain 격리 (멀티테넌시) |
| AWS API에 락인되기 싫음 | 표준 오픈 API |

**주 사용처**: 통신사 5G/NFV, 정부·금융 사설클라우드, EU 소버린 클라우드, VMware 탈출자.

---

## 3분: 머릿속 그림

```
         사용자 / Horizon / CLI
                  │
   ┌──────┬──────┼──────┬──────┬──────┐
   ▼      ▼      ▼      ▼      ▼      ▼
[Keystone][Nova][Neutron][Glance][Cinder][Placement]   ← 각자 API
   ▲  ▲     ▲     ▲       ▲      ▲      ▲
   │  └─────┴─────┴───────┴──────┴──────┘
   │      "토큰 진짜?" 물어볼 때만 호출
   │
   └─ 게이트웨이 아니다. 신원조회소.

각자 자기 DB:        nova-db, neutron-db, ...
서비스 간 통신:       REST API
서비스 내부 통신:     RabbitMQ
영속 데이터:         MariaDB (보통 Galera 클러스터)
```

---

## 5분: 서비스 6개 한 줄씩

| 서비스 | 역할 | AWS 대응 |
|---|---|---|
| **Keystone** | 인증 + 서비스 카탈로그 | IAM |
| **Nova** | VM 라이프사이클 매니저 (직접 안 만듦) | EC2 |
| **Neutron** | 가상 네트워크 (VPC + 라우터 + 방화벽 + 공인IP 통합) | VPC + ELB + Route Table |
| **Glance** | OS 이미지 저장소 | AMI |
| **Cinder** | 블록 스토리지 (영구 볼륨) | EBS |
| **Placement** | 자원 가계부 (누가 얼마 썼나 추적) | (AWS 내부 숨김) |

부가: Swift(S3), Heat(CloudFormation), Octavia(ELB), Magnum(EKS), Ironic(베어메탈).

---

## 10분: VM 한 개 만들 때 — 9단계 협업

```bash
$ openstack server create --flavor m1.small --image ubuntu --network private my-vm
```

```
[1] Keystone:    토큰 검증
[2] Nova-API:    요청 수신
[3] Conductor:   DB에 instance 레코드 (BUILD)
[4] Scheduler + Placement:  "어느 호스트?"
[5] Compute on host-3:
    ├─► Glance:   OS 이미지 다운로드
    ├─► Neutron:  포트/IP/MAC/SG
    ├─► Cinder:   (있으면) 볼륨 생성+attach
    └─► libvirt → KVM:  실제 VM 띄움
[6] cloud-init:  키/hostname 주입
[7] ACTIVE
```

**6개 서비스가 협업**. 어디서 막혔는지가 디버깅의 출발점.

---

## ★ 인사이트 10가지 (시간 없으면 여기만)

### 1. **Nova는 VM을 직접 만들지 않는다**
발주자/매니저. 실제 시공은 **libvirt → KVM/Xen/VMware**.
```
Nova-Compute → libvirt → 하이퍼바이저
   (지시)      (어댑터)    (실제 작업)
```

### 2. **Keystone은 게이트웨이가 아니라 신원조회소**
모든 트래픽이 거쳐가는 게 아니라, 각 서비스가 **필요할 때만 토큰 검증을 위탁**.

### 3. **Fernet 토큰 = 자기 자신을 증명하는 봉인된 편지**
DB 조회 없이 **AES-128-CBC + HMAC-SHA256** 복호화만으로 검증. → stateless → Keystone 100대 띄워도 OK.

### 4. **부하 분산 3기법** (Keystone에 매번 안 물어봄)
1. **Stateless 토큰** — DB 조회 0회
2. **각 서비스의 토큰 캐시** — memcached 5~10분
3. **Keystone 수평 확장** — 같은 키만 공유

### 5. **Placement가 분리된 이유**
원래 Nova 안에 있었음. 이젠 **Cyborg(GPU), Neutron(대역폭), Cinder(스토리지)** 도 자원 추적 필요 → 공용 가계부로 외재화. 2019년 Stein 릴리스.

### 6. **자원 부족 시 OpenStack은 안 쫓아낸다**
"No valid host" 거절. **멀티테넌시 신뢰 약속** 때문. (K8s는 Priority로 Pod 죽임 — VM은 무거우니 다른 모델.)

### 7. **VPN과 같은 원리의 터널링**
다른 서버의 VM이 같은 사설망인 척 통신. **Geneve(또는 VXLAN) 캡슐화 + VNI** 로 가상망 식별. VPN과 차이는 암호화 vs 격리 목적.

### 8. **OVN: 선언과 실행 분리**
**Neutron/OVN NB DB** = 무엇을(논리). **OVS** = 어떻게(OpenFlow 룰). ovn-northd 가 자동 변환. 라우팅·DHCP·ARP가 모든 compute 노드에 분산 → 옛 L3 agent 병목 사라짐.

### 9. **REST는 서비스 간, RabbitMQ는 서비스 내부**
- Nova-API ↔ Glance API: **HTTP REST** (남남, 표준 계약)
- Nova-API ↔ Nova-Scheduler ↔ Nova-Compute: **RabbitMQ RPC** (한 가족, 비동기)

### 10. **VM 만들기 = 6개 서비스 협업**
하나가 침묵하면 BUILD 멈춤. **task_state 보고 → 해당 서비스 로그** 가 디버깅 공식.

---

## 5분: 비유로 잡기

### Keystone = 호텔 프론트 데스크
체크인 한 번 → 방 키(토큰) 받음 → 이후 모든 시설은 키만 보여주면 됨.

### Nova = 건설 현장 매니저
본인이 망치 안 듦. KVM이 망치, libvirt가 표준 계약서.

### Placement = 객실 현황판
빈 방 / 청소중 / 투숙중을 실시간 추적. 매니저가 손님 배정할 때 이걸 봄.

### Neutron + OVN = 우체국 + 우편 시스템
사설망 패킷을 봉투(Geneve)에 싸서 물리 네트워크로 보냄. **VNI 라벨**로 가상망 구분.

### Cinder = 외장하드 대여점
VM에 붙였다 뗐다. VM 죽어도 살아남음.

---

## 디버깅 한 컷

```
"BUILD에서 안 넘어감"
   │
   ▼
$ openstack server show <vm> | grep task_state
   │
   ├─ scheduling      → Placement 자원 부족? heal_allocations
   ├─ networking      → Neutron IP 풀? OVN 죽음? (제일 흔함)
   ├─ block_device    → Cinder 백엔드 문제
   ├─ spawning        → libvirt/qemu, journalctl -u libvirtd
   └─ ERROR + fault   → fault 메시지 + 해당 서비스 로그
```

> **OpenStack 디버깅 = 협력 서비스 중 누가 거짓말/침묵 했는지 추적.**

---

## OpenStack vs 친구들

| | OpenStack | AWS | Kubernetes | VMware vSphere |
|---|---|---|---|---|
| 위치 | 내 하드웨어 | 남의 하드웨어 | 컨테이너 위주 | 내 하드웨어 (라이선스) |
| 단위 | VM/베어메탈/컨테이너 | EC2/ECS 등 | Pod | VM |
| 라이선스 | 무료 | 사용료 | 무료 | $$$ (Broadcom) |
| 멀티테넌시 | 강함 (DNA) | 계정 단위 | Namespace (약함) | vCloud 별도 |
| 학습곡선 | 가파름 | 완만 | 중간 | 완만 |
| 베어메탈 | Ironic 1급 | 별도 인스턴스 타입 | 약함 | ESXi 자체 |
| 추세 | 통신·정부·VMware 탈출 | 표준 | 압도적 성장 | 감소 (Broadcom 후) |

---

## 자주 듣는 오해 정리

- ❌ "OpenStack은 하이퍼바이저다" → 아님. KVM 위에서 **오케스트레이션**.
- ❌ "K8s가 OpenStack을 대체한다" → 다른 레이어. K8s on OpenStack 조합이 흔함.
- ❌ "OpenStack은 단일 바이너리다" → 30+ 프로젝트의 **느슨한 연합체**. 필요한 것만 깐다.
- ❌ "AWS 킬러" → 아님. **Private/Hybrid/Telco/Sovereign** 영역.
- ❌ "Keystone이 게이트웨이다" → 신원조회소. 트래픽 안 거쳐감.

---

## 30초: 결론

> **OpenStack = 데이터 주권 + 멀티테넌시가 필요한 곳의 표준 IaaS 프레임워크.**  
> **여러 독립 서비스가 토큰 한 장 들고 협업.**  
> **2010년대 클라우드를 정의했고, 통신·금융·정부에서 향후 10년 살아남을 기술.**

---

## 더 깊이

| 주제 | 문서 |
|---|---|
| 큰 그림 (질문 따라가는) | [00-overview/architecture-overview.md](./00-overview/architecture-overview.md) |
| 각 서비스 사용법 | [01-core-services/](./01-core-services/) |
| 부가 서비스 | [02-advanced-services/](./02-advanced-services/) |
| 직접 설치 (DevStack) | [03-installation/devstack/](./03-installation/devstack/) |
| 운영 디테일 | [04-operations/](./04-operations/) |
| 내부 구현 (Fernet/OVN/Scheduler) | [05-deep-dives/](./05-deep-dives/) |

---

> 💡 **이 문서를 30분 토론 자료로 활용하기**:  
> 1. "30초 요약" 부터 함께 읽기  
> 2. **인사이트 10개 중 본인이 의외였던 것** 한 명씩 고르기  
> 3. "VM 9단계 흐름" 그리며 어디서 어떤 서비스 일하는지 짚기  
> 4. 디버깅 한 컷 — 실제 장애 시나리오 한두 개 묘사하며 어디 봐야 할지 토론

---

# 부록 — Private Cloud 설계안 답안

> **과제 문항**: OpenStack 기반 Private Cloud의 기본 구성 아키텍처 설계안 작성하시오. 핵심 컴포넌트(Nova, Neutron, Glance, Cinder 등)를 포함한 기본 아키텍처 도식 및 역할 설명하시오.

## 1. 설계 개요

**목적**: 자체 데이터센터에 멀티테넌트 IaaS를 구축하여, AWS와 동등한 수준의 셀프서비스 VM/네트워크/스토리지를 사내 사용자에게 제공.

**설계 원칙**:
- **느슨한 결합**: 각 서비스 독립 프로세스, REST API + RabbitMQ 통신
- **수평 확장**: stateless 컴포넌트 우선, DB/MQ는 클러스터링
- **장애 격리**: 컨트롤 플레인 / 데이터 플레인 분리

---

## 2. 노드 토폴로지 (3-Tier 권장)

```
┌──────────────────────────────────────────────────────────┐
│  [Controller Node]  × 3대 (HA)                          │
│  ─ Keystone, Nova-API/Scheduler/Conductor, Neutron-Server│
│  ─ Glance-API, Cinder-API, Placement, Horizon            │
│  ─ MariaDB(Galera), RabbitMQ Cluster, memcached          │
└──────┬───────────────────────────────────────────────────┘
       │ Management Network (10.0.0.0/24)
       │
       ├──► [Compute Node] × N대
       │    ─ nova-compute, libvirt, KVM
       │    ─ ovn-controller, OVS
       │
       ├──► [Network Node] × 2대 (Gateway HA)
       │    ─ ovn-northd, OVN NB/SB DB
       │    ─ External Gateway (SNAT/Floating IP)
       │
       └──► [Storage Node] × 3대 이상
            ─ Ceph (RBD for Cinder/Glance, RGW for Swift)
```

**물리 네트워크 분리**:
- Management (API/SSH/RabbitMQ)
- Tunnel (Geneve overlay — 가상망 트래픽)
- Storage (Ceph 트래픽 격리)
- External (Floating IP, 외부 인터넷)

---

## 3. 핵심 컴포넌트 아키텍처 도식

```
                  ┌─────────────────────┐
                  │  사용자 / Horizon   │
                  └──────────┬──────────┘
                             │ REST API + Token
   ┌─────────────────────────┼─────────────────────────┐
   ▼                         ▼                         ▼
┌─────────┐  토큰 검증  ┌─────────┐              ┌─────────┐
│Keystone │◄────────────┤  Nova   │─────────────►│Placement│
│ (인증)  │             │(컴퓨트) │  자원 질의   │ (가계부)│
└─────────┘             └────┬────┘              └─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         ┌────────┐    ┌─────────┐    ┌─────────┐
         │ Glance │    │ Neutron │    │ Cinder  │
         │(이미지)│    │(네트워크)│    │ (디스크)│
         └────┬───┘    └────┬────┘    └────┬────┘
              │             │              │
              ▼             ▼              ▼
         ┌──────────────────────────────────────┐
         │  Compute Node (libvirt → KVM → VM)   │
         │  + OVS (Geneve 터널링)                │
         └──────────────────────────────────────┘
```

---

## 4. 컴포넌트별 역할

| 컴포넌트 | 역할 | AWS 대응 |
|---|---|---|
| **Keystone** | 인증/인가, 토큰 발급(Fernet), 서비스 카탈로그. 모든 서비스의 신원조회소 | IAM |
| **Nova** | VM 라이프사이클 관리. API 수신 → Scheduler가 호스트 결정 → Compute가 libvirt/KVM 호출 | EC2 |
| **Neutron** | 가상 네트워크(VPC), 서브넷, 라우터, 방화벽, Floating IP. OVN 기반 분산 처리 | VPC + ELB + Route Table |
| **Glance** | OS 이미지 저장/배포 (qcow2, raw). 백엔드는 Ceph 또는 Swift | AMI |
| **Cinder** | 영구 블록 스토리지(볼륨). VM에 attach/detach. LVM/Ceph RBD 백엔드 | EBS |
| **Placement** | 자원 인벤토리 추적. "어느 호스트에 CPU/RAM 남았나" 질의 응답 | (AWS 내부) |
| **Horizon** | 웹 대시보드. 위 모든 서비스의 API를 클릭 가능한 UI로 | Console |
| **(부가) Heat** | 인프라 템플릿 오케스트레이션 (YAML로 스택 배포) | CloudFormation |
| **(부가) Octavia** | LBaaS, HAProxy 기반 로드밸런서 | ELB/ALB |

---

## 5. 데이터 흐름 — VM 생성 예시 (`server create`)

```
[1] Keystone:    토큰 검증
[2] Nova-API:    요청 수신 → DB(MariaDB)에 instance 레코드
[3] Scheduler + Placement:  여유 호스트 결정 (Filter + Weigher)
[4] Glance:      OS 이미지 다운로드 (Ceph로부터)
[5] Neutron:     가상 포트 생성, IP/MAC 할당, OVN이 OVS에 flow rule 설치
[6] Cinder:      (선택) 볼륨 생성 + iSCSI/RBD로 attach
[7] Compute → libvirt → KVM:  실제 VM 부팅
[8] cloud-init:  SSH 키 주입 → ACTIVE
```

→ **6개 서비스가 협업**, 통신은 REST API + RabbitMQ.

---

## 6. 공통 인프라

| 구성 요소 | 역할 | 권장 |
|---|---|---|
| **MariaDB** | 각 서비스 영속 데이터 | Galera 3대 클러스터 |
| **RabbitMQ** | 서비스 내부 컴포넌트 간 비동기 RPC | 3대 미러 큐 |
| **memcached** | Keystone 토큰 캐시 (Keystone 부하 90%↓) | 컨트롤러마다 |
| **HAProxy + Keepalived** | API 엔드포인트 HA | 컨트롤러 앞단 |
| **Ceph** | Glance/Cinder/Swift 통합 스토리지 백엔드 | 3 OSD 이상 |

---

## 7. 멀티테넌시 격리 계층

| 계층 | 도구 |
|---|---|
| 신원/권한 | Keystone (Project/Domain) |
| 컴퓨트 | Nova + KVM 격리 |
| 네트워크 | Neutron + OVN (Geneve VNI 분리) |
| 스토리지 | Cinder Volume Type + Ceph Pool 권한 |

테넌트 A의 VM은 테넌트 B의 네트워크/볼륨을 **API 단계에서부터** 못 봄.

---

## 8. 한 줄 요약

> **컨트롤(API/DB/MQ) — 컴퓨트(KVM) — 네트워크(OVN) — 스토리지(Ceph)** 4층 분리 구조에서, 핵심 컴포넌트가 토큰 한 장으로 협업해 멀티테넌트 IaaS를 제공한다.
