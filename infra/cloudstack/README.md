# Apache CloudStack Deep Dive

CloudStack 학습 + 실제 설치/운영 노트. OpenStack 정리와 같은 흐름으로, Private Cloud(IaaS)를 다른 철학으로 푸는 방식을 비교 학습한다.

> **모든 정리는 [Apache CloudStack 공식 문서](https://docs.cloudstack.apache.org/en/latest/) 기준**. 각 문서 끝에 참고한 공식 페이지 링크를 명시한다.

## 학습 로드맵

| 단계 | 디렉터리 | 내용 |
| --- | --- | --- |
| 1 | [00-overview/](./00-overview/) | CloudStack 정체성, Region→Zone→Pod→Cluster→Host 계층, OpenStack/AWS 비교 |
| 2 | [01-core-services/](./01-core-services/) | Management Server, Hypervisor 지원, Networking, Primary/Secondary Storage, API, Account/Domain |
| 3 | [02-advanced-services/](./02-advanced-services/) | System VM(SSVM/CPVM/VR), VPC, Project, Region & Multi-Zone |
| 4 | [03-installation/](./03-installation/) | Apple Silicon Multipass + 단일 노드 All-in-One 설치 가이드 + 실제 설정 산출물 |
| 5 | [04-operations/](./04-operations/) | 모니터링, 업그레이드, 트러블슈팅 |
| 6 | [05-deep-dives/](./05-deep-dives/) | API 인증 흐름, Virtual Router 내부, Scheduler/Allocator 내부 |
| 7 | [labs/](./labs/) | 설치 후 실습 시나리오 (첫 VM, 네트워크 격리 등) |

## 사용 규칙

- 신규 문서는 [../../template.md](../../template.md) 양식을 따른다.
- 설치 산출물(`/etc/cloudstack/*` 일부, `cloudstack-setup-databases` 인자 등)은 해당 설치 도구 디렉터리에 가이드와 함께 둔다.
- 입문~중급 개념은 `01-core-services/`에, 내부 구현/플로우 분석은 `05-deep-dives/`에 둔다.
- 출처가 불명확한 내용은 적지 않는다. 공식 문서 링크가 있는 사실 위주.

## OpenStack 정리와의 차이

[../openstack/](../openstack/) 가 "30+ 프로젝트 느슨한 연합" 모델을 다룬다면, 이 디렉터리는 **"단일 Java Management Server + MySQL"** 모델이 같은 IaaS 문제를 어떻게 다르게 푸는지를 다룬다. 두 정리를 나란히 두고 읽으면 IaaS 설계 트레이드오프가 보인다.
