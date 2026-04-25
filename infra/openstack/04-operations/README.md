# 04 · Operations

OpenStack 클러스터를 띄운 이후의 운영 주제.

## 문서

- [troubleshooting.md](./troubleshooting.md) — 흔한 장애 패턴, 로그 위치, 디버깅 체크리스트 (DevStack 시나리오 포함)
- [monitoring-telemetry.md](./monitoring-telemetry.md) — Ceilometer + Gnocchi + Aodh 진영 vs Prometheus + Exporter 진영, SLO 설계
- [upgrade-strategy.md](./upgrade-strategy.md) — 릴리스 모델(SLURP), N→N+1 업그레이드, Kolla-Ansible 업그레이드 절차

## 학습 순서

1. [troubleshooting.md](./troubleshooting.md) — DevStack을 띄워뒀다면 가장 먼저 부딪히는 곳
2. [monitoring-telemetry.md](./monitoring-telemetry.md) — 메트릭 없이는 장애도 SLO도 안 보인다
3. [upgrade-strategy.md](./upgrade-strategy.md) — 안정화 후 다음 릴리스 따라가기

> 💡 DevStack 자체의 일상 운영(서비스 켜기/끄기, 디스크 정리)은 [../03-installation/devstack/daily-ops.md](../03-installation/devstack/daily-ops.md).
