# 00 · Overview

OpenStack 학습의 출발점. "이게 뭐고, 왜 쓰고, 무엇과 비교되는가"를 잡는다.

---

## 한 줄 정의

> **OpenStack은 "내 서버실/데이터센터를 AWS처럼 쓰게 해주는 오픈소스 소프트웨어 묶음"이다.**

AWS가 Amazon의 데이터센터를 빌려 쓰는 서비스라면, OpenStack은 **내가 가진 서버 더미에 설치해서 AWS 같은 기능을 직접 제공**하는 플랫폼이다. 그래서 보통 **"오픈소스 Private Cloud OS"** 또는 **"IaaS(Infrastructure as a Service) 플랫폼"** 이라고 부른다.

## 왜 쓰는가 — 문제 상황부터

서버 100대가 있다고 해보자. 누군가 "VM 하나 주세요"라고 하면 어떻게 줄 것인가?

1. **수동으로 한다** → `virsh`로 KVM 띄우고, IP 직접 할당, 디스크 수동 생성. 1명은 되는데 100명이 오면 지옥.
2. **AWS를 쓴다** → 돈이 나간다. 회사 내부 데이터는 외부로 못 뺀다. 규제상 불가.
3. **OpenStack을 쓴다** → 100대 서버 위에 올려놓으면, 사용자는 **웹 콘솔/API로 "VM 만들어줘" 한 번**이면 끝. 내부적으로 OpenStack이 어느 서버에 띄울지, 어떤 IP를 줄지, 디스크는 어디서 끌어올지 알아서 처리.

즉, **"서버 자원을 풀(pool)로 묶고 셀프서비스로 나눠주는"** 문제를 푼다.

## 머릿속 그림

```
┌─────────────────────────────────────────────────────┐
│  사용자 (개발자/테넌트)                              │
│  "VM 1개, CPU 4, RAM 8G, Ubuntu, 사설망 A에 붙여줘" │
└──────────────────┬──────────────────────────────────┘
                   │ Horizon(웹) / OpenStack CLI / API
                   ▼
┌─────────────────────────────────────────────────────┐
│  OpenStack (컨트롤 플레인)                          │
│  ─────────────────────────────────                  │
│  Keystone  → 누구세요? 권한 있어요?                 │
│  Nova      → VM 어느 서버에 띄울지 결정             │
│  Neutron   → 네트워크/IP/방화벽                     │
│  Glance    → OS 이미지 제공                         │
│  Cinder    → 디스크 볼륨 제공                       │
│  Placement → 남은 자원 추적                         │
└──────────────────┬──────────────────────────────────┘
                   │ (libvirt/KVM, OVN/OVS, iSCSI 등)
                   ▼
┌─────────────────────────────────────────────────────┐
│  실제 하드웨어 (Compute / Network / Storage 노드)  │
│  [서버1][서버2][서버3]...[서버N]                    │
└─────────────────────────────────────────────────────┘
```

각 서비스가 독립된 프로세스이고, **REST API + RabbitMQ 메시지 버스**로 서로 통신한다. 그래서 필요한 서비스만 골라 쓸 수 있고, 각기 다른 노드에 분산시킬 수 있다.

## AWS에 비유하면

| AWS 서비스 | OpenStack 서비스 | 역할 |
| --- | --- | --- |
| IAM | **Keystone** | 인증/인가, 서비스 카탈로그 |
| EC2 | **Nova** | 가상머신(VM) |
| VPC / Security Group | **Neutron** | 가상 네트워크, 방화벽 |
| AMI | **Glance** | OS 이미지 저장소 |
| EBS | **Cinder** | 블록 스토리지(디스크) |
| S3 | **Swift** | 오브젝트 스토리지 |
| CloudFormation | **Heat** | 인프라 템플릿 오케스트레이션 |
| ELB | **Octavia** | 로드밸런서 |
| EKS | **Magnum** | 관리형 Kubernetes |
| 콘솔(웹 UI) | **Horizon** | 대시보드 |

"AWS를 써본 사람"이라면 **이름만 매핑**해도 OpenStack의 절반은 이해한 셈이다.

## OpenStack이 *아닌* 것

흔한 오해를 먼저 정리한다.

- ❌ **하이퍼바이저가 아니다.** VM을 *직접* 실행하지 않는다. KVM/Xen/VMware ESXi 같은 하이퍼바이저를 **오케스트레이션**한다.
- ❌ **컨테이너 플랫폼이 아니다.** Kubernetes의 대체재가 아니라, 오히려 **K8s가 올라갈 인프라**를 제공한다. (K8s on OpenStack 조합이 흔함)
- ❌ **단일 바이너리가 아니다.** 수십 개 프로젝트(Nova, Neutron, ...)의 **느슨한 연합체**다. 필요한 것만 골라 설치한다.
- ❌ **AWS 킬러가 아니다.** Public Cloud 경쟁이 아니라 **Private/Hybrid Cloud, Telco NFV, Edge** 영역이 주력.

## 누가 쓰는가

- **통신사 (NFV)**: AT&T, Verizon, China Mobile, SK텔레콤, KT — 네트워크 기능(5G 코어, vEPC)을 VM/컨테이너로 올려 돌림
- **연구기관/공공**: CERN (10만 코어 이상), 미국 국립연구소, 유럽 공공 클라우드
- **대형 기업의 사설 클라우드**: Walmart, PayPal, BMW
- **소버린 클라우드**: 데이터가 국경을 못 넘는 규제 환경 (유럽, 중동)

## 문서

이 디렉터리에서 더 깊게 다룰 주제:

- [what-is-openstack.md](./what-is-openstack.md) — 정의, 역사(2010 NASA + Rackspace), 거버넌스(OpenInfra Foundation), 6개월 릴리스 모델(Antelope, Bobcat, Caracal …)
- [architecture-overview.md](./architecture-overview.md) — 컨트롤/컴퓨트/네트워크 노드 구성, RabbitMQ 메시지 버스, MariaDB, 서비스 간 호출 흐름(예: VM 생성 시 Nova → Placement → Neutron → Glance → Cinder 순서)
- [openstack-vs-aws-k8s.md](./openstack-vs-aws-k8s.md) — Public Cloud(AWS/GCP/Azure) / Container Orchestrator(Kubernetes)와의 포지셔닝 비교, "왜 아직도 OpenStack인가"

## 다음 단계

이 개요가 익숙해지면 → [01-core-services/](../01-core-services/)에서 Keystone → Nova → Neutron 순서로 내려가는 것을 권장. 실제로 깔아보고 싶다면 [03-installation/devstack/](../03-installation/devstack/)으로 점프해서 노트북에 단일 노드를 띄워보는 것이 가장 빠른 체득법이다.
