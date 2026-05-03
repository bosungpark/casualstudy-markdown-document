# 03 · Installation

CloudStack을 직접 설치하기 위한 가이드와 실제 설정 산출물.

## 설치 방법 비교

| 방법 | 용도 | 노드 수 | 난이도 | 추천 시나리오 |
| --- | --- | --- | --- | --- |
| **Multipass All-in-One** | 학습/PoC | 1 | 낮음 | 노트북에서 빠르게 학습 (본 정리) |
| **Quick Install (EL8)** | 학습/PoC | 1 | 낮음 | RHEL/Rocky 환경 |
| **Manual Multi-Node** | 프로덕션 가까운 환경 | 3+ | 높음 | 운영 토폴로지 경험 |
| **Ansible/CloudStack-Ansible** | 자동화 배포 | 1~N | 중간 | 재현 가능한 인프라 |

본 정리는 **Apple Silicon Mac + Multipass 단일 VM 위에서 모든 컴포넌트(MS + Agent + NFS + MySQL)를 한 번에** 설치하는 방식. 학습 목적의 가장 빠른 길.

## 디렉터리

- [multipass-allinone/](./multipass-allinone/) — Apple Silicon Mac 위 Multipass Ubuntu VM에 단일 노드 설치
  - [setup-guide.md](./multipass-allinone/setup-guide.md) — 단계별 설치 가이드
  - [bootstrap.sh](./multipass-allinone/bootstrap.sh) — 자동화 스크립트
  - [agent.properties](./multipass-allinone/agent.properties) — ARM64 KVM Agent 설정 예시
  - [my.cnf](./multipass-allinone/my.cnf) — MySQL 설정 예시

## 권장 학습 순서

1. **Multipass 설치** — `brew install --cask multipass`
2. [multipass-allinone/setup-guide.md](./multipass-allinone/setup-guide.md) 따라 단일 노드 띄우기
3. UI 접속 → Zone 마법사 (Advanced Zone 권장)
4. [../labs/01-first-vm.md](../labs/01-first-vm.md) 첫 VM 띄워보기

> ⚠️ **프로덕션 금지**. 모든 컴포넌트를 한 VM에 두는 구성은 학습용. 실제 운영은 [../00-overview/architecture-overview.md](../00-overview/architecture-overview.md) 의 분리 토폴로지를 따른다.

## 공식 문서 레퍼런스

- [Quick Installation Guide](https://docs.cloudstack.apache.org/en/latest/quickinstallationguide/qig.html)
- [Management Server Installation](https://docs.cloudstack.apache.org/en/latest/installguide/management-server/index.html)
- [Configure Package Repository](https://docs.cloudstack.apache.org/en/latest/installguide/management-server/_pkg_repo.html)
- [KVM Hypervisor Host Installation](https://docs.cloudstack.apache.org/en/latest/installguide/hypervisor/kvm.html)
