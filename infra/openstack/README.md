# OpenStack Deep Dive

OpenStack 학습 + 실제 설치/운영 노트.

## 학습 로드맵

| 단계 | 디렉터리 | 내용 |
| --- | --- | --- |
| 1 | [00-overview/](./00-overview/) | OpenStack 정체성, 아키텍처 큰 그림, 다른 플랫폼과 비교 |
| 2 | [01-core-services/](./01-core-services/) | Keystone, Nova, Neutron, Glance, Cinder, Swift, Horizon, Placement |
| 3 | [02-advanced-services/](./02-advanced-services/) | Heat, Magnum, Octavia, Ironic 등 부가 프로젝트 |
| 4 | [03-installation/](./03-installation/) | DevStack / Kolla-Ansible / PackStack 설치 가이드 + 실제 설정 파일 |
| 5 | [04-operations/](./04-operations/) | 모니터링, 업그레이드, 트러블슈팅 |
| 6 | [05-deep-dives/](./05-deep-dives/) | 핵심 컴포넌트 내부 동작 심화 (OVN, Nova scheduler, Keystone token flow) |
| 7 | [labs/](./labs/) | 설치 후 실습 시나리오 |

## 사용 규칙

- 신규 문서는 [../../template.md](../../template.md) 양식을 따른다.
- 설치 산출물(`local.conf`, `globals.yml`, inventory 등)은 해당 설치 도구 디렉터리에 가이드와 함께 둔다.
- 입문~중급 개념은 `01-core-services/`에, 내부 구현/플로우 분석은 `05-deep-dives/`에 둔다.
