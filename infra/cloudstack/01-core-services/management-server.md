# Management Server — CloudStack의 두뇌

> **"VM 만들어줘" 한 줄을 받아서 거의 모든 결정과 지휘를 담당하는 단일 Java 프로세스.**

OpenStack의 Keystone + Nova-API + Nova-Scheduler + Nova-Conductor + Glance + Placement 가 **한 프로세스**에 합쳐진 형태.

> 출처: [Concepts: Management Server Overview](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#management-server-overview) · [Install Guide: Management Server](https://docs.cloudstack.apache.org/en/latest/installguide/management-server/index.html).

---

## 한 줄 요약

MS는 **Tomcat 위에 도는 Java Servlet 묶음**이다. 외부에서 보면 "API 엔드포인트 1개", 내부적으로는 모듈이 여러 개. MySQL 한 개를 본다.

```
사용자: "4코어 8G짜리 VM 하나"
    ▼
  MS의 ApiServer가 받음
    ▼
  Authenticator 검증 → Allocator가 호스트/스토리지 결정
    ▼
  AsyncJob queue → AgentManager가 Host Agent에 명령
    ▼
  실제 VM 부팅
```

---

## 비유: 백화점 본점

- **ApiServer** = 안내데스크 (요청 접수)
- **Authenticator** = 신원 확인 (Signed Query 검증)
- **Allocators / Planner** = 매장 배정 담당 (어느 호스트?)
- **ResourceManager** = 자원 관리부
- **AgentManager** = 각 매장 직원과의 통신 담당
- **AsyncJobManager** = 비동기 주문 큐
- **UsageServer** (옵션) = 회계부 (시간당 사용량)

전부 한 건물(JVM 프로세스)에 있다.

---

## 내부 모듈 지도

```
┌─────────────────────────────────────────────────────────┐
│ Management Server (Java Servlet, port 8080/8443/8250)   │
│                                                          │
│   [ApiServer]  ─ /client/api 엔드포인트                  │
│       ↓                                                  │
│   [Authenticator] ─ apiKey + HMAC-SHA1 검증              │
│       ↓                                                  │
│   [AccessChecker / RoleManager] ─ RBAC                   │
│       ↓                                                  │
│   [APIs (Java classes)] ─ deployVirtualMachine 등        │
│       ↓                                                  │
│   ─────────────────────────────────────────────          │
│   [Orchestration Layer]                                  │
│       ├─ DeploymentPlanner                               │
│       ├─ HostAllocator                                   │
│       ├─ StoragePoolAllocator                            │
│       ├─ NetworkManager                                  │
│       └─ TemplateManager                                 │
│       ↓                                                  │
│   [AsyncJobManager] ─ 작업 큐 (DB 기반)                  │
│       ↓                                                  │
│   [AgentManager] ─ Host와 TLS RPC                        │
│       ↓                                                  │
│   ─────────────────────────────────────────────          │
│   [Resource Managers]: HostManager / VMManager /         │
│       VolumeManager / NetworkManager / ...               │
│       ↓                                                  │
│   [DB Layer (JPA/IBatis)] ─ MySQL                        │
└─────────────────────────────────────────────────────────┘
```

| 모듈 | 책임 |
|---|---|
| **ApiServer** | HTTP 요청 → API 클래스 디스패치 |
| **Authenticator** | Signed Query 검증, role 인식 |
| **Allocator** | Host/Storage/IP 자원 매칭 |
| **DeploymentPlanner** | 어느 묶음(Cluster/Pod)에서 고를지 |
| **AsyncJobManager** | jobid 발급 + 진행 추적 (DB-backed) |
| **AgentManager** | KVM cloudstack-agent / XenServer / vCenter API 통신 |
| **UsageServer** | 시간당 누적 사용량 → `cloud_usage` DB |

---

## 외부 인터페이스 — 4개의 포트

```
┌──────────────────────────────────────────┐
│  Management Server                       │
│                                          │
│   8080  HTTP  ─ 평문 API (개발/내부)      │
│   8443  HTTPS ─ TLS API (권장)           │
│   8250  TLS   ─ Agent ↔ MS RPC           │
│   9090  HTTP  ─ 내부 cluster mgmt API    │
└──────────────────────────────────────────┘
```

- **8080/8443**: 사용자/cmk가 호출하는 API
- **8250**: Hypervisor Host Agent 가 MS와 양방향 RPC. 보통 inbound. (방화벽 주의)
- **9090**: MS 노드 간 cluster 관리 (HA 시)

---

## 요청 흐름 — "VM 하나 주세요"

```
[1] 클라이언트 → MS:443/client/api?command=deployVirtualMachine&...&signature=...
[2] ApiServer → Authenticator: apiKey + signature 검증
[3] AccessChecker: account의 role이 deployVirtualMachine 권한 있나?
[4] DeployVMCmd 실행:
       ├─ DB에 vm_instance(state=Allocated), volumes, nics 레코드
       ├─ DeploymentPlanner → HostAllocator → 후보 호스트
       ├─ StoragePoolAllocator → primary storage
       └─ AsyncJobManager.submit(VmDeployWorkJob) → jobid 반환
[5] (즉시 응답) {jobid: "abc-123"}
[6] (백그라운드) AgentManager → 선택 Host의 Agent:
       ├─ 템플릿 캐시 없으면 SSVM이 Secondary→Primary 복사
       ├─ libvirt define + start
       └─ 결과 ping → vm_instance.state=Running
```

→ **사용자 응답은 즉시**, **VM 부팅은 비동기**. OpenStack의 `nova boot`도 같은 패턴.

---

## VM 라이프사이클

```
Allocated  → (Planner/Allocator)
   ↓
Starting   → (Agent가 libvirt 호출)
   ↓
Running    → 정상 운영
   ↓
Stopping   → graceful shutdown
   ↓
Stopped    ← (재시작 가능)
   ↓
Destroyed  ← 삭제 (expunge 후 영구 삭제)
   ↓
Expunged   ← DB에서도 사라짐
```

추가 상태:
- `Migrating` — 라이브/콜드 마이그레이션 중
- `Error` — 무엇이든 실패 (errortext 봐야)
- `Restoring` — 스냅샷 복구 중

---

## HA 구성

> 출처: [Management Server Load Balancing](https://docs.cloudstack.apache.org/en/latest/installguide/configuration.html#management-server-load-balancing).

```
       [HAProxy / keepalived]   (가상 IP)
              │
       ┌──────┴──────┐
       ▼             ▼
   [MS-1]        [MS-2]      ← Active-Active 가능 (자체 stateless에 가까움)
       │             │
       └──────┬──────┘
              │
       ┌──────▼──────┐
       │  MySQL HA   │  (InnoDB Cluster / Galera)
       └─────────────┘
```

**MS는 사실상 stateless**: 모든 상태가 MySQL에 있음. 따라서 노드 추가가 비교적 쉽다. 단, **Agent 연결**은 MS 노드별로 sticky 한 점에 주의(`host` 컬럼이 어느 MS와 talking 인지 추적).

---

## 핵심 객체 (DB)

`cloud` 스키마의 주요 테이블:

| 테이블 | 의미 |
|---|---|
| `account`, `domain`, `user` | 멀티테넌시 객체 |
| `vm_instance` | VM 메타데이터 + state |
| `volumes` | 디스크 |
| `host` | Hypervisor Host |
| `cluster`, `host_pod_ref`, `data_center` | 토폴로지 |
| `network`, `vlan`, `nics` | 네트워크 |
| `service_offering`, `disk_offering`, `network_offering` | 정책 |
| `async_job` | 비동기 작업 추적 |
| `usage_event` (cloud_usage) | 시간당 사용량 |

→ **단일 DB의 강점**: `JOIN` 한 번으로 "이 VM이 어디 클러스터의 어느 호스트에서, 어느 스토리지에 디스크 두고, 어느 네트워크에 붙어있나" 한 줄 SQL로 답 가능.

---

## 손으로 해보기

```bash
# MS 헬스체크
$ curl -k https://<MS_IP>:8080/client/api?command=listCapabilities | jq

# cmk 설치 (Apache CloudStack 공식 CLI)
$ pip install cloudmonkey
$ cmk sync

# 첫 API 호출 (apiKey/secretKey 발급은 UI에서)
$ cmk -u "https://<MS_IP>:8443/client/api" \
      -k <apiKey> -s <secretKey> \
      list users

$ cmk list zones
$ cmk list serviceofferings
$ cmk list templates templatefilter=featured

$ cmk deploy virtualmachine \
      serviceofferingid=<id> \
      templateid=<id> \
      zoneid=<id> \
      networkids=<id> \
      name=test-vm

# 진행 추적
$ cmk query asyncjobs jobid=<jobid>
```

---

## 자주 밟는 지뢰

- **MS에서 Agent와 연결 안 됨** → 8250 포트 방화벽. `tcpdump` 로 outbound 확인. Agent의 `cloudstack-setup-agent` 다시 실행.
- **`management-server.log`가 멈춤** → JVM heap 부족. `/etc/cloudstack/management/server.properties` 또는 `tomcat.conf` 의 `JAVA_OPTS` 에 `-Xmx` 늘리기.
- **MySQL 연결 끊김** → MySQL `wait_timeout` 짧음. 권장 `28800` 이상. `max_connections` 도 350~1000 사이.
- **API가 401** → `apiKey/secretKey` 오타 또는 시계 차이 (Signed Query 자체에는 timestamp 강제 X 이지만, 운영 도구가 timestamp 추가하기도).
- **AsyncJob이 영원히 0** → AsyncJobWorker가 죽음. MS 재시작 또는 `async_job` 테이블 stale 행 정리.

---

## OpenStack 매핑

| OpenStack | CloudStack MS의 모듈 |
|---|---|
| keystone | ApiServer + Authenticator |
| nova-api | ApiServer (deployVirtualMachine 등) |
| nova-scheduler | DeploymentPlanner + HostAllocator |
| nova-conductor | ResourceManager (DB 접근 중앙화) |
| placement | (없음. capacity는 DB의 `host_capacity` 테이블) |
| neutron-server | NetworkManager + Network Orchestration |
| glance-api | TemplateManager + SSVM |
| cinder-api | VolumeManager + StoragePoolAllocator |

→ 한 프로세스 안의 모듈 ≈ OpenStack의 별도 서비스.

---

## 다음

→ [hypervisor-support.md](./hypervisor-support.md): MS가 명령을 보내면 실제로 누가 받는지.
→ [api-and-cloudmonkey.md](./api-and-cloudmonkey.md): 외부에서 MS에 어떻게 말 거는지.
→ [../05-deep-dives/scheduler-allocator-internals.md](../05-deep-dives/scheduler-allocator-internals.md): Allocator의 내부 알고리즘.

---

## 공식 문서 레퍼런스

- [Concepts: Management Server Overview](https://docs.cloudstack.apache.org/en/latest/conceptsandterminology/concepts.html#management-server-overview)
- [Install Guide — Management Server](https://docs.cloudstack.apache.org/en/latest/installguide/management-server/index.html)
- [Management Server Load Balancing](https://docs.cloudstack.apache.org/en/latest/installguide/configuration.html#management-server-load-balancing)
- [API Reference](https://cloudstack.apache.org/api.html)
