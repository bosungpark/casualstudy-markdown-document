# Troubleshooting — 어디부터 봐야 하나

> **CloudStack 디버깅의 출발점은 거의 항상 MS 로그 + AsyncJob 결과 한 곳.**

OpenStack의 "여러 서비스 로그 추적" 과 결정적으로 다른 점.

> 출처: [Admin Guide — Troubleshooting](https://docs.cloudstack.apache.org/en/latest/adminguide/troubleshooting.html).

---

## 1. 로그 위치 ([공식](https://docs.cloudstack.apache.org/en/latest/adminguide/troubleshooting.html#log-files))

| 컴포넌트 | 경로 |
|---|---|
| **Management Server** | `/var/log/cloudstack/management/management-server.log` |
| **Management Server SETUP** | `/var/log/cloudstack/management/setupManagementDb.log` (DB init 시) |
| **Agent (KVM)** | `/var/log/cloudstack/agent/agent.log` |
| **Usage Server** | `/var/log/cloudstack/usage/usage.log` |
| **System VM** (SSH 가능 시) | `/var/log/cloud.log`, `/var/log/messages` |
| **MySQL (Slow query)** | `/var/log/mysql/slow.log` (활성 시) |

→ MS 로그가 1차 출발점.

---

## 2. AsyncJob — "잡이 어디서 막혔나"

대부분의 큰 작업(VM 배포, 스토리지 마이그레이션, 스냅샷)은 비동기.

```bash
$ cmk query asyncjobs jobid=<job-id>
```

```json
{
  "jobstatus": 2,           // 0=running, 1=success, 2=failed
  "jobresultcode": 530,
  "jobresult": {
    "errortext": "Insufficient capacity on cluster X",
    "errorcode": 530
  }
}
```

### 자주 보는 errorcode

| errorcode | 의미 | 출발점 |
|---|---|---|
| 401 | Unauthorized | API 키, signature |
| 432 | Resource not found | id 오타, account scope |
| 530 | Insufficient capacity | Allocator (host/storage) |
| 531 | Resource state mismatch | VM이 Stopped인데 stop 호출 등 |
| 533 | Snapshot related | Secondary Storage 문제 |

### 진행 중 잡 일괄 보기

```bash
$ cmk list asyncjobs status=in-progress
```

---

## 3. 디버깅 흐름 — 결정 트리

```
"VM 생성/시작이 실패"
    │
    ▼
[1] cmk list virtualmachines id=<...>
    └─ state=Error 면 events 보기
    └─ state=Stopped/Allocated 멈춤이면 ↓
    │
    ▼
[2] 마지막 AsyncJob 결과 확인
    └─ errortext 한 줄로 99% 가닥
    │
    ▼
[3] errortext 키워드별 분기:
    ├─ "Insufficient capacity"     → Allocator 단계
    ├─ "No host available"         → HostAllocator
    ├─ "No storage available"      → StoragePoolAllocator
    ├─ "Network setup failed"      → VR (System VM)
    ├─ "Template install failed"   → SSVM / Secondary Storage
    ├─ "Libvirt"                   → KVM Host의 agent.log
    └─ "Connection refused"        → Agent ↔ MS 통신 (8250)
    │
    ▼
[4] 의심 컴포넌트 로그 5분치
    grep -i "<vm-uuid 앞 8자리>\|ERROR\|FAILED" log
```

---

## 4. 흔한 케이스 모음

### 🔴 "Insufficient capacity"

```
원인: capacity 임계 초과 또는 host_capacity DB가 깨짐
   ▼
$ cmk list capacity zoneid=<...>
   → CPU/RAM/Storage 사용률 확인

$ cmk list hosts state=Up resourcestate=Enabled
   → 충분한 호스트가 살아있나?

해결:
   - 큰 VM이면 Service Offering 줄이거나
   - cluster.cpu.allocated.capacity.disablethreshold (기본 0.85) 일시 완화
   - 정말 자원이 없으면 Host 증설
```

### 🔴 SSVM/CPVM이 영원히 Starting

```
$ cmk list systemvms
+--------+-------+----------+
| name   | type  | state    |
+--------+-------+----------+
| s-1-VM | SSVM  | Starting |   ← 5분 넘게 이 상태면 문제
+--------+-------+----------+

원인 1: SystemVM template 누락 (또는 잘못된 architecture)
   ▼
$ ls /mnt/secondary/template/tmpl/1/
   → arm64 환경에 x86 template 등록했을 수 있음
   → cloud-install-sys-tmplt 다시 -F 옵션으로

원인 2: System VM Offering 부족 (메모리)
   ▼
$ cmk list serviceofferings issystem=true
   → 작은 SystemVM Offering 권장 안 함 (특히 ARM)

원인 3: Agent ↔ MS 통신 단절
   ▼
$ tail -f /var/log/cloudstack/agent/agent.log
   → "Connecting to ${MS_IP}:8250" 가 계속 실패면 방화벽/네트워크
```

### 🔴 "Network setup failed" — VR이 안 뜸

```
원인: 게스트망의 Virtual Router 부팅 실패
   ▼
$ cmk list routers state=Stopped
   → 죽은 VR 발견

해결:
$ cmk reboot router id=<...>
또는 강제 재생성:
$ cmk destroy router id=<...>     # 자동 재생성
$ cmk restart network id=<...> cleanup=true
```

### 🔴 Template "Downloading" 영원히

```
원인: SSVM이 Secondary Storage에 못 닿거나, 외부 URL이 느리거나 죽음

진단:
$ cmk list systemvms type=secondarystoragevm
   → SSVM Running 인가?

$ ssh -i /var/lib/cloudstack/management/.ssh/id_rsa.cloud root@<SSVM-IP>
   → MS의 SSVM SSH 키 사용
   → SSVM 안에서 wget <URL> 직접 시도

해결:
   - 외부 URL 변경 또는 직접 다운로드 후 SSVM에 SCP
   - cmk delete template 후 다시 register
```

### 🔴 KVM live migration 실패

```
원인: 두 호스트의 CPU 모델 불일치 또는 storage 불일치

진단:
$ tail -f /var/log/cloudstack/agent/agent.log    # 양쪽 호스트
$ virsh capabilities | grep -A5 cpu

해결:
   - CPU 모델 통일: agent.properties의 guest.cpu.mode를 "Nehalem" 같은 공통 모델로
   - 같은 Cluster 안에서만 시도 (Primary 공유 보장)
```

### 🔴 MS Web UI 접속 안 됨

```
$ systemctl status cloudstack-management
$ tail -f /var/log/cloudstack/management/management-server.log

자주 있는 원인:
   - MySQL 연결 실패 (db.properties 비번 mismatch)
   - JVM heap 부족 (kill -9)
   - 8080 포트 점유 (다른 톰캣)
   - DB schema upgrade 도중 실패 (cloudstack-setup-databases 다시)

heap:
   /etc/default/cloudstack-management → JAVA_OPTS="-Xmx2g"
```

### 🔴 cloudstack-agent 시작 안 됨

```
$ systemctl status cloudstack-agent
$ tail -f /var/log/cloudstack/agent/agent.log

흔한 원인:
   - libvirt가 16509에 listen 안 함 → /etc/libvirt/libvirtd.conf, /etc/default/libvirtd
   - AppArmor가 차단 → Ubuntu에서 disable
   - agent.properties의 host=가 잘못됨
   - Java 17 미설치
```

---

## 5. cmk 진단 명령 모음

```bash
# 전체 상태
$ cmk list zones
$ cmk list pods state=Enabled
$ cmk list clusters allocationstate=Enabled
$ cmk list hosts state=Up
$ cmk list systemvms state=Running

# 자원 사용률
$ cmk list capacity zoneid=<...> type=0   # 0=cpu, 1=ram, 2=storage allocated, 3=storage used, 4=public ip, ...

# 알람/이벤트 (최근 100개)
$ cmk list alerts pagesize=100
$ cmk list events level=ERR pagesize=100

# 사용자 작업 추적
$ cmk list events account=<...> startdate=2026-01-01

# DB 마이그레이션 상태
$ cmk list configurations name="cloud.version"
```

---

## 6. SQL 빠른 진단

CloudStack은 단일 MySQL이라 SQL이 강력한 진단 도구.

```sql
-- 죽어있는 호스트
SELECT name, status, state, resource_state, last_ping
FROM host
WHERE removed IS NULL AND status != 'Up';

-- VM이 어느 호스트에서 도는지
SELECT vm.name, vm.state, h.name AS host
FROM vm_instance vm
LEFT JOIN host h ON vm.host_id = h.id
WHERE vm.removed IS NULL
  AND vm.state IN ('Stopping', 'Starting', 'Error');

-- 진행 중 잡
SELECT id, cmd, job_status, created
FROM async_job
WHERE job_status = 0
ORDER BY created DESC
LIMIT 20;

-- Capacity 깨짐 진단
SELECT capacity_type, used_capacity, total_capacity,
       used_capacity / total_capacity AS ratio
FROM op_host_capacity
WHERE host_id = <host-id>;
```

> ⚠️ **DB 직접 UPDATE는 절대 금지** (운영). 데이터 정합성 깨짐. 진단 SELECT만.

---

## 7. 글로벌 설정 — 흔히 만지는 항목

```bash
$ cmk list configurations name=<...>
$ cmk update configuration name=<...> value=<...>
```

| 설정 | 기본 | 의미 |
|---|---|---|
| `cluster.cpu.allocated.capacity.disablethreshold` | 0.85 | CPU 85% 사용 시 새 VM 배치 거부 |
| `cluster.memory.allocated.capacity.disablethreshold` | 0.85 | 동일 (RAM) |
| `pool.storage.allocated.capacity.disablethreshold` | 0.85 | Primary Storage |
| `host.health.check.interval.seconds` | 60 | Host ping 간격 |
| `secondary.storage.copy.timeout` | 36000 | 큰 템플릿 복사 timeout (sec) |
| `system.vm.use.local.storage` | false | SystemVM이 Local Storage 쓸지 |
| `enable.dynamic.scale.vm` | false | 라이브 vCPU/RAM 변경 |
| `cloud.kubernetes.cluster.enabled` | true | CKS 활성 |

변경 후 일부는 MS 재시작 필요 ("Yes, restart" 표시 있음).

---

## 8. 로그 레벨 임시 변경

```bash
# DEBUG로 잠깐 켜기
$ cmk update configuration name=management-server.log.level value=DEBUG
$ systemctl restart cloudstack-management

# 끄기 (운영은 INFO)
$ cmk update configuration name=management-server.log.level value=INFO
```

또는 `/etc/cloudstack/management/log4j-cloud.xml` 직접 수정.

---

## 9. 로그 따라가기 한 컷

```bash
# VM 생성 흐름 실시간 관찰
$ tail -f /var/log/cloudstack/management/management-server.log \
    | grep -i "deploy\|allocate\|vm-instance\|<vm-uuid 앞 8자리>"
```

```bash
# Agent 쪽
$ tail -f /var/log/cloudstack/agent/agent.log \
    | grep -i "libvirt\|copy\|template"
```

---

## 10. OpenStack 디버깅과의 비교

| | OpenStack | CloudStack |
|---|---|---|
| 로그 위치 | `/var/log/{nova,neutron,cinder,glance,keystone}` 분산 | `/var/log/cloudstack/management` 단일 |
| 출발점 | task_state + 6개 서비스 후보 | AsyncJob + MS 로그 |
| DB 진단 | 서비스별 DB JOIN 못함 | **단일 DB JOIN** 으로 한 컷 |
| RPC 추적 | RabbitMQ 메시지 추적 | (인-프로세스, 추적 X) |

→ 디버깅이 단순한 게 CloudStack의 운영적 강점.

---

## 다음

→ [monitoring.md](./monitoring.md): Prometheus exporter로 자동 알람.
→ [upgrade-strategy.md](./upgrade-strategy.md): 새 버전 올리기.
→ [../05-deep-dives/](../05-deep-dives/): 내부 동작이 궁금할 때.

---

## 공식 문서 레퍼런스

- [Admin Guide — Troubleshooting](https://docs.cloudstack.apache.org/en/latest/adminguide/troubleshooting.html)
- [Log Files](https://docs.cloudstack.apache.org/en/latest/adminguide/troubleshooting.html#log-files)
- [Global Settings](https://docs.cloudstack.apache.org/en/latest/adminguide/management.html#changing-the-global-configuration-parameters)
