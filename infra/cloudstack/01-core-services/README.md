# 01 · Core Services

CloudStack의 핵심 컴포넌트별 사용법과 기본 개념. OpenStack과 달리 **별도 프로세스 6개가 아니라**, MS 내부 모듈 + Host Agent + System VM 의 조합으로 구성된다.

> 출처: [Apache CloudStack Documentation — Concepts](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/) · [Admin Guide](https://docs.cloudstack.apache.org/en/latest/adminguide/).

## 학습 순서

| 순서 | 문서 | 무엇을 배움 |
|---|---|---|
| 1 | [management-server.md](./management-server.md) | MS의 내부 구조와 모듈 (ApiServer/Allocator/AgentManager) |
| 2 | [hypervisor-support.md](./hypervisor-support.md) | KVM/XenServer/VMware/Hyper-V 지원 차이, KVM Agent |
| 3 | [networking.md](./networking.md) | Basic Zone vs Advanced Zone, Network Offering, VPC |
| 4 | [storage-primary-secondary.md](./storage-primary-secondary.md) | Primary/Secondary 구분, 백엔드 옵션, 템플릿 흐름 |
| 5 | [api-and-cloudmonkey.md](./api-and-cloudmonkey.md) | Signed Query API, cloudmonkey CLI 사용 |
| 6 | [accounts-domains-projects.md](./accounts-domains-projects.md) | Domain 트리 + Account + User + Project |
| 7 | [service-offerings.md](./service-offerings.md) | Service / Disk / Network Offering 차이 |

## OpenStack 대응 한 컷

| OpenStack 서비스 | CloudStack 대응 |
|---|---|
| Keystone | MS의 ApiServer + Authenticator (별도 프로세스 X) |
| Nova-API | MS의 ApiServer (`deployVirtualMachine` 등) |
| Nova-Scheduler | DeploymentPlanner + HostAllocator (MS 내부) |
| Nova-Conductor | ResourceManager (MS 내부) |
| Nova-Compute | cloudstack-agent (KVM 한정. Xen/VMware는 Hypervisor 자체 API) |
| Placement | MS의 capacity 테이블 (별도 서비스 X) |
| Neutron | Network Offering + Virtual Router (System VM) |
| Glance | Secondary Storage + SSVM (System VM) |
| Cinder | Primary Storage + StoragePoolAllocator |
| Horizon | CloudStack UI (MS에 포함, JSP/HTML5) |

→ "별도 서비스로 분리된 OpenStack 컴포넌트"를 CloudStack은 "MS 내부 모듈 + System VM" 으로 통합했다.

## 다음

각 문서를 읽고 → [../03-installation/multipass-allinone/](../03-installation/multipass-allinone/) 에서 직접 설치 → [../labs/01-first-vm.md](../labs/01-first-vm.md) 로 첫 VM 띄우기.
