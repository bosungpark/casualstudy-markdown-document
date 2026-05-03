# 00 · Overview

CloudStack 학습의 출발점. "이게 뭐고, 왜 쓰고, OpenStack과 무엇이 다른가"를 잡는다.

> 사실 출처: [Apache CloudStack Concepts and Terminology](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/).

---

## 한 줄 정의

> **CloudStack은 "내 서버실/데이터센터를 AWS처럼 쓰게 해주는 한 덩어리짜리 오픈소스 IaaS"이다.**

OpenStack과 같은 문제(Private/Hosted IaaS)를 풀지만, **30+ 프로젝트의 연합** 대신 **단일 Java Management Server + 단일 MySQL** 로 푼다. 그래서 "CloudStack은 모놀리식 IaaS" 라고 부르기도 한다.

## 왜 쓰는가 — 문제 상황부터

서버 100대가 있다고 해보자. 누군가 "VM 하나 주세요"라고 하면 어떻게 줄 것인가?

1. **수동으로 한다** → `virsh`로 KVM 띄우고, IP 직접 할당, 디스크 수동 생성. 수동 운영은 사용자가 늘면 폭발.
2. **AWS를 쓴다** → 돈/규제. 데이터를 외부로 못 뺌.
3. **OpenStack을 쓴다** → 가능하지만 Keystone/Nova/Neutron/Cinder/Glance/Placement... 운영팀이 6+개 컴포넌트를 다 봐야 함.
4. **CloudStack을 쓴다** → **Management Server 한 개 + MySQL 한 개** 보면 됨. 운영자 1명도 가능.

→ "**서버 자원을 풀로 묶고 셀프서비스로 나눠주는**" OpenStack과 같은 문제를, **운영 단순함**을 키 가치로 푼다.

## 머릿속 그림

```
┌─────────────────────────────────────────────────────┐
│  사용자 (개발자/테넌트)                              │
│  "VM 1개, CPU 4, RAM 8G, Ubuntu, 게스트망 A에 붙여줘"│
└──────────────────┬──────────────────────────────────┘
                   │ Web UI / cloudmonkey CLI / Signed Query API
                   ▼
┌─────────────────────────────────────────────────────┐
│  Management Server (Java)                           │
│  ─ API endpoint  (단일)                              │
│  ─ Authentication (apiKey + HMAC-SHA1)              │
│  ─ Allocators (Host/Storage/IP)                     │
│  ─ Orchestration / AsyncJob                         │
│  ─ Resource Manager                                 │
│  ─ Usage / Billing (선택)                            │
└──────┬──────────────────────────────────────────────┘
       │ JDBC                  ▲ Agent RPC (TLS)
       ▼                       │
┌──────────┐         ┌─────────┴──────────────────────┐
│  MySQL   │         │  Hypervisor Hosts              │
│ (단일 DB) │         │   ─ KVM + cloudstack-agent     │
└──────────┘         │   ─ XenServer/XCP-ng           │
                     │   ─ VMware vCenter             │
                     └─┬───────────────────┬──────────┘
                       │                   │
              ┌────────▼────────┐ ┌────────▼────────┐
              │ Primary Storage │ │Secondary Storage│
              │ (NFS/iSCSI/Ceph)│ │   (NFS/SMB/S3)  │
              │  *Cluster scope*│ │   *Zone scope*  │
              └─────────────────┘ └─────────────────┘
```

핵심 차이: OpenStack의 "**서비스마다 DB와 API**" → CloudStack의 "**MS 하나가 다 함, MySQL 하나가 다 담음**".

## OpenStack에 비유하면

| OpenStack | CloudStack | 설명 |
| --- | --- | --- |
| Keystone (인증) | **MS의 ApiServer** | CloudStack은 "신원조회소"가 별도 서비스가 아님 |
| Nova (VM) | **MS + Hypervisor Agent** | Allocator/Conductor가 MS 안 |
| Nova Scheduler | **DeploymentPlanner + HostAllocator** | MS 내부 모듈 |
| Glance (이미지) | **Secondary Storage + SSVM** | 별도 서비스 X. NFS/S3 + 시스템 VM 1개 |
| Placement (자원 추적) | **MS 내부 capacity 테이블** | 별도 서비스 X |
| Cinder (블록) | **Primary Storage + StoragePoolAllocator** | "Cinder API" 같은 별도 서비스 X |
| Neutron (네트워크) | **Network Offering + Virtual Router(VR)** | L3는 게스트망마다 VR 1개 |
| Heat (오케스트레이션) | **(별도) AutoScale, 또는 외부 Terraform** | 1급 시민은 아님 |
| Octavia (LB) | **VR이 LB 내장** | LBaaS가 VR의 한 기능 |
| Ironic (베어메탈) | **Bare Metal Compute** (제한적) | Provisioning 일부 지원 |

→ "OpenStack 6개 서비스 = CloudStack MS의 6개 모듈" 로 매핑된다.

## AWS에 비유하면

| AWS | CloudStack |
| --- | --- |
| IAM | Account + Domain + User + Role |
| EC2 | Virtual Machine (Service Offering) |
| EBS | Volume (Disk Offering) + Primary Storage |
| AMI | Template (Secondary Storage) |
| VPC | Advanced Zone Isolated Network 또는 VPC |
| ELB | Network Offering의 LB Service |
| Auto Scaling | AutoScale Policy |
| CloudFormation | (없음, 보통 Terraform CloudStack provider 사용) |

## CloudStack이 *아닌* 것

- ❌ **하이퍼바이저가 아니다.** KVM/Xen/VMware/Hyper-V를 **부린다**.
- ❌ **OpenStack의 라이트 버전이 아니다.** 2008년 Cloud.com → 2011년 Citrix 인수 → 2012년 Apache Foundation 으로 독립적인 역사. ([history](https://cloudstack.apache.org/about.html))
- ❌ **컨테이너 플랫폼이 아니다.** K8s가 올라갈 IaaS 제공.
- ❌ **AWS 킬러가 아니다.** Private/Hosting/Telco 영역.
- ❌ **VMware 전용이 아니다.** KVM이 기본 추천.

## 누가 쓰는가

- **Apple iCloud** (가장 큰 공개 사례)
- **호스팅 / 통신사** — Bitnine, Beeline, Datapipe, Verizon (일부)
- **금융 / 공공** — 데이터 주권이 필요한 곳
- **Apple Silicon 기반 사내 클라우드** — KVM/ARM 지원이 안정화되어 점점 늘어남

(공식 사용자 목록: [users](https://cloudstack.apache.org/users.html))

## 문서

이 디렉터리에서 더 깊게 다루는 주제:

- [architecture-overview.md](./architecture-overview.md) — Region/Zone/Pod/Cluster/Host 계층, MS↔Agent 통신, MySQL 단일 DB, VM 생성 시 협업 흐름

## 다음 단계

이 개요가 익숙해지면 → [01-core-services/](../01-core-services/) 에서 Management Server → Hypervisor → Networking → Storage 순서. 실제로 깔아보고 싶다면 [03-installation/multipass-allinone/](../03-installation/multipass-allinone/) 으로 점프해서 Apple Silicon Mac 위 Multipass VM에 단일 노드를 띄워보는 것이 가장 빠른 체득법이다.
