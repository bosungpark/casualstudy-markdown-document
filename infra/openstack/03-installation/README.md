# 03 · Installation

OpenStack을 직접 설치하기 위한 가이드와 실제 설정 산출물.

## 설치 도구 비교

| 도구 | 용도 | 노드 수 | 난이도 | 추천 시나리오 |
| --- | --- | --- | --- | --- |
| **DevStack** | 개발/학습용 단일 노드 | 1 | 낮음 | API 학습, 단일 노드 PoC |
| **Kolla-Ansible** | 컨테이너 기반 프로덕션 배포 | 1~N | 중간 | 멀티노드, 운영 가까운 환경 |
| **PackStack** | RHEL/CentOS RPM 기반 소규모 배포 | 1~소규모 | 낮음~중간 | RHEL 계열 빠른 PoC |

## 디렉터리

- [devstack/](./devstack/) — `local.conf` + [setup-guide.md](./devstack/setup-guide.md) + [daily-ops.md](./devstack/daily-ops.md)
- [kolla-ansible/](./kolla-ansible/) — `globals.yml`, `multinode-inventory`, 가이드
- [packstack/](./packstack/) — answer file, 가이드

## 권장 학습 순서

1. **DevStack**으로 단일 노드 띄워 핵심 API/CLI 익히기
2. **Kolla-Ansible**로 멀티노드 구성 — 운영에 가까운 토폴로지 경험
3. (선택) **PackStack**으로 RHEL 계열 배포 흐름 비교
