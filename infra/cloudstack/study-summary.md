# CloudStack 한 장 요약 — 스터디 공유용

> 10분 안에 핵심을 잡고, OpenStack과 비교해 토론할 수 있는 분량.
> 사실 출처: [Apache CloudStack Documentation](https://docs.cloudstack.apache.org/en/latest/).

---

## 30초: 한 줄로

> **내 데이터센터를 AWS처럼 쓰게 해주는 "한 덩어리짜리" 오픈소스 IaaS.**

OpenStack과 같은 문제를 풀지만, **30+ 프로젝트의 연합** 대신 **단일 Java Management Server + MySQL 한 개**로 해결.

---

## 1분: 왜 존재하나

| 문제 | CloudStack의 답 |
|---|---|
| AWS에 데이터 못 올림 (규제·주권) | 내 하드웨어에 직접 깐다 |
| 서버 100대, 사용자 1000명 분배 | 단일 API 한 줄로 셀프서비스 |
| 여러 팀·고객이 안전하게 나눠 씀 | Domain/Account/Project 격리 |
| 운영팀이 OpenStack 30개 컴포넌트 다 못 봄 | **한 서비스만 보면 됨** (Management Server) |
| 설치 며칠 → 학습 곡선 가팔라 | 단일 노드 All-in-One **수 시간 안**에 |

**주 사용처**: Apple iCloud(공개된 사례), 통신사, 호스팅 사업자, Apple Silicon 시대의 가벼운 사내 클라우드, Bitnine/Beeline 등 사이즈가 작은 ISP. ([adopters](https://cloudstack.apache.org/users.html))

---

## 3분: 머릿속 그림

```
            사용자 / UI(웹) / cloudmonkey CLI / API
                          │
                          ▼  HTTP(S) + Signed Query
            ┌─────────────────────────────────┐
            │   Management Server  (Java)      │   ← 한 덩어리
            │   ─ API endpoint                 │
            │   ─ Orchestration engine         │
            │   ─ Scheduler / Allocators       │
            │   ─ Resource managers            │
            │   ─ Async job queue              │
            └────────────┬────────────────────┘
                         │ JDBC
                  ┌──────┴──────┐
                  │   MySQL     │   ← 단일 RDB (cloud, cloud_usage)
                  └─────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   [Hypervisor      [Primary       [Secondary
    Hosts: KVM /    Storage:        Storage:
    XenServer /     NFS/iSCSI/      NFS/SMB/S3]
    VMware/Hyper-V] Ceph]
```

- **Management Server (MS)** 가 거의 모든 일을 맡는다. 운영자 시점에서 OpenStack의 Keystone+Nova+Neutron+Glance+Placement가 합쳐진 형태로 보인다.
- **MySQL 한 개**가 모든 메타데이터(가상머신/네트워크/볼륨/계정/이벤트)를 담는다. OpenStack의 "서비스마다 DB" 와 정반대.
- **Primary Storage**: 살아있는 VM의 디스크. **Secondary Storage**: 템플릿/ISO/스냅샷.

---

## 5분: 계층(Hierarchy) 한 장

> 출처: [Cloud Infrastructure Concepts](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html).

```
Region   ─ 지리적 묶음 (Multi-MS/Multi-Zone)
  └─ Zone   ─ 데이터센터 1개 = 1 Zone (보통)
       ├─ Secondary Storage  (Zone 단위 공유)
       └─ Pod      ─ 보통 1개 랙
            └─ Cluster ─ 같은 하이퍼바이저 + 같은 Primary Storage 공유
                 └─ Host ─ 실제 하이퍼바이저 머신
                      └─ VM
```

| 계층 | 비유 | 무엇을 공유? |
|---|---|---|
| **Region** | 도시 | 여러 Zone, 여러 MS |
| **Zone** | 데이터센터 동 | Secondary Storage, 공용 네트워크 |
| **Pod** | 랙 | 관리망 IP 대역 |
| **Cluster** | 같은 시공사 시공한 바닥 | **하이퍼바이저 종류 동일** + Primary Storage |
| **Host** | 한 대의 서버 | VM들 |

→ **OpenStack의 "AZ/Aggregate"** 와는 다르게, CloudStack은 **물리 토폴로지 자체를 모델링**한다.

---

## 5분: 컴포넌트 6개 한 줄씩

| CloudStack | 역할 | OpenStack 대응 |
|---|---|---|
| **Management Server** | 모든 API/오케스트레이션/스케줄링 | Keystone + Nova-API/Scheduler/Conductor + Glance + Placement |
| **MySQL** | 단일 메타데이터 저장소 | (분산된 nova-db, neutron-db, ...) |
| **System VMs** (SSVM/CPVM/VR) | Secondary Storage I/O / Console / 가상 라우터 | Glance worker + noVNC + Neutron L3 agent |
| **Primary Storage** | 살아있는 VM 디스크 | Cinder의 "스토리지 백엔드" |
| **Secondary Storage** | 템플릿/ISO/스냅샷 | Glance 백엔드 + 스냅샷 저장소 |
| **Hypervisor Host (Agent)** | 실제 VM 실행. KVM은 MS에서 SSH로 직접, XenServer/VMware는 호스트 자체 API | Nova-Compute + libvirt |

---

## 10분: VM 한 개 만들 때 — 협업 단계

> CloudStack API 호출: `deployVirtualMachine`. ([API ref](https://cloudstack.apache.org/api/apidocs-4.20/apis/deployVirtualMachine.html))

```bash
$ cmk deploy virtualmachine \
    serviceofferingid=... templateid=... zoneid=... networkids=...
```

```
[1] API server: Signed Query 검증 (apiKey + secretKey HMAC)
[2] DB: vm_instance 레코드 생성 (state=Allocated)
[3] DeploymentPlanner + Allocators:
       ├─ HostAllocator     "어느 Host?"
       ├─ StoragePoolAllocator  "어느 Primary Storage?"
       └─ (Network이 없으면) GuestNetwork 자동 할당
[4] AsyncJob queue로 작업 enqueue → 즉시 jobid 반환
[5] AgentManager → 선택된 Host의 Agent (KVM은 cloudstack-agent + libvirt)
       ├─ Secondary Storage에서 템플릿 복사 → Primary Storage
       ├─ Virtual Router(System VM)가 DHCP/DNS/Userdata 준비
       └─ libvirt가 VM 부팅
[6] Async job 결과: vm_instance.state=Running
```

**한 컴포넌트(MS)가 진두지휘**. OpenStack은 6개 서비스가 협업, CloudStack은 **MS가 거의 다 함**. 디버깅도 보통 `/var/log/cloudstack/management/management-server.log` **한 곳**에서 시작.

---

## ★ 인사이트 10가지

> 시간 없으면 여기만 읽어도 토론 가능. 모두 [공식 문서](https://docs.cloudstack.apache.org/en/latest/) 근거.

### 1. **MS는 Java Servlet 엔진 한 덩어리**

OpenStack의 "마이크로서비스 연합" 정반대. 디버깅이 쉽지만, 단일 리소스/장애 도메인. 보통 MS 2~3대를 LB(HAProxy) 뒤에 두는 HA 구성. ([management-server-ha](https://docs.cloudstack.apache.org/en/latest/installguide/configuration.html#management-server-load-balancing))

### 2. **하이퍼바이저는 Cluster 단위로 묶인다**

같은 Cluster 안의 모든 Host는 **같은 하이퍼바이저 종류**여야 한다. KVM Host와 VMware Host를 한 Cluster에 못 섞음. ([clusters](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#about-clusters))

### 3. **Primary는 Cluster, Secondary는 Zone 스코프**

| | Primary | Secondary |
|---|---|---|
| 스코프 | Cluster (또는 Zone-wide) | Zone |
| 저장 | 라이브 VM 디스크 | 템플릿/ISO/스냅샷 |
| 프로토콜 | NFS / iSCSI / Ceph RBD / SharedMountPoint | NFS / SMB / S3 |
| 호스트 마운트 | Hypervisor Host에 직접 | **Secondary Storage VM(SSVM)** 이 매개 |

→ Secondary는 **System VM이 매개**. 호스트가 직접 마운트하지 않음. ([storage](https://docs.cloudstack.apache.org/en/latest/adminguide/storage.html))

### 4. **System VM 3종이 사실상 핵심 인프라**

`Zone 만들면 자동 생성`되는 VM 3개:

| VM | 역할 |
|---|---|
| **Secondary Storage VM (SSVM)** | Secondary Storage I/O. 템플릿 다운로드/스냅샷 업로드의 길목 |
| **Console Proxy VM (CPVM)** | 웹 콘솔(noVNC) 프록시. UI에서 "VM 콘솔" 누르면 이 친구가 받음 |
| **Virtual Router (VR)** | 게스트망의 DHCP/DNS/SNAT/PortForward/LB. 네트워크당 1개 (또는 redundant 2개) |

**System VM이 죽으면 그 도메인의 모든 게스트망/콘솔/Secondary I/O가 마비**됨. ([system-vm](https://docs.cloudstack.apache.org/en/latest/adminguide/systemvm.html))

### 5. **Basic Zone vs Advanced Zone — 네트워크 모델 두 갈래**

| | Basic Zone | Advanced Zone |
|---|---|---|
| 격리 | Security Group | VLAN / VXLAN / GRE |
| 통제 | 평면 L2 + SG | Isolated/Shared/L2/VPC |
| 적합 | AWS-classic 같은 단순 멀티테넌트 | 진짜 사설 VPC가 필요한 환경 |

선택은 **Zone 생성 시점에 결정**, 이후 변경 불가. ([networking](https://docs.cloudstack.apache.org/en/latest/adminguide/networking.html))

### 6. **API는 Signed Query 한 가지**

OpenStack의 "토큰 헤더(X-Auth-Token)" 와 다름. CloudStack은 **모든 호출이 apiKey + HMAC-SHA1 서명**. AWS Signature V2와 비슷. 게이트웨이/세션 없음. ([api-doc](https://cloudstack.apache.org/api.html))

### 7. **MS 한 대가 다 하니 스케일링은 수직 + LB 다중화**

OpenStack은 stateless 토큰 + memcached로 수평 확장. CloudStack MS는 **자체적으로 stateless에 가깝지만**, 모든 워커가 한 프로세스 내부에 있어 보통 **MS 노드 2~3대를 HAProxy로 묶는 식**. DB는 MySQL Master + 여러 Read Replica + (대규모는) Galera/InnoDB Cluster. ([install-mgmt-server](https://docs.cloudstack.apache.org/en/latest/installguide/management-server/index.html))

### 8. **Multi-tenancy: Domain 트리 + Account + (선택) Project**

OpenStack의 "Domain → Project" 가 평면이라면, CloudStack의 **Domain 은 N단 트리**. Reseller가 자기 하위 Domain을 다시 분할 가능. ([accounts-domains](https://docs.cloudstack.apache.org/en/latest/adminguide/accounts.html))

### 9. **Service Offering = Flavor + 정책**

OpenStack Flavor가 CPU/RAM 스펙이라면, CloudStack의 **Service Offering** 은 거기에 **HA 옵션, CPU pinning, NUMA, 디스크 QoS, 네트워크 rate limit** 까지 포함. **Disk Offering** 과 **Network Offering** 도 별도 객체로 정책화. ([service-offerings](https://docs.cloudstack.apache.org/en/latest/adminguide/service_offerings.html))

### 10. **운영 디버깅 = 로그 한 곳 보고 시작**

OpenStack은 "어느 서비스가 침묵?" 추적이라면, CloudStack은 **`/var/log/cloudstack/management/management-server.log` 한 곳에서 다 시작**. AsyncJob ID로 추적, 그 다음 hypervisor host의 `agent.log`. 단순함이 무기.

---

## 5분: 비유로 잡기

### Management Server = **백화점 본점 1개**
모든 부서(API/Scheduler/Storage/Network)가 한 건물 안. 결재 도장도 본점장(Java 프로세스) 한 명.

### MySQL = **본사 회계 장부 한 권**
모든 거래(VM, 볼륨, 네트워크, 계정)가 같은 장부에 기록. OpenStack은 "부서별 장부" 인 점이 정반대.

### System VM(VR) = **층마다 있는 안내데스크 + 우편실**
DHCP/DNS/SNAT/포트포워딩이 게스트망마다 1개. 죽으면 그 층 통신 마비.

### Cluster = **같은 시공사가 시공한 한 건물**
KVM 시공사면 KVM, VMware 시공사면 VMware로 묶임. 한 Cluster 안에서는 라이브 마이그레이션이 자유롭다.

### Service Offering = **메뉴판**
"4코어 8GB + HA + 디스크 QoS 100MB/s" 같은 패키지. 사용자는 메뉴 골라서 주문(deploy)만.

---

## 디버깅 한 컷

```
"VM이 Allocated에서 Running으로 안 넘어감"
   │
   ▼
[1] 비동기 잡 ID 확인
$ cmk query asyncjob jobid=<id>
   │
   ├─ jobstatus=2 (failed) + jobresult.errortext
   │
   ▼
[2] MS 로그
$ tail -f /var/log/cloudstack/management/management-server.log
   ├─ NoHostsAvailable          → Allocator 단계 (CPU/RAM/스토리지)
   ├─ InsufficientCapacity      → capacity_threshold 초과 / DB host_capacity 깨짐
   ├─ Network setup failed      → Virtual Router 기동 실패
   └─ TemplateInstallException  → SSVM/Secondary Storage 마운트 문제
   ▼
[3] 해당 Host Agent 로그
$ tail -f /var/log/cloudstack/agent/agent.log     # KVM
   └─ libvirt error / iSCSI login fail / NFS mount fail
```

> **CloudStack 디버깅 = MS 로그 → AsyncJob 결과 → 의심 컴포넌트 한 개로 좁히기.**

---

## CloudStack vs 친구들

| | CloudStack | OpenStack | AWS | Kubernetes |
|---|---|---|---|---|
| 위치 | 내 하드웨어 | 내 하드웨어 | 남의 하드웨어 | 컨테이너 위주 |
| 단위 | VM (Bare metal/Container 부가) | VM/베어메탈/컨테이너 | EC2/ECS 등 | Pod |
| 라이선스 | Apache 2.0 | Apache 2.0 | 사용료 | Apache 2.0 |
| 모듈 모델 | **단일 MS + 플러그인** | 30+ 독립 프로젝트 | 자체 | 컨트롤러+kubelet |
| 학습곡선 | **완만** | 가파름 | 완만 | 중간 |
| 멀티 하이퍼바이저 | **1급** (KVM/VMware/Xen/Hyper-V/LXC) | KVM 위주 | 자체 | (대상 아님) |
| 추세 | 안정적, 통신/호스팅 중심 | 활발 | 표준 | 압도적 성장 |

---

## 자주 듣는 오해 정리

- ❌ "CloudStack은 OpenStack의 라이트 버전이다" → 아님. **2008년부터 Cloud.com → Citrix → Apache 재단**으로 독립적으로 발전. 설계 철학이 다름. 같은 시기에 시작.
- ❌ "Java라서 무겁다" → MS 1대로 수천 호스트/수만 VM 운영 사례 다수(Apple iCloud, Bitnine 등). 무거운 건 메모리 풋프린트뿐.
- ❌ "VMware밖에 못 쓴다" → KVM이 1급 시민. **KVM이 CloudStack의 기본** 추천. VMware/XenServer는 옵션.
- ❌ "AWS 대체" → 아님. **Private/Hosting/Telco** 영역 IaaS.
- ❌ "OpenStack을 다 흡수했다" → 정반대. 두 프로젝트는 **별개의 ASF/OpenInfra Foundation** 프로젝트.

---

## 30초: 결론

> **CloudStack = "한 덩어리 IaaS". 단일 Management Server + 단일 MySQL로 OpenStack과 같은 문제를 푼다.**
> **물리 토폴로지(Region→Zone→Pod→Cluster→Host)를 직접 모델링**, **System VM 3종으로 게스트망/콘솔/Secondary I/O를 처리**.
> **운영 단순함과 학습 곡선이 강점**, 단일 MS 의존이 약점.

---

## 더 깊이

| 주제 | 문서 |
|---|---|
| 큰 그림 (질문 따라가는) | [00-overview/architecture-overview.md](./00-overview/architecture-overview.md) |
| 각 컴포넌트 사용법 | [01-core-services/](./01-core-services/) |
| 부가 서비스 (System VM/VPC/Project/Region) | [02-advanced-services/](./02-advanced-services/) |
| 직접 설치 (Apple Silicon Multipass) | [03-installation/multipass-allinone/](./03-installation/multipass-allinone/) |
| 운영 디테일 | [04-operations/](./04-operations/) |
| 내부 구현 (API auth/Allocator/Virtual Router) | [05-deep-dives/](./05-deep-dives/) |
| 첫 VM 실습 | [labs/01-first-vm.md](./labs/01-first-vm.md) |

---

> 💡 **이 문서를 30분 토론 자료로 활용하기**:
> 1. "30초 요약" + "3분 머릿속 그림" 부터 함께 읽기
> 2. **인사이트 10개 중 OpenStack과 가장 다르다고 느낀 점** 한 명씩 고르기
> 3. "VM 협업 단계" 그리며 "MS 한 곳" vs "OpenStack 6개 서비스" 비교
> 4. 디버깅 한 컷 — "한 곳에서 시작 vs 여기저기 추적" 트레이드오프 토론

---

# 부록 — Private Cloud 설계안 답안 (CloudStack 버전)

> **과제 문항**: CloudStack 기반 Private Cloud의 기본 구성 아키텍처 설계안 작성. 핵심 컴포넌트(Management Server, System VM, Primary/Secondary Storage, Hypervisor)를 포함한 기본 아키텍처 도식 및 역할 설명.

## 1. 설계 개요

**목적**: 자체 데이터센터에 멀티테넌트 IaaS를 구축하여, AWS와 동등한 셀프서비스 VM/네트워크/스토리지를 사내 사용자에게 제공. 운영 인력이 적은 조건에서 **단순함**을 우선.

**설계 원칙**:
- **단일 컨트롤 플레인**: Management Server + MySQL을 HA로 묶어 운영 단일점 최소화
- **물리 토폴로지 충실 모델링**: Zone(DC) → Pod(랙) → Cluster(하이퍼바이저 + 스토리지) → Host
- **장애 격리**: Cluster 단위로 Primary Storage 분리, Secondary는 Zone 단위 공유
- **System VM HA**: VR과 SSVM/CPVM 자동 재기동

---

## 2. 노드 토폴로지 (Zone 1개 기준)

```
┌────────────────────────────────────────────────────────────┐
│  [Management Tier]                                         │
│  ─ MS(Java) × 2 (HAProxy + keepalived)                     │
│  ─ MySQL Master + Replica (또는 InnoDB Cluster 3대)         │
│  ─ NFS for Secondary Storage  (또는 S3-compat)             │
└──────┬─────────────────────────────────────────────────────┘
       │ Management Network (10.0.0.0/24)
       │
       ├──► [Pod-1: 첫 번째 랙]
       │     └── [Cluster-A: KVM]
       │            ├─ Host-1 (cloudstack-agent + libvirt + KVM)
       │            ├─ Host-2 ...
       │            └─ Primary Storage: Ceph RBD pool (Cluster-A 전용)
       │     └── [Cluster-B: KVM] ...
       │
       └──► [Pod-2: 두 번째 랙]
             └── ...
```

**물리 네트워크 분리** (CloudStack에서는 "Traffic Type"으로 명시 — [networking guide](https://docs.cloudstack.apache.org/en/latest/adminguide/networking.html))
- **Management** — MS ↔ Agent 통신, MySQL
- **Public** — 인터넷 출구 / Floating IP
- **Guest** — VM 간 / VPC 트래픽 (VLAN or VXLAN)
- **Storage** — Primary Storage iSCSI/NFS/RBD 트래픽 격리

---

## 3. 핵심 컴포넌트 아키텍처 도식

```
                ┌────────────────────────┐
                │  사용자 / Web UI / cmk │
                └───────────┬────────────┘
                            │ HTTPS + Signed Query
                            ▼
                ┌────────────────────────┐
                │  Management Server     │
                │  (API + Orchestration) │
                └────┬───────────────────┘
                     │ JDBC          ▲
                ┌────▼─────┐         │ Agent RPC
                │  MySQL   │         │
                └──────────┘         │
                                     │
                ┌────────────────────┴──────────────┐
                │                                   │
        ┌───────▼────────┐               ┌─────────▼──────┐
        │ Secondary      │               │ Hypervisor     │
        │ Storage  (NFS) │◄──── SSVM ────│ Host (KVM)     │
        │  templates/ISO │ (System VM)   │ + Agent        │
        └────────────────┘               └─────┬──────────┘
                                               │ libvirt
                                         ┌─────▼──────┐
                                         │   VMs      │
                                         └────┬───────┘
                                              │
                                       ┌──────▼──────┐
                                       │ Primary     │
                                       │ Storage     │
                                       │ (Ceph/iSCSI)│
                                       └─────────────┘

       Per Guest Network:  Virtual Router (System VM)
                            ─ DHCP/DNS/SNAT/PF/LB
```

---

## 4. 컴포넌트별 역할

| 컴포넌트 | 역할 | OpenStack 대응 |
|---|---|---|
| **Management Server** | API 수신, 인증(Signed Query), Allocators, AsyncJob, Resource Manager | Keystone + Nova-API/Scheduler/Conductor + Glance + Placement |
| **MySQL** | 모든 메타데이터(`cloud` 스키마), 사용량(`cloud_usage`) | (각 서비스별 DB 분산) |
| **System VM — Virtual Router (VR)** | 게스트망별 DHCP/DNS/SNAT/포트포워딩/로드밸런싱 | Neutron L3 agent + DHCP agent (분산) |
| **System VM — SSVM** | Secondary Storage 마운트/I/O. 템플릿 다운로드, 스냅샷 업로드 | Glance worker |
| **System VM — CPVM** | 웹 콘솔(noVNC) 프록시 | Nova noVNC proxy |
| **Hypervisor Agent** (cloudstack-agent) | Host에서 MS 명령 실행 (libvirt 호출 등). KVM 한정 | Nova-Compute |
| **Primary Storage** | 라이브 VM 디스크. NFS/iSCSI/Ceph RBD | Cinder + 백엔드 |
| **Secondary Storage** | 템플릿/ISO/스냅샷. NFS/SMB/S3 | Glance backend + snapshot store |
| **(선택) Usage Server** | 시간당 사용량 집계 → 빌링 입력 | Ceilometer/Telemetry |

---

## 5. 데이터 흐름 — VM 생성 (`deployVirtualMachine`)

> 출처: [API doc](https://cloudstack.apache.org/api/apidocs-4.20/apis/deployVirtualMachine.html), [Concepts: deployment process](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/development.html).

```
[1] API server: Signed Query 검증
[2] DB: vm_instance (state=Allocated), volumes 레코드 작성
[3] DeploymentPlanner:
       ├─ FirstFitPlanner / UserDispersingPlanner / ...
       ├─ HostAllocator     → 후보 Host
       ├─ StoragePoolAllocator → 후보 Primary Storage
       └─ Cluster 단위 결정
[4] AsyncJob enqueue → 즉시 jobid 반환
[5] Network 준비:
       ├─ Guest Network 미존재 → 생성
       ├─ Virtual Router 미기동 → System VM 부팅
       └─ DHCP/DNS/Userdata 등록
[6] AgentManager → 선택 Host의 Agent (cloudstack-agent for KVM):
       ├─ 템플릿 캐시 없으면 SSVM이 Secondary→Primary 복사
       ├─ root volume = 템플릿의 COW 클론
       └─ libvirt: define + start
[7] Agent → MS: VM running ping → vm_instance.state=Running
[8] (User Data 사용 시) VR이 169.254.169.254 응답
```

→ **MS가 거의 모든 단계를 직접 진두지휘**.

---

## 6. 공통 인프라 / HA

| 구성 요소 | 역할 | 권장 |
|---|---|---|
| **HAProxy + keepalived** | MS API 엔드포인트 HA | 별도 LB 노드 또는 MS와 공동 |
| **MySQL InnoDB Cluster** | 메타데이터 HA | 3노드 |
| **NFS-HA / Ceph RGW** | Secondary Storage 가용성 | NFS는 DRBD/Pacemaker 또는 Ceph RGW |
| **Ceph RBD** | Primary Storage 통합 | 3 OSD 이상, Cluster당 1 pool 권장 |
| **NTP/Chrony** | MS↔Host 시계 일치 | 필수 (Signed Query에 timestamp 영향 적지만 운영 필수) |

---

## 7. 멀티테넌시 격리 계층

| 계층 | 도구 |
|---|---|
| 신원/권한 | Domain 트리 + Account + User + RoleType (Admin/DomainAdmin/User) |
| 컴퓨트 | Hypervisor 격리 + Service Offering (CPU/RAM 보장) |
| 네트워크 | Advanced Zone: VLAN/VXLAN per Network. Basic Zone: Security Group |
| 스토리지 | Disk Offering별 Storage tag, Project별 Resource Limit |

테넌트 A의 VM은 테넌트 B의 네트워크/볼륨을 **API 단계에서부터** 못 봄.

---

## 8. 한 줄 요약

> **Management Server(API + Orchestration) + MySQL + Hypervisor Cluster(+Primary) + Secondary Storage + System VM 3종** 5층 구성에서, 단일 컨트롤 플레인이 물리 토폴로지(Zone/Pod/Cluster/Host)를 모델링해 멀티테넌트 IaaS를 제공한다.

---

## 공식 문서 레퍼런스

- [Apache CloudStack Documentation (latest)](https://docs.cloudstack.apache.org/en/latest/)
- [Concepts and Terminology](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html)
- [Admin Guide — Networking](https://docs.cloudstack.apache.org/en/latest/adminguide/networking.html)
- [Admin Guide — Storage](https://docs.cloudstack.apache.org/en/latest/adminguide/storage.html)
- [Admin Guide — System VMs](https://docs.cloudstack.apache.org/en/latest/adminguide/systemvm.html)
- [Admin Guide — Accounts](https://docs.cloudstack.apache.org/en/latest/adminguide/accounts.html)
- [Install Guide](https://docs.cloudstack.apache.org/en/latest/installguide/)
- [API Reference](https://cloudstack.apache.org/api.html)
