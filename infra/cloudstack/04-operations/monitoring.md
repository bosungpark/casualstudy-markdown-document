# Monitoring — 무엇을 보고, 어떻게 알람을 받나

> **CloudStack은 자체 Alert 시스템 + Prometheus exporter + Usage Server 3가지 신호원을 가진다.**

OpenStack Telemetry(Ceilometer/Gnocchi/Aodh) 와 달리, CloudStack의 모니터링은 **MS 안에 통합** + **Prometheus 호환 exporter** 로 단순.

> 출처: [Admin Guide — Management](https://docs.cloudstack.apache.org/en/latest/adminguide/management.html) · [Prometheus Exporter Plugin](https://github.com/apache/cloudstack/tree/main/server/src/main/java/org/apache/cloudstack/metrics).

---

## 1. 신호원 3가지

| 신호원 | 어디 | 무엇 |
|---|---|---|
| **Alert** | MS 안 + UI / API | 자원/Host 다운/Storage 임계 |
| **Prometheus Exporter** | MS의 8080 또는 별도 포트 | Capacity, VM count, 호스트 상태 |
| **Usage Server** | 별도 데몬 + `cloud_usage` DB | 시간당 사용량 (빌링 입력) |

---

## 2. Alert 시스템

> [Admin Alerts](https://docs.cloudstack.apache.org/en/latest/adminguide/management.html#administrator-alerts).

MS가 자체적으로 감지하고 이메일/UI로 통지.

### 기본 알람 종류

| 카테고리 | 예시 |
|---|---|
| 자원 임계 | CPU/RAM/Storage capacity 85% 초과 |
| Host 상태 | Host disconnected / Down |
| System VM | SSVM/CPVM/VR Stopped |
| Secondary Storage | Disk full |
| Public IP | 풀 고갈 |
| Network | VR HA failover |

### UI에서 보기

```
좌측: Infrastructure → Alerts
또는 API:
$ cmk list alerts pagesize=100
$ cmk list alerts type=capacity
```

### 이메일 알람 설정

```bash
# 글로벌 설정
$ cmk update configuration name=alert.email.addresses value=ops@example.com,sre@example.com
$ cmk update configuration name=alert.email.sender value=cloudstack@example.com
$ cmk update configuration name=alert.smtp.host value=smtp.example.com
$ cmk update configuration name=alert.smtp.port value=587
$ cmk update configuration name=alert.smtp.useAuth value=true
$ cmk update configuration name=alert.smtp.username value=alert
$ cmk update configuration name=alert.smtp.password value=...
```

### 임계 변경

```bash
$ cmk update configuration name=cluster.cpu.allocated.capacity.notificationthreshold value=0.75    # 75%
$ cmk update configuration name=pool.storage.allocated.capacity.notificationthreshold value=0.80
```

→ "warn at 75%, disable at 85%" 식 2단계.

---

## 3. Prometheus Exporter

> [Prometheus exporter](https://github.com/apache/cloudstack/blob/main/server/src/main/java/org/apache/cloudstack/metrics/PrometheusExporterImpl.java).

CloudStack 4.10+ 부터 **MS에 빌트인** Prometheus 호환 exporter.

### 활성화

```bash
$ cmk update configuration name=prometheus.exporter.enable value=true
$ cmk update configuration name=prometheus.exporter.port value=9595
$ cmk update configuration name=prometheus.exporter.allowed.ips value=0.0.0.0/0   # 운영은 좁히기

# MS 재시작
$ systemctl restart cloudstack-management
```

```bash
$ curl http://<MS_IP>:9595/metrics
# HELP cloudstack_zones_total ...
cloudstack_zones_total 1
cloudstack_clusters_total 1
cloudstack_hosts_total{state="Up"} 1
cloudstack_vms_total{state="Running"} 5
cloudstack_capacity_used_bytes{type="cpu"} 8000
cloudstack_capacity_total_bytes{type="cpu"} 16000
...
```

### 주요 메트릭

| 메트릭 | 의미 |
|---|---|
| `cloudstack_capacity_used_*` / `cloudstack_capacity_total_*` | CPU/RAM/Storage 사용률 |
| `cloudstack_hosts_total{state}` | Host 상태별 개수 |
| `cloudstack_vms_total{state}` | VM 상태별 개수 |
| `cloudstack_systemvms_total{type,state}` | SSVM/CPVM/VR 상태 |
| `cloudstack_async_jobs_pending` | 대기 작업 |
| `cloudstack_db_response_time_ms` | DB latency |
| `cloudstack_management_server_uptime_seconds` | MS 가동 시간 |

### Prometheus + Grafana 연동

```yaml
# prometheus.yml
scrape_configs:
  - job_name: cloudstack
    static_configs:
      - targets: ['<MS_IP>:9595']
```

→ Grafana 공식 대시보드 [Apache CloudStack — Grafana](https://grafana.com/grafana/dashboards/?search=cloudstack) 검색.

### 외부 exporter (옵션)

[shapeblue/cloudstack-exporter](https://github.com/shapeblue/cloudstack-exporter) 같은 별도 프로젝트도 있음. API 호출 기반.

---

## 4. Usage Server — 빌링 입력

> [Admin Guide — Setting Up Usage](https://docs.cloudstack.apache.org/en/latest/adminguide/usage/usage.html).

별도 데몬(`cloudstack-usage`)이 시간 단위로 사용량 집계.

```
cloud DB        →  cloudstack-usage  →  cloud_usage DB
(이벤트)             (집계)               (시간당 누적)
```

### 활성화

```bash
$ apt install -y cloudstack-usage
$ systemctl enable --now cloudstack-usage

$ cmk list configurations name=usage.execution.timezone
```

### 사용량 보기

```bash
$ cmk list usagerecords \
    startdate=2026-01-01 \
    enddate=2026-01-31

# JSON으로 받아서 외부 빌링 시스템에 입력
$ cmk -o json list usagerecords ... > usage.json
```

### 집계 단위

| usagetype | 의미 |
|---|---|
| 1 | Running VM (시간) |
| 2 | Allocated VM (메모리) |
| 4 | IP Address |
| 5 | Network Bytes Received |
| 6 | Network Bytes Sent |
| 7 | Volume |
| 8 | Template |
| 9 | ISO |
| 10 | Snapshot |
| 21 | LB Policy |
| 22 | Port Forwarding |

→ "초당" 가 아니라 **집계 윈도우(기본 1시간)** 안의 Sum / Avg.

---

## 5. 운영 체크리스트 — 매일/매주/매월

### 매일

- [ ] Alert 새 항목 확인 (UI Dashboard)
- [ ] System VM 모두 Running
- [ ] Host disconnected 없음
- [ ] AsyncJob "in-progress" 5분 이상 머무는 것

### 매주

- [ ] Capacity 임계 근접 (CPU/RAM/Storage)
- [ ] MS log 에 ERROR/WARN 패턴 트렌드
- [ ] 백업: cloud DB / cloud_usage DB / Secondary Storage
- [ ] Prometheus 알람 룰 동작 확인

### 매월

- [ ] Usage 데이터 빌링 시스템에 연동
- [ ] Snapshot 청소 (오래된 백업 삭제)
- [ ] 보안 패치 (Java/Linux/CloudStack 마이너)

---

## 6. 권장 알람 룰 (Prometheus)

```yaml
groups:
- name: cloudstack
  rules:
  - alert: CloudStackHostDown
    expr: cloudstack_hosts_total{state="Down"} > 0
    for: 5m
    annotations:
      summary: "{{ $value }} hosts down"

  - alert: CloudStackCpuCapacityHigh
    expr: cloudstack_capacity_used_bytes{type="cpu"} / cloudstack_capacity_total_bytes{type="cpu"} > 0.85
    for: 10m
    annotations:
      summary: "CPU capacity > 85%"

  - alert: CloudStackSystemVmDown
    expr: cloudstack_systemvms_total{state!="Running"} > 0
    for: 2m
    annotations:
      summary: "System VM not running ({{ $labels.type }})"

  - alert: CloudStackAsyncJobsBacklog
    expr: cloudstack_async_jobs_pending > 50
    for: 10m
    annotations:
      summary: "AsyncJob backlog: {{ $value }}"

  - alert: CloudStackMgmtServerDbSlow
    expr: cloudstack_db_response_time_ms > 1000
    for: 5m
    annotations:
      summary: "DB response > 1s"
```

---

## 7. OpenStack 매핑

| OpenStack | CloudStack |
|---|---|
| Ceilometer / Gnocchi | Usage Server (`cloud_usage` DB) |
| Aodh | Alert system (이메일 + UI) |
| (외부) | Prometheus Exporter (빌트인) |
| Watcher | (없음) |
| Skyline | UI Dashboard |

→ CloudStack은 외부 컴포넌트 의존을 줄여 **단순함을 우선**.

---

## 다음

→ [troubleshooting.md](./troubleshooting.md): 알람 떴을 때 디버깅 흐름.
→ [upgrade-strategy.md](./upgrade-strategy.md): 모니터링 레이어 자체 업그레이드.

---

## 공식 문서 레퍼런스

- [Admin Guide — Administrator Alerts](https://docs.cloudstack.apache.org/en/latest/adminguide/management.html#administrator-alerts)
- [Admin Guide — Setting Up Usage](https://docs.cloudstack.apache.org/en/latest/adminguide/usage/usage.html)
- [CloudStack Prometheus Exporter (소스)](https://github.com/apache/cloudstack/tree/main/server/src/main/java/org/apache/cloudstack/metrics)
- [Global Settings (capacity.threshold 류)](https://docs.cloudstack.apache.org/en/latest/adminguide/management.html#changing-the-global-configuration-parameters)
