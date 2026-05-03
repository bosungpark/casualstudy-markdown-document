# CloudStack 아키텍처 — 질문으로 따라가는 큰 그림

> **"이건 왜 이렇게 돼있지?"** 라는 질문을 따라 CloudStack 전체 구조를 그림으로 잡는 문서.

각 컴포넌트의 사용법은 [01-core-services/](../01-core-services/) 에서, 내부 구현은 [05-deep-dives/](../05-deep-dives/) 에서. 여기는 **머릿속에 큰 그림**을 그리는 게 목적.

> 사실 출처: [Apache CloudStack Documentation — Concepts](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html).

---

## 1. 왜 "한 덩어리"인가 — OpenStack과의 분기점

### 두 IaaS의 출발

```
2010 ─ OpenStack 시작 (NASA + Rackspace)
   "여러 회사가 모듈을 따로 만들어 합치자" → 30+ 프로젝트의 연합
2008 ─ Cloud.com 시작 (CloudStack의 전신)
   "운영자가 보기 좋게 한 덩어리로 만들자" → 단일 Management Server
```

같은 시기, 같은 문제(Private IaaS)에 대해 **반대 철학**으로 출발했다. 그 결과:

| | OpenStack | CloudStack |
|---|---|---|
| 모듈 | 30+ 독립 프로세스 | 단일 Java 프로세스 (+ Agent) |
| 통신 | REST + RabbitMQ | 내부는 Java method, MS↔Agent는 TLS RPC |
| DB | 서비스마다 따로 | MySQL 1개 (cloud + cloud_usage) |
| 인증 | Keystone Fernet 토큰 | Signed Query (apiKey + HMAC) |
| 배포 단위 | 서비스별 패키지 / 컨테이너 | `cloudstack-management` 한 패키지 |

### "한 덩어리" 의 결과

장점:
- **운영 단순**: 서비스 간 메시지 큐/REST 디버깅이 없다
- **로그 한 곳**: `/var/log/cloudstack/management/` 에서 시작
- **DB 한 곳**: 한 트랜잭션으로 일관성 보장 쉬움

단점:
- **수직 확장 위주**: MS 1대로 한계, 보통 2~3대 LB
- **모듈 간 결합**: Allocator 버그가 API 응답을 막을 수 있음
- **언어 제약**: 거의 다 Java (확장 시 Java 강제)

→ **"운영자가 적은 환경에서 Private/Hosting IaaS"** 가 CloudStack의 sweet spot.

---

## 2. 물리 토폴로지를 직접 모델링한다

OpenStack의 AZ/Aggregate가 "라벨 + 메타데이터" 로 추상화한다면, CloudStack은 **데이터센터 구조 그대로 객체**.

### 5단계 계층 ([concepts](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html))

```
Region    ─ 도시 단위 (지리적 묶음, 보통 1개)
  └─ Zone   ─ 데이터센터 1개 (또는 1개 동) = 1 Zone
       │  ├─ Public Network (인터넷 출구)
       │  ├─ Guest Network 정의들
       │  └─ Secondary Storage (Zone-wide)
       │
       └─ Pod  ─ 보통 1개 랙 = 1 Pod
            │  ├─ Management Network IP 풀
            │  └─ Guest Subnet (Basic Zone만)
            │
            └─ Cluster  ─ 같은 하이퍼바이저 + Primary Storage 공유
                 │  └─ Primary Storage (Cluster-scope or Zone-scope)
                 │
                 └─ Host  ─ 실제 서버
                      │  └─ libvirt/HVM/ESXi
                      │
                      └─ VM
```

### 각 계층의 의미

| 계층 | 결정 사항 | 변경 가능? |
|---|---|---|
| **Region** | Multi-MS, Multi-Zone 그룹핑 | 거의 정적 |
| **Zone** | Basic vs Advanced 네트워킹, DNS 서버, Internal/Public DNS | 한 번 정하면 사실상 고정 |
| **Pod** | 관리망 IP 대역, Pod 단위 fail domain | 추가/제거 가능 |
| **Cluster** | **하이퍼바이저 종류**, Primary Storage | 하이퍼바이저 종류는 고정 |
| **Host** | 실제 CPU/RAM/디스크. Maintenance 모드 가능 | 동적 |

### 왜 이렇게 나누나 — 비유

- Region = 도시
- Zone = 데이터센터 동
- Pod = 한 랙
- Cluster = "같은 시공사가 시공한 한 층"
- Host = 사무실 한 칸

같은 Cluster 안에서만 **라이브 마이그레이션이 자유로움**. Cluster 경계를 넘으면 cold migration / 스토리지 모션이 필요.

### Primary vs Secondary Storage 스코프

```
Zone
 ├─ Secondary Storage  ────────────────────► Zone 전체 공유
 │                                            (templates, ISO, snapshots)
 ├─ Pod-1
 │   ├─ Cluster-A (KVM)
 │   │   └─ Primary-A  ─────────► Cluster-A 전용 (또는 Zone-wide)
 │   └─ Cluster-B (KVM)
 │       └─ Primary-B  ─────────► Cluster-B 전용
 └─ Pod-2 ...
```

→ **"왜 Cluster 단위?"**: 같은 Primary Storage를 마운트한 호스트끼리만 라이브 마이그레이션이 빠름. 스토리지 일관성/락 충돌을 줄이는 자연스러운 단위.
→ **"왜 Secondary는 Zone-wide?"**: 템플릿/스냅샷은 큰 파일. 한 Zone 안의 모든 호스트가 공유해야 효율.

---

## 3. 서비스 지도 — 누가 누구인가

```
            [사용자 / Web UI / cmk]
                     │
                     ▼  HTTPS Signed Query
        ┌────────────────────────────────┐
        │     Management Server          │
        │ ┌────────────────────────────┐ │
        │ │  ApiServer (Servlet)        │ │
        │ │  ↓                          │ │
        │ │  Authenticator (HMAC)       │ │
        │ │  ↓                          │ │
        │ │  Resource Manager           │ │
        │ │  ↓                          │ │
        │ │  Allocators / Planners      │ │
        │ │  ↓                          │ │
        │ │  AsyncJobManager            │ │
        │ │  ↓                          │ │
        │ │  AgentManager (RPC)         │ │
        │ └────────────────────────────┘ │
        │            │                    │
        │            ▼                    │
        │       MySQL (JDBC)              │
        └─────────┬────────┬──────────────┘
                  │        │
        ┌─────────▼─┐    ┌─▼──────────┐
        │ KVM Host  │    │ XenServer  │
        │ +Agent    │    │ (no agent  │
        │           │    │  needed)   │
        └───────────┘    └────────────┘
```

### 흔한 오해 — Keystone 같은 게 없다

OpenStack에 익숙한 사람이 가장 헷갈리는 점:

```
❌ CloudStack: 사용자 → Keystone 같은 거 → MS
✅ CloudStack: 사용자 → MS API 엔드포인트 (Signed Query 직접 검증)
```

비유: OpenStack은 "신원조회소(Keystone) + 각 서비스" 구조이고, CloudStack은 "**프론트 데스크(ApiServer)가 신원도 봄**". MS 자체가 게이트웨이 + 인증 + 오케스트레이터.

---

## 4. 통신 구조 — 단순한 두 계층

```
[브라우저/CLI]
     │ HTTPS POST/GET, query string에 signature
     ▼
[Management Server]
     │ ↑
     │ │ Java method 호출 (intra-process)
     │ │   ApiServer → ResourceManager → AsyncJobManager → AgentManager
     ▼ │
   [MySQL]
     │
[Management Server]
     │ ↑
     │ │ TLS RPC (자체 프로토콜, JSON-ish over TLS)
     ▼ │
[Hypervisor Host Agent (KVM)]   또는 [XenAPI / vCenter API for non-KVM]
     │
     ▼
[libvirt / virsh]
     │
     ▼
[VM]
```

### 두 종류 통신

| 통신 | 도구 | 특징 |
|---|---|---|
| **외부 → MS** | HTTPS + Signed Query | apiKey + HMAC-SHA1, AWS SigV2 유사 |
| **MS ↔ Agent** | TLS RPC (커스텀) | KVM은 cloudstack-agent, VMware는 vCenter |
| **MS 내부** | Java in-process | 메시지 큐 없음 — 모놀리식의 강점이자 약점 |

### DB는 한 개

```
mysql> SHOW DATABASES;
+--------------------+
| cloud              |   ← 메타데이터: account, vm_instance, volumes, host, ...
| cloud_usage        |   ← 시간당 사용량 (옵션, Usage Server 활성 시)
+--------------------+
```

OpenStack의 "서비스마다 DB" 와 정반대. 모든 컴포넌트가 같은 스키마를 본다.

장단점:
- ✅ JOIN으로 한 번에 진단: "이 VM의 host, primary storage, network이 뭐야?" → SQL 한 줄
- ❌ MySQL이 죽으면 전부 죽음 → InnoDB Cluster/Galera 필수

---

## 5. VM 한 개 만들 때 — 8단계 흐름

> 출처: [API: deployVirtualMachine](https://cloudstack.apache.org/api/apidocs-4.20/apis/deployVirtualMachine.html), [Concepts: Allocators/Planners](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/development.html).

```bash
$ cmk deploy virtualmachine \
    serviceofferingid=<id> templateid=<id> \
    zoneid=<id> networkids=<id> name=my-vm
```

이 한 줄 뒤:

```
[1] ApiServer:  Signed Query 검증 (apiKey + HMAC-SHA1)
       ▼
[2] Authorization:  account/role 권한 확인
       ▼
[3] DB:  vm_instance(state=Allocated), volume 레코드 작성, jobid 발급
       ▼
[4] DeploymentPlanner + Allocators:
       ├─ HostAllocator        → 후보 Host 목록
       ├─ StoragePoolAllocator → 후보 Primary Storage
       └─ Cluster 1개로 좁힘
       ▼
[5] Network 준비:
       ├─ Guest Network 미존재 → 생성 (Network Offering 적용)
       ├─ Virtual Router 없으면 → 부팅 (System VM)
       └─ DHCP/DNS/Userdata 등록
       ▼
[6] AgentManager → 선택 Host의 cloudstack-agent (KVM):
       ├─ 템플릿 캐시 없으면 SSVM이 Secondary→Primary 복사
       ├─ root volume = 템플릿 클론 (qcow2 backing or RBD clone)
       └─ libvirt define + start
       ▼
[7] Agent → MS: VM running ping → vm_instance.state=Running
       ▼
[8] User Data 사용 시: VR이 169.254.169.254 응답
```

**MS가 진두지휘**, OpenStack과의 결정적 차이는 단계 4~7이 **거의 다 MS 내부 모듈** 이라는 점.

---

## 6. 인증/권한 — Signed Query

### 토큰이 아니라 서명

```
요청 URL = base + ?command=deployVirtualMachine&...&apiKey=<K>&signature=<HMAC>

서명 = base64( HMAC_SHA1( secretKey, lower(sorted(params)) ) )
```

→ 서버는 같은 방식으로 서명을 재계산 후 비교. **세션/토큰 없음**.

### 장단점 vs OpenStack Keystone

| | CloudStack Signed Query | OpenStack Keystone |
|---|---|---|
| 세션 | 없음, 매 요청 자체 완결 | 토큰 1시간 유효 |
| 만료 | 없음 (apiKey 폐기로 회수) | 토큰 만료 후 재발급 |
| 서버 부하 | HMAC 1회 = 사실상 0 | Fernet 복호화는 빠르지만 검증 미들웨어 필요 |
| 사용자 UX | 키 발급/관리 필요 | username/password로 매번 로그인 |
| 실수 위험 | secretKey 노출 = 영구 위험 | 토큰 노출 = 1시간 |

자세한 내부: [05-deep-dives/api-auth-flow.md](../05-deep-dives/api-auth-flow.md).

---

## 7. 호스트 선택 — Allocator + Planner

### Planner = "어디 묶음에서 고를까"

| Planner | 정책 |
|---|---|
| `FirstFitPlanner` | 자원 남는 첫 번째 클러스터 |
| `UserDispersingPlanner` | 사용자별로 분산 |
| `UserConcentratedPodPlanner` | 사용자 VM을 한 Pod에 몰기 |
| `ImplicitDedicationPlanner` | 특정 호스트에 한 사용자 전용 |

### Allocator = "그 묶음 안에서 누구"

```
HostAllocator (RandomAllocator / FirstFitRoutingAllocator …)
   ├─ vCPU 맞나?
   ├─ RAM 맞나?
   ├─ Reserved capacity 침범?
   └─ Maintenance 모드?

StoragePoolAllocator
   ├─ Disk Offering 의 storage tag 매치?
   ├─ 사용량 capacity_threshold 초과?
   └─ Cluster scope 매치?
```

→ Plan + Allocate가 **DB의 capacity 테이블**을 본다. 별도 Placement 서비스 없음.

자세한 내부: [05-deep-dives/scheduler-allocator-internals.md](../05-deep-dives/scheduler-allocator-internals.md).

---

## 8. 네트워크 — 두 모델 + System VM

### Basic Zone (단순한 평면 L2 + Security Group)

```
Pod 단위 Guest Subnet  (예: 10.0.0.0/16)
    │
    └─► VM이 그냥 받은 IP를 씀
        보안: AWS-classic 같은 Security Group
```

- VLAN 없음
- 같은 Subnet 안에 모든 VM이 평면적으로 위치
- 격리는 **Security Group(L3/L4 규칙)** 으로
- AWS-classic / Rackspace 같은 단순 멀티테넌트에 적합

### Advanced Zone (VLAN/VXLAN + 풍부한 모델)

```
Network Offering 으로 정의:
   ─ Isolated Network: 테넌트 전용 사설망 + VR
   ─ Shared Network: 여러 테넌트 공유 (예: Public)
   ─ L2 Network: L2만, IPAM 없음
   ─ VPC: 여러 Tier + 라우터 + ACL
```

각 게스트망마다 **Virtual Router(VR)** 가 1개:

```
[VM-A]──[VM-B]──[VM-C]   <─ 같은 게스트망
    \      |      /
     \     │     /
      [Virtual Router]  ← System VM 1개
        │ │ │ │ │
        │ │ │ │ └─ LB (HAProxy)
        │ │ │ └─── PortForward (iptables)
        │ │ └───── SNAT (iptables MASQ)
        │ └─────── DNS (dnsmasq)
        └───────── DHCP (dnsmasq)
```

→ "**Neutron 의 L3 agent + DHCP agent + Octavia 가 System VM 한 개**". OpenStack의 "에이전트들" 이 **VM 1개로 합쳐진** 것.

### Redundant VR

VR이 단일 장애점이 되니, **2개 redundant VR + keepalived(VRRP)** 설정 가능. ([virtualrouter](https://docs.cloudstack.apache.org/en/latest/adminguide/virtual_machines/virtual_router.html))

자세한 내부: [05-deep-dives/virtual-router-internals.md](../05-deep-dives/virtual-router-internals.md).

---

## 9. 운영 관점 — VM이 Allocated에서 안 넘어갈 때

위 8단계 중 **어디든 막힐 수 있음**. CloudStack은 디버깅이 단순한데, **MS 로그 + AsyncJob 결과** 가 1차 출발점.

### 진단 1단계: AsyncJob 결과

```bash
$ cmk query asyncjobs jobid=<id>
```

```json
{
  "jobstatus": 2,
  "jobresultcode": 530,
  "jobresult": {
    "errortext": "Insufficient capacity on cluster ..."
  }
}
```

| jobstatus | 의미 |
|---|---|
| 0 | 진행 중 |
| 1 | 성공 |
| 2 | 실패 (errortext 봐야) |

### 진단 2단계: MS 로그

```bash
$ tail -f /var/log/cloudstack/management/management-server.log
```

| 로그 메시지 | 의심 단계 |
|---|---|
| `NoAvailableHostException` | HostAllocator (단계 4) |
| `StorageUnavailableException` | StoragePoolAllocator (단계 4) |
| `Network setup failed` | Virtual Router 부팅 (단계 5) ⭐ 흔함 |
| `TemplateInstallException` | SSVM/Secondary Storage (단계 6) |
| `LibvirtException` | Host Agent / KVM (단계 6) |

### 진단 3단계: Host Agent 로그

```bash
# KVM Host에서
$ tail -f /var/log/cloudstack/agent/agent.log
```

흔한 케이스:
- libvirt error → `journalctl -u libvirtd`
- iSCSI login fail → `iscsiadm` 세션 확인
- NFS mount fail → 네트워크 / 권한 / `showmount -e`

### 핵심 교훈

> **CloudStack 디버깅 = "MS 로그 → AsyncJob 결과 → 한 컴포넌트로 좁히기".**
> OpenStack 대비 디버깅 출발점이 **단일**이라는 점이 운영 단순함의 핵심.

---

## 10. 한 줄 요약

> **CloudStack = "한 덩어리짜리" 사설 IaaS 프레임워크.**
> **Region/Zone/Pod/Cluster/Host 라는 물리 토폴로지를 직접 모델링.**
> **Management Server 1개 + MySQL 1개**가 인증/스케줄링/오케스트레이션을 다 함.
> **System VM 3종(SSVM/CPVM/VR)** 이 게스트망/콘솔/Secondary I/O를 처리.
> **OpenStack과 같은 문제를 반대 철학으로 푼 결과**, 운영 단순함이 강점, 단일 컨트롤 플레인이 약점.

---

## 다음

- 각 컴포넌트 사용법: [../01-core-services/](../01-core-services/)
- 부가 컴포넌트 (System VM/VPC/Project/Region): [../02-advanced-services/](../02-advanced-services/)
- 직접 깔아보기: [../03-installation/multipass-allinone/](../03-installation/multipass-allinone/)
- 운영 디테일: [../04-operations/](../04-operations/)
- 내부 구현: [../05-deep-dives/](../05-deep-dives/)

---

## 공식 문서 레퍼런스

- [Concepts and Terminology](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html)
- [Cloud Infrastructure (Region/Zone/Pod/Cluster/Host)](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#cloud-infrastructure-overview)
- [Management Server Overview](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#management-server-overview)
- [API Reference](https://cloudstack.apache.org/api.html)
