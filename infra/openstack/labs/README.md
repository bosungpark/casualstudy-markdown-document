# Labs

설치된 OpenStack 위에서 직접 실행하는 실습 시나리오. 각 lab은 "목표 → 사전 조건 → 단계별 명령 → 검증 → 정리(cleanup)" 구조.

## 시나리오

1. [01-first-vm.md](./01-first-vm.md) — 이미지 업로드 → 키페어 → 보안그룹 → 네트워크 → 인스턴스 부팅 → SSH
2. [02-multi-tenant-network.md](./02-multi-tenant-network.md) — 두 프로젝트, 각자 사설망, 외부 floating IP, 라우터/SNAT 검증
3. [03-live-migration.md](./03-live-migration.md) — 공유 스토리지 셋업, compute 노드 간 live migration 수행
