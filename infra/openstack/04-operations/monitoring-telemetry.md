# Monitoring & Telemetry — OpenStack 관측

> **"내 VM 누가 CPU 100% 쓰는데?"**, **"지난달 프로젝트별 사용량은?"** 에 답하는 도구들.

OpenStack 자체는 메트릭 수집을 코어로 가지지 않는다. **별도 텔레메트리 스택을 붙여야** 보인다.

---

## 한 줄 요약

```
              ┌── Ceilometer (수집 에이전트)
   리소스 ──→ │
              ├── Gnocchi (시계열 저장)        ← 청구/리포트
              └── Aodh   (알림/임계치)          ← 알람

   리소스 ──→ Prometheus exporter ──→ Prometheus ──→ Grafana
                                                 ←── Alertmanager
```

**둘 중 하나 또는 둘 다** 쓴다. OpenStack 자체 텔레메트리(왼쪽) vs 클라우드 네이티브(오른쪽).

---

## 두 진영 비교

| 항목 | Ceilometer + Gnocchi + Aodh | Prometheus + Exporter |
|---|---|---|
| 설치 난이도 | 높음 (서비스 4개 추가) | 중간 (exporter만) |
| 메트릭 모델 | OpenStack 리소스 중심 (instance, volume…) | 노드/프로세스 중심 |
| 청구(billing) 적합 | ⭐⭐⭐ (Gnocchi가 정밀 집계) | △ (별도 가공) |
| 알람 | Aodh | Alertmanager |
| 대시보드 | Horizon 통합 가능 | Grafana |
| 운영 부담 | 무거움 | 가벼움 |
| 추천 | 텔코/공공 클라우드, 청구 필요 | 사내 IaaS, SRE 친화 |

> 💡 **현장 트렌드**: 사내/엔터프라이즈는 Prometheus가 우세. 청구가 필요한 퍼블릭/세미퍼블릭 사업자는 Ceilometer+Gnocchi 조합 유지.

---

## 진영 1 · Ceilometer / Gnocchi / Aodh

### 역할 분담

```
[Ceilometer Agents] ── 폴링/이벤트 수집
       │
       ▼
[Gnocchi]    ─ 시계열 DB. 빠른 집계용 aggregate 사전계산
       │
       ▼
[Aodh]       ─ 임계치 평가 → Webhook/Heat 트리거
```

| 컴포넌트 | 한 줄 |
|---|---|
| **Ceilometer-agent-compute** | 노드별로 libvirt 통해 VM 메트릭 수집 |
| **Ceilometer-agent-notification** | 다른 서비스의 RabbitMQ 이벤트 수신 (VM 생성/삭제 등) |
| **Ceilometer-agent-central** | API 폴링 (Glance, Cinder…) |
| **Gnocchi** | 시계열 저장. S3/Ceph/파일/InfluxDB 백엔드 |
| **Aodh** | 알람 정의·평가. 임계치/이벤트 기반 |
| **Panko** | (구) 이벤트 저장. **deprecated** — 신규 배포는 사용 X |

### 설치 (DevStack)

`local.conf` 에 한 줄씩 추가하고 `./stack.sh` 재실행.

```ini
enable_plugin ceilometer https://opendev.org/openstack/ceilometer
enable_plugin aodh https://opendev.org/openstack/aodh
# Gnocchi는 별도 — 외부 저장소 사용
CEILOMETER_BACKEND=gnocchi
```

> ⚠️ DevStack에서 Gnocchi는 한때 외부 저장소로 분리되어 설치가 까다롭다. 학습용으로는 **Prometheus 진영을 권장**.

### 손으로 해보기

```bash
# 메트릭 정의 보기
$ openstack metric list | head

# 특정 VM의 CPU 측정값
$ openstack metric measures show \
    --resource-id <vm-uuid> cpu_util

# 알람 만들기 — CPU 80% 5분 지속 시 webhook
$ openstack alarm create \
    --name high-cpu \
    --type gnocchi_resources_threshold \
    --metric cpu_util \
    --threshold 80 \
    --comparison-operator gt \
    --aggregation-method mean \
    --granularity 60 \
    --evaluation-periods 5 \
    --resource-type instance \
    --resource-id <vm-uuid> \
    --alarm-action 'http://my-webhook/'
```

### 청구(billing) 통합

CloudKitty라는 별도 서비스가 Gnocchi 데이터를 읽어 **요금 계산 → 청구서 발급**. 텔코가 자주 쓴다.

```
Gnocchi (raw 메트릭)
   ↓
CloudKitty (rating: vCPU/h × 단가)
   ↓
Invoice / 외부 청구 시스템
```

---

## 진영 2 · Prometheus + Exporter

### 컴포넌트 지도

```
[OpenStack Exporter] ─┐
[Node Exporter]      ─┼→ [Prometheus] → [Grafana]
[libvirt Exporter]   ─┘        ↓
                          [Alertmanager] → Slack/Email/PagerDuty
```

### 흔히 쓰는 Exporter

| Exporter | 무엇을 노출 |
|---|---|
| **openstack-exporter** (`prometheus-openstack-exporter`) | Nova/Neutron/Cinder/Glance API 상태, 리소스 카운트 |
| **node-exporter** | 호스트 CPU/메모리/디스크/네트워크 |
| **libvirt-exporter** | KVM VM별 vCPU·RAM·디스크 IO |
| **rabbitmq-exporter** | 큐 길이, 컨슈머 수 |
| **mysqld-exporter** | DB 커넥션, 슬로우 쿼리 |
| **ovn-exporter** | OVN 컨트롤러/Northbound 상태 |

### Prometheus 설정 예시

```yaml
# prometheus.yml
scrape_configs:
  - job_name: openstack
    static_configs:
      - targets: ['controller:9180']    # openstack-exporter
    metrics_path: /metrics
    params:
      cloud: ['admin']                  # clouds.yaml 의 클라우드 이름

  - job_name: nodes
    static_configs:
      - targets:
          - 'controller:9100'
          - 'compute1:9100'
          - 'compute2:9100'

  - job_name: libvirt
    static_configs:
      - targets: ['compute1:9177', 'compute2:9177']
```

### `clouds.yaml` (openstack-exporter용)

```yaml
clouds:
  admin:
    auth:
      auth_url: http://controller:5000/v3
      username: admin
      password: secret
      project_name: admin
      domain_name: Default
    region_name: RegionOne
    interface: internal
```

### 알아두면 유용한 메트릭

| 메트릭 | 한 줄 |
|---|---|
| `openstack_nova_running_vms` | 컴퓨트 노드별 실행 VM 수 |
| `openstack_nova_vcpus_used` / `_available` | vCPU 가용량 (배치 결정에 핵심) |
| `openstack_neutron_floating_ips` | Floating IP 사용/총량 |
| `openstack_cinder_volumes` | 볼륨 상태별 카운트 (in-use/available/error) |
| `libvirt_domain_info_cpu_time_seconds` | 게스트 별 누적 CPU 사용 |
| `node_filesystem_avail_bytes{mountpoint="/var/lib/nova/instances"}` | 인스턴스 디스크 여유 |

### 알림 룰 예시

```yaml
groups:
  - name: openstack
    rules:
      - alert: NovaComputeDown
        expr: openstack_nova_agent_state == 0
        for: 5m
        annotations:
          summary: "{{ $labels.hostname }} nova-compute down"

      - alert: HypervisorHighMemory
        expr: |
          (openstack_nova_memory_used_bytes
           / openstack_nova_memory_available_bytes) > 0.9
        for: 10m

      - alert: CinderVolumeStuckInError
        expr: openstack_cinder_volumes{status="error"} > 0
        for: 15m
```

---

## 로그 집계 (메트릭과 별개)

메트릭으로 못 잡는 건 로그로 잡는다.

```
[OpenStack 서비스] → journald / 파일 → [Fluent Bit]
                                            ↓
                                    [Loki]   또는   [Elasticsearch]
                                       ↓                    ↓
                                    Grafana             Kibana
```

DevStack에서 빠르게 시도:

```bash
# 모든 devstack 유닛 로그를 journald 에서 한 번에
$ sudo journalctl -u 'devstack@*' --since today
```

---

## 운영자가 봐야 할 대시보드 4개

1. **Capacity** — vCPU/RAM/Disk 가용량 (스케줄링 실패 예방)
2. **Service Health** — Nova/Neutron/Cinder agent up/down
3. **Per-Tenant Usage** — 프로젝트별 인스턴스/볼륨/IP 카운트
4. **Queue / DB** — RabbitMQ 적체, MySQL 슬로우 쿼리

Grafana에 `openstack-exporter` 공식 대시보드(ID 9701, 12693 등)를 그대로 import하면 베이스는 깔린다.

---

## SLO 잡기 좋은 항목

| SLI | SLO 예시 |
|---|---|
| `nova boot` API p95 지연 | < 5s |
| `floating ip create` 성공률 | > 99.9% |
| `nova-compute` agent up 비율 | > 99.95% |
| `cinder volume create → available` p95 | < 60s |

이런 지표는 **합성 트랜잭션(synthetic check)** 으로 잡기 쉽다 — 1분마다 작은 VM 만들고 지우는 cron 잡 만들어서 성공/지연 측정.

---

## 자주 밟는 지뢰

- **Ceilometer가 RabbitMQ 큐를 폭주시킴** — agent-notification 스케일 아웃 또는 이벤트 필터링 (`pipeline.yaml`)
- **Gnocchi 디스크 폭주** — `archive_policy` 보존 정책 안 맞춰두면 무한 증가. 기본 high/medium/low 중 medium 이하로 시작
- **openstack-exporter가 admin 토큰을 자주 발급해 Keystone CPU 100%** — `--cache` 활성, 폴링 주기 30s+
- **VM 메트릭이 안 보임** — libvirt-exporter 미설치 또는 nova가 `compute_monitors` 미설정 (`nova.conf` → `[DEFAULT] compute_monitors = cpu.virt_driver`)
- **알람이 안 가는데 메트릭은 정상** — Alertmanager의 `inhibit_rules`/`route` 설정 또는 Aodh의 `evaluator` 워커 죽음

---

## 다음

- 메트릭으로 장애 감지 → 그 다음은 **로그로 원인 추적** [troubleshooting.md](./troubleshooting.md)
- 버전 올릴 때 텔레메트리 호환성 → [upgrade-strategy.md](./upgrade-strategy.md)
