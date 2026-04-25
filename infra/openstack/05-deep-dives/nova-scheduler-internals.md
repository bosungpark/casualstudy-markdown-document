# Nova Scheduler Internals — VM은 어떻게 호스트를 선택하나

> **`openstack server create` 한 줄 뒤에 일어나는 스케줄링 알고리즘.** Filter → Weigher → Claim 의 3단계.

[01-core-services/nova-compute.md](../01-core-services/nova-compute.md) 가 "Nova의 역할"을 다뤘다면, 이 문서는 **scheduler 코드 안에서 일어나는 일**.

---

## 1. 큰 그림 — 한 번의 스케줄링이 거치는 단계

```
사용자: server create --flavor m1.medium --image ubuntu
   ▼
[nova-api] 요청 검증, DB에 instance 레코드 (status=BUILD)
   ▼ (RabbitMQ)
[nova-conductor] scheduler에 RPC
   ▼
[nova-scheduler] ▼▼▼ 핵심 4단계 ▼▼▼

  ① Placement에 GET /allocation_candidates
     → 자원 가능한 호스트 후보 N개

  ② Filter Scheduler (in-process):
     필터 체인 → 후보 줄임 (AZ, affinity, 이미지 호환 등)

  ③ Weigher 체인:
     남은 후보들에 점수 매김 → 정렬

  ④ Claim:
     상위 호스트에 자원 예약 (Placement에 PUT allocations)
     실패하면 다음 후보로 → 성공할 때까지

   ▼
[nova-conductor] → 선택된 호스트의 nova-compute에 RPC: "build"
   ▼
[nova-compute] libvirt 호출, VM 부팅
```

**핵심 포인트**: scheduler는 **결정**만 한다. 실제 VM은 nova-compute가 만든다.

---

## 2. Step ① — Placement Allocation Candidates

scheduler가 제일 먼저 하는 일은 **Placement에 후보 요청**.

```http
GET /allocation_candidates?
    resources=VCPU:4,MEMORY_MB:8192,DISK_GB:20
    &required=COMPUTE_STATUS_ENABLED
    &member_of=<aggregate>
```

응답:

```json
{
  "allocation_requests": [
    {
      "allocations": {
        "<compute-01-uuid>": {
          "resources": {"VCPU": 4, "MEMORY_MB": 8192, "DISK_GB": 20}
        }
      }
    },
    {
      "allocations": {"<compute-03-uuid>": {...}}
    }
  ],
  "provider_summaries": {
    "<compute-01-uuid>": {
      "resources": {"VCPU": {"used": 10, "capacity": 64}, ...},
      "traits": ["HW_CPU_X86_AVX2", "STORAGE_DISK_SSD"]
    },
    ...
  }
}
```

이 단계가 **1차 필터**. Placement는 **자원 산수**만 빠르게 한다 — 복잡한 정책은 안 봄.

> 💡 옛날엔 모든 호스트를 nova-scheduler가 직접 돌면서 RAM/CPU 체크했다. 이제 그 부담을 Placement로 이관 → scheduler는 더 똑똑한 일에 집중.

---

## 3. Step ② — Filter Scheduler

남은 후보들에 **체인된 필터**를 적용. 각 필터는 호스트별로 True/False 반환.

### 기본 필터 체인 (`nova.conf`)

```ini
[filter_scheduler]
enabled_filters = ComputeFilter,
                  ComputeCapabilitiesFilter,
                  ImagePropertiesFilter,
                  ServerGroupAntiAffinityFilter,
                  ServerGroupAffinityFilter,
                  AvailabilityZoneFilter
```

### 주요 필터들

| 필터 | 역할 |
|---|---|
| `ComputeFilter` | nova-compute가 살아있는가? |
| `ComputeCapabilitiesFilter` | CPU 모드/하이퍼바이저 종류 매칭 |
| `ImagePropertiesFilter` | 이미지가 요구하는 hypervisor_type 등 |
| `AvailabilityZoneFilter` | 요청한 AZ에 속하는가? |
| `ServerGroupAffinityFilter` | server group의 다른 멤버와 같은 호스트인가? |
| `ServerGroupAntiAffinityFilter` | 다른 호스트인가? |
| `NUMATopologyFilter` | NUMA 토폴로지 충족? |
| `PciPassthroughFilter` | 요청한 PCI 디바이스(GPU 등) 있나? |

### Affinity / Anti-Affinity 예시

```bash
$ openstack server group create --policy anti-affinity ha-group

$ openstack server create --hint group=<group-id> ... web1
$ openstack server create --hint group=<group-id> ... web2
# web1, web2는 반드시 다른 호스트에 배치 (같이 죽지 않게)
```

스케줄러가 처리 흐름:

```
web2 생성 요청 → scheduler:
  ① Placement: 후보 [host-A, host-B, host-C]
  ② AntiAffinityFilter: web1이 host-A에 있음 → host-A 제외
                                              → [host-B, host-C]
  ③ Weigher 점수 매겨서 host-B 선택
```

---

## 4. Step ③ — Weigher (점수 매기기)

필터 통과한 후보가 여러 개면, 가중치로 정렬.

```ini
[filter_scheduler]
weight_classes = nova.scheduler.weights.all_weighers
```

### 주요 Weigher

| Weigher | 설명 |
|---|---|
| `RAMWeigher` | RAM 많이 남은 호스트 우선 (스프레드) — 기본 |
| `CPUWeigher` | CPU 많이 남은 호스트 우선 |
| `DiskWeigher` | 디스크 많이 남은 호스트 우선 |
| `IoOpsWeigher` | I/O 작업 적은 호스트 우선 |
| `MetricsWeigher` | 외부 metric 기반 |
| `BuildFailureWeigher` | 최근 build 실패 많은 호스트 페널티 |

### Spread vs Pack — 둘 중 하나 선택

```ini
# 기본: Spread (RAM Weight 양수)
ram_weight_multiplier = 1.0     # 큰 RAM 호스트 선호 → 분산

# Pack (먼저 채우기)
ram_weight_multiplier = -1.0    # 작은 RAM 호스트 선호 → 한 곳에 몰아
```

**Spread**: 부하 분산, 장애 영향 최소화 — 일반적
**Pack**: 자원 효율적 사용, 빈 호스트 살려서 전원 끔 (Green DC)

---

## 5. Step ④ — Claim (자원 예약)

선택한 호스트에 자원을 **확정 예약**해야 한다 — 그래야 다른 동시 요청이 같은 자원을 또 안 가져감.

```http
PUT /allocations/<consumer_uuid (= instance_uuid)>

{
  "allocations": {
    "<compute-01-uuid>": {
      "resources": {"VCPU": 4, "MEMORY_MB": 8192, "DISK_GB": 20}
    }
  },
  "consumer_generation": null,
  "project_id": "...",
  "user_id": "..."
}
```

**Conflict 발생 가능**:
- 동시 요청이 같은 자원을 잡으려 함
- → 응답: `409 Conflict`
- → scheduler: 다음 후보로 retry (`scheduler_max_attempts` 회 까지)

```python
for attempt in range(max_attempts):
    host = filter_and_weigh()
    try:
        placement.claim(host, resources)
        return host
    except ConflictError:
        continue
raise NoValidHost
```

이게 **"No valid host was found"** 의 가장 흔한 원인 중 하나.

---

## 6. Cells v2 — 멀티 셀 환경

대규모 (수천 호스트) 에서는 **Cell** 로 나눈다.

```
[API Cell]
   ├─ nova-api, super-conductor, scheduler
   │
   └─► [Cell 1]  ─ nova-conductor, compute-01~50
       [Cell 2]  ─ nova-conductor, compute-51~100
       [Cell N]  ─ ...
```

scheduler 흐름:

```
[1] super-conductor: scheduler에 "어느 호스트?"
[2] scheduler: Placement(전역) + filter+weigh → "compute-77"
[3] super-conductor: cell-2의 conductor에 RPC
[4] cell-2 conductor → compute-77 nova-compute에 build
```

scheduler는 **글로벌 결정자**. 각 Cell은 **독립된 실행 단위** (RabbitMQ/DB 분리).

---

## 7. 실전: "No valid host was found" 디버깅

가장 흔한 원인 우선순위:

### 1) Placement에 후보가 없음

```bash
$ openstack allocation candidate list \
    --resource VCPU=4 --resource MEMORY_MB=8192
# 결과 비어있으면 자원 부족
```

대처: 자원 정리 (deleted instance allocation 누수 점검 → `nova-manage placement heal_allocations`)

### 2) Filter에서 다 잘림

scheduler 로그:

```
INFO ... Filter ComputeCapabilitiesFilter returned 0 hosts
```

대처: 어느 필터가 잘랐는지 확인 → flavor `extra_specs` / image `properties` 점검

### 3) Claim Conflict 반복

```
WARNING ... Failed to claim resources, retrying. 4 attempts remaining
```

대처: `scheduler_max_attempts` 늘리기 (10~20). 동시 요청 spike가 자주 있으면 이걸로 흡수.

---

## 8. 외부에서 스케줄링에 영향 주기

### Flavor extra_specs

```bash
$ openstack flavor set m1.gpu \
    --property "resources:VGPU=1" \
    --property "trait:HW_GPU_NVIDIA=required" \
    --property "hw:cpu_policy=dedicated"
```

→ Placement 쿼리에 trait/resources 자동 반영.

### Image properties

```bash
$ openstack image set ubuntu-22.04 \
    --property hw_disk_bus=virtio \
    --property hw_video_model=virtio
```

→ ImagePropertiesFilter가 본다.

### Aggregate metadata

```bash
$ openstack aggregate create gpu-zone --availability-zone gpu
$ openstack aggregate set --property gpu=true gpu-zone
$ openstack aggregate add host gpu-zone compute-99
```

→ AggregateInstanceExtraSpecsFilter로 매칭.

---

## 9. 코드 위치 (참고)

| 파일 | 역할 |
|---|---|
| `nova/scheduler/manager.py` | scheduler 메인 루프 (`select_destinations`) |
| `nova/scheduler/filter_scheduler.py` | 필터+가중치 흐름 조정 |
| `nova/scheduler/filters/` | 모든 필터 |
| `nova/scheduler/weights/` | 모든 가중치 |
| `nova/scheduler/client/report.py` | Placement 호출 클라이언트 |
| `nova/scheduler/utils.py` | claim 로직 |

---

## 10. 핵심 요약

```
1. Placement: 자원 산수로 1차 후보 추리기
2. Filter: 정책/속성 기반 후보 줄이기 (체인 통과 못 하면 탈락)
3. Weigher: 남은 후보에 점수 → 정렬
4. Claim: 1순위 호스트에 자원 예약 (실패 시 다음으로 retry)
5. 결정된 호스트의 nova-compute에 build RPC
```

> 💡 **자주 나오는 오해**: scheduler가 매 초마다 모든 호스트를 polling 하지 않는다. **요청 받을 때만** Placement에 한 번 쿼리하고 끝. 그래서 scheduler는 stateless하고 수평 확장이 쉽다.

---

## 다음

→ [keystone-token-flow.md](./keystone-token-flow.md): scheduler 호출 직전의 토큰 검증  
→ [neutron-ovn-internals.md](./neutron-ovn-internals.md): 결정된 호스트에서 VM 포트가 어떻게 네트워크에 붙는지
